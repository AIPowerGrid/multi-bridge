"""Get and process a job from the horde"""
import copy
import json
import os
import random
import re
import time
import traceback
import uuid
from datetime import datetime

import requests

from worker.consts import BRIDGE_VERSION
from worker.enums import JobStatus
from worker.jobs.framework import HordeJobFramework
from worker.jobs.poppers import _last_job_completed, _last_job_info, _waiting_start_time
from worker.logger import logger
from worker.stats import bridge_stats


class ScribeHordeJob(HordeJobFramework):
    """Process a scribe job from the horde"""

    def __init__(self, mm, bd, pop):
        # mm will always be None for the scribe
        super().__init__(mm, bd, pop)
        self.current_model = None
        self.seed = None
        self.text = None
        # Set the model based on API type
        if self.bridge_data.api_type == "openai":
            self.current_model = self.bridge_data.model
        else:
            self.current_model = self.bridge_data.model
        self.current_id = self.pop["id"]
        # Don't try to set current_id on the parent class as it doesn't have that attribute
        self.current_payload = self.pop["payload"]
        self.current_payload["quiet"] = True
        self.requested_softprompt = self.current_payload.get("softprompt")
        self.censored = None
        self.max_seconds = None

    @logger.catch(reraise=True)
    def start_job(self):
        """Starts a Scribe job from a pop request"""
        # Format with consistent width
        job_id = self.current_id[:8]
        model_name = self.current_model
        tokens = self.current_payload['max_length']
        
        # Ensure model name doesn't exceed reasonable length
        if len(model_name) > 15:
            model_name = model_name[:12] + ".."
            
        # Add emoji to model name for visual appeal
        model_name = f"🧠 {model_name}"
        
        # Format job info to match waiting messages
        job_info = f"🚀Received {job_id}"  # Even shorter message as requested
        job_col = f"{job_info:<21}"    # Fixed width of 21 chars to match status_msg in poppers.py
        model_col = f"{model_name:<16}"   # Reduced width to match thread_col in poppers.py
        token_col = f"📊 {tokens} tokens"
        token_col_padded = f"{token_col:<16}"
        
        # Placeholder for task type
        receive_task_type = "🆕 Job"
        logger.info(f"{job_col}| {model_col}| {token_col_padded}| {receive_task_type}")
        
        super().start_job()
        if self.status == JobStatus.FAULTED:
            self.start_submit_thread()
            return
        # we also re-use this for the https timeout to llm inference
        self.max_seconds = (self.current_payload.get("max_length", 80) / 2) + 10
        self.stale_time = time.time() + self.max_seconds
        # These params will always exist in the payload from the horde
        gen_payload = self.current_payload
        if "width" in gen_payload or "length" in gen_payload or "steps" in gen_payload:
            error_info = f"❌ Image Payload Error"  # Shorter message consistent with others
            error_col = f"{error_info:<21}"
            error_type_col = f"Text-only worker{'':<4}"  # Adjusted width for alignment
            logger.error(f"{error_col}| {error_type_col}| Aborting")
            self.status = JobStatus.FAULTED
            self.start_submit_thread()
            return
        
        try:
            prompt_length = len(self.current_payload['prompt'])
            logger.debug(
                f"Prompt length is {prompt_length} characters",
            )
            time_state = time.time()
            
            # Handle based on API type
            if self.bridge_data.api_type == "openai":
                self.handle_openai_generation()
            else:
                self.handle_koboldai_generation()
                
            self.seed = 0
            gen_time = time.time() - time_state
            
            # Format completion info to match waiting messages
            complete_info = f"✅ Complete {job_id}"  # Even shorter message as requested
            complete_col = f"{complete_info:<21}"   # Fixed width of 21 chars to match status_msg in poppers.py
            model_col = f"{model_name:<16}"         # Reduced width to match thread_col in poppers.py
            
            # Determine speed indicator
            tokens_generated = self.current_payload['max_length']
            tokens_per_second = tokens_generated / gen_time

            if tokens_per_second >= 10:
                speed_indicator = "🐇 Fast"
            elif tokens_per_second >= 5:
                speed_indicator = "🚶 Moderate"
            else:
                speed_indicator = "�� Slow"

            speed_indicator_padded = f"{speed_indicator:<16}"
            tps_col_padded = f"⚡{tokens_per_second:<7.1f}TPS"
            logger.info(f"{complete_col}| {model_col}| {speed_indicator_padded}| {tps_col_padded}")
        except Exception as err:
            error_info = f"❌ Failed {job_id}"  # Even shorter message as requested
            error_col = f"{error_info:<21}"
            error_model_col = f"{model_name:<16}"  # Reduced width to match thread_col in poppers.py
            logger.error(
                f"{error_col}| {error_model_col}| Error"
            )
            trace = "".join(traceback.format_exception(type(err), err, err.__traceback__))
            logger.trace(trace)
            self.status = JobStatus.FAULTED
            self.start_submit_thread()
            return
        self.start_submit_thread()
        
    def handle_koboldai_generation(self):
        """Handle generation using KoboldAI API"""
        if self.requested_softprompt != self.bridge_data.current_softprompt:
            requests.put(
                self.bridge_data.kai_url + "/api/latest/config/soft_prompt",
                json={"value": self.requested_softprompt},
            )
            time.sleep(1)  # Wait a second to unload the softprompt
        
        loop_retry = 0
        gen_success = False
        while not gen_success and loop_retry < 5:
            try:
                gen_req = requests.post(
                    self.bridge_data.kai_url + "/api/latest/generate",
                    json=self.current_payload,
                    timeout=self.max_seconds,
                )
            except requests.exceptions.ConnectionError:
                logger.error(f"Worker {self.bridge_data.kai_url} unavailable. Retrying in 3 seconds...")
                loop_retry += 1
                time.sleep(3)
                continue
            except requests.exceptions.ReadTimeout:
                logger.error(f"Worker {self.bridge_data.kai_url} request timeout. Aborting.")
                self.status = JobStatus.FAULTED
                self.start_submit_thread()
                return
            
            if not isinstance(gen_req.json(), dict):
                logger.error(
                    (
                        f"KAI instance {self.bridge_data.kai_url} API unexpected response on generate: {gen_req}. "
                        "Retrying in 3 seconds..."
                    ),
                )
                time.sleep(3)
                loop_retry += 1
                continue
            if gen_req.status_code == 503:
                logger.debug(
                    f"KAI instance {self.bridge_data.kai_url} Busy (attempt {loop_retry}). Will try again...",
                )
                time.sleep(3)
                loop_retry += 1
                continue
            if gen_req.status_code == 422:
                logger.error(
                    f"KAI instance {self.bridge_data.kai_url} reported validation error.",
                )
                self.status = JobStatus.FAULTED
                self.start_submit_thread()
                return
            try:
                req_json = gen_req.json()
            except json.decoder.JSONDecodeError:
                logger.error(
                    (
                        f"Something went wrong when trying to generate on {self.bridge_data.kai_url}. "
                        "Please check the health of the KAI worker. Retrying 3 seconds...",
                    ),
                )
                loop_retry += 1
                time.sleep(3)
                continue
            try:
                self.text = req_json["results"][0]["text"]
            except KeyError:
                logger.error(
                    (
                        f"Unexpected response received from {self.bridge_data.kai_url}: {req_json}. "
                        "Please check the health of the KAI worker. Retrying in 3 seconds..."
                    ),
                )
                logger.debug(self.current_payload)
                loop_retry += 1
                time.sleep(3)
                continue
            gen_success = True
    
    def handle_openai_generation(self):
        """Handle generation using OpenAI API"""
        # Transform the payload to OpenAI format
        openai_payload = self.transform_to_openai_format()
        
        # Set up headers
        headers = {
            "Authorization": f"Bearer {self.bridge_data.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Log the model and payload for debugging
        logger.debug(f"Using model: {self.bridge_data.openai_model}")
        logger.debug(f"OpenAI request payload: {openai_payload}")
        
        # Make request to OpenAI API
        loop_retry = 0
        gen_success = False
        
        while not gen_success and loop_retry < 5:
            try:
                # Use chat completions API with OpenAI
                gen_req = requests.post(
                    f"{self.bridge_data.openai_url}/chat/completions",
                    json=openai_payload,
                    headers=headers,
                    timeout=self.max_seconds
                )
                
                # Log the full request and response for debugging
                logger.debug(f"API URL: {self.bridge_data.openai_url}/chat/completions")
                logger.debug(f"Request headers: {headers}")
                logger.debug(f"Response status: {gen_req.status_code}")
                logger.debug(f"Response headers: {gen_req.headers}")
                
                # Handle response status
                if gen_req.status_code != 200:
                    error_message = f"OpenAI API error: {gen_req.status_code}"
                    try:
                        error_data = gen_req.json()
                        logger.debug(f"Error response data: {error_data}")
                        if "error" in error_data:
                            error_message = f"OpenAI API error: {error_data['error'].get('message', 'Unknown error')}"
                    except json.JSONDecodeError:
                        logger.debug(f"Non-JSON error response: {gen_req.text}")
                        pass
                    
                    logger.error(error_message)
                    
                    # Handle specific status codes
                    if gen_req.status_code == 429:
                        logger.warning("Rate limit exceeded or quota reached. Retrying in 5 seconds...")
                        time.sleep(5)
                    elif gen_req.status_code >= 500:
                        logger.warning("Server error from OpenAI. Retrying in 3 seconds...")
                        time.sleep(3)
                    else:
                        # Client errors like 401, 403, 404 are likely not recoverable
                        self.status = JobStatus.FAULTED
                        # Make sure we have text set to something, even if empty
                        if self.text is None:
                            self.text = ""
                        self.start_submit_thread()
                        return
                    
                    loop_retry += 1
                    continue
                
                # Parse response
                try:
                    response_data = gen_req.json()
                    logger.debug(f"OpenAI API response: {response_data}")
                    
                    # Special handling for o1-mini model which might have a different response format
                    if self.bridge_data.openai_model == "o1-mini":
                        # Log the entire response for debugging
                        logger.info(f"o1-mini response structure: {json.dumps(response_data, indent=2)}")
                        
                        # Try different ways to extract the content
                        if "choices" in response_data and len(response_data["choices"]) > 0:
                            choice = response_data["choices"][0]
                            
                            # Try standard message format first
                            if "message" in choice and "content" in choice["message"]:
                                content = choice["message"]["content"]
                                logger.info(f"o1-mini extracted content: '{content}'")
                                if content.strip():  # Check if content is not just whitespace
                                    self.text = content
                                else:
                                    logger.warning("o1-mini returned empty content")
                                    self.text = "The model did not generate any content."
                            # Try text/content directly in choice
                            elif "text" in choice:
                                self.text = choice["text"]
                                logger.info(f"o1-mini extracted text: '{self.text}'")
                            elif "content" in choice:
                                self.text = choice["content"]
                                logger.info(f"o1-mini extracted content directly: '{self.text}'")
                            # Try finish_reason to see if it's empty for a reason
                            elif "finish_reason" in choice:
                                reason = choice.get("finish_reason")
                                logger.warning(f"o1-mini finish_reason: {reason}")
                                if reason == "stop":
                                    self.text = ""  # Normal stop with no content
                                else:
                                    self.text = f"Generation stopped: {reason}"
                            else:
                                logger.error(f"Unknown o1-mini response format: {choice}")
                                self.text = "Error: Unknown response format"
                        else:
                            logger.error(f"No choices in o1-mini response: {response_data}")
                            self.text = "Error: No choices in response"
                        
                        # If we got here, consider it a success even if text is empty or an error message
                        gen_success = True
                        continue
                    
                    # Standard handling for other models
                    # Extract text from response
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        logger.debug(f"Response choices: {response_data['choices']}")
                        if "message" in response_data["choices"][0]:
                            message_content = response_data["choices"][0]["message"].get("content", "")
                            logger.debug(f"Message content: '{message_content}'")
                            self.text = message_content
                        else:
                            logger.error(f"Unexpected response format from OpenAI API. Choice structure: {response_data['choices'][0]}")
                            loop_retry += 1
                            time.sleep(2)
                            continue
                    else:
                        logger.error(f"No choices returned from OpenAI API. Full response: {response_data}")
                        loop_retry += 1
                        time.sleep(2)
                        continue
                    
                    gen_success = True
                    
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from OpenAI API")
                    loop_retry += 1
                    time.sleep(2)
                    continue
                
            except requests.exceptions.ConnectionError:
                logger.error(f"OpenAI API connection error. Retrying in 3 seconds... (attempt {loop_retry + 1}/5)")
                loop_retry += 1
                time.sleep(3)
                continue
            except requests.exceptions.ReadTimeout:
                logger.error(f"OpenAI API request timeout. Retrying in 3 seconds... (attempt {loop_retry + 1}/5)")
                loop_retry += 1
                time.sleep(3)
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"OpenAI API request exception: {e}")
                self.status = JobStatus.FAULTED
                self.start_submit_thread()
                return
        
        if not gen_success:
            logger.error("Failed to generate text after multiple retries")
            self.status = JobStatus.FAULTED
            self.start_submit_thread()
            return
    
    def transform_to_openai_format(self):
        """Transform Horde payload to OpenAI format"""
        payload = self.current_payload
        
        # Extract parameters from payload
        prompt = payload.get("prompt", "")
        max_tokens = int(payload.get("max_length", 80))
        
        # Use OpenAI model from bridge data
        model = self.bridge_data.openai_model
        
        # Special handling for o1-mini model
        if model == "o1-mini":
            openai_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_completion_tokens": max_tokens  # Correct parameter for o1-mini
            }
            logger.info(f"Using o1-mini with payload: {json.dumps(openai_payload, indent=2)}")
        else:
            temperature = float(payload.get("temperature", 0.8))
            top_p = float(payload.get("top_p", 0.9))
            
            openai_payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,  # Correct parameter for other models
                "temperature": temperature,
                "top_p": top_p
            }
            
            if "stop_sequence" in payload:
                openai_payload["stop"] = payload["stop_sequence"]
            
            if "frequency_penalty" in payload:
                openai_payload["frequency_penalty"] = float(payload["frequency_penalty"])
            
            if "presence_penalty" in payload:
                openai_payload["presence_penalty"] = float(payload["presence_penalty"])
        
        return openai_payload

    def submit_job(self, endpoint="/api/v2/generate/text/submit"):
        """Submits the job to the server to earn our kudos."""
        super().submit_job(endpoint=endpoint)

    def prepare_submit_payload(self):
        self.submit_dict = {
            "id": self.current_id,
            "generation": self.text,
            "seed": self.seed,
        }
        if self.censored:
            self.submit_dict["state"] = self.censored

    def post_submit_tasks(self, submit_req):
        # Store information about the completed job
        global _last_job_completed, _last_job_info
        _last_job_completed = time.time()
        
        # Store relevant job info for stats display
        _last_job_info = {
            'model': self.current_model,
            'kudos': submit_req.json()["reward"],
            'id': self.current_id
        }
        
        # Reset waiting time when a job is completed
        global _waiting_start_time
        _waiting_start_time = time.time()
        
        bridge_stats.update_inference_stats(self.current_model, submit_req.json()["reward"])
