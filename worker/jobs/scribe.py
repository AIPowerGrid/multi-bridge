"""Get and process a job from the horde"""
import json
import time
import traceback

import requests

from worker.enums import JobStatus
from worker.jobs.framework import HordeJobFramework
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
        self.current_payload = self.pop["payload"]
        self.current_payload["quiet"] = True
        self.requested_softprompt = self.current_payload.get("softprompt")
        self.censored = None
        self.max_seconds = None

    @logger.catch(reraise=True)
    def start_job(self):
        """Starts a Scribe job from a pop request"""
        logger.info(f"▶️ Starting job {self.current_id[:8]}... | Model: {self.current_model} | Length: {self.current_payload['max_length']}")
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
            logger.error(f"❌ Image generation payload detected. This is a text-only worker. Aborting.")
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
            logger.info(
                f"✅ Job {self.current_id[:8]} completed in {round(gen_time, 1)}s | Model: {self.current_model}"
            )
        except Exception as err:
            logger.error(
                f"❌ Error processing job {self.current_id[:8]} | Model: {self.current_model}"
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
                
                # Handle response status
                if gen_req.status_code != 200:
                    error_message = f"OpenAI API error: {gen_req.status_code}"
                    try:
                        error_data = gen_req.json()
                        if "error" in error_data:
                            error_message = f"OpenAI API error: {error_data['error'].get('message', 'Unknown error')}"
                    except json.JSONDecodeError:
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
                        self.start_submit_thread()
                        return
                    
                    loop_retry += 1
                    continue
                
                # Parse response
                try:
                    response_data = gen_req.json()
                    logger.debug(f"OpenAI API response: {response_data}")
                    
                    # Extract text from response
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        if "message" in response_data["choices"][0]:
                            self.text = response_data["choices"][0]["message"].get("content", "")
                        else:
                            logger.error("Unexpected response format from OpenAI API")
                            loop_retry += 1
                            time.sleep(2)
                            continue
                    else:
                        logger.error("No choices returned from OpenAI API")
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
        temperature = float(payload.get("temperature", 0.8))
        top_p = float(payload.get("top_p", 0.9))
        
        # Use OpenAI model from bridge data
        model = self.bridge_data.openai_model
        
        # Create basic payload with common parameters
        openai_payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        # Add messages for chat completion API
        # For simplicity, put everything in a user message
        openai_payload["messages"] = [{"role": "user", "content": prompt}]
        
        # Add stop sequences if specified
        if "stop_sequence" in payload:
            openai_payload["stop"] = payload["stop_sequence"]
        
        # Add optional parameters if present
        if "frequency_penalty" in payload:
            openai_payload["frequency_penalty"] = float(payload["frequency_penalty"])
        
        if "presence_penalty" in payload:
            openai_payload["presence_penalty"] = float(payload["presence_penalty"])
            
        logger.debug(f"Transformed payload for OpenAI: {openai_payload}")
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
        bridge_stats.update_inference_stats(self.current_model, submit_req.json()["reward"])
