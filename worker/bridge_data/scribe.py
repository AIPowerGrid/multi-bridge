"""The configuration of the bridge"""
import os

import requests
from loguru import logger

from worker.argparser.scribe import args
from worker.bridge_data.framework import BridgeDataTemplate


class KoboldAIBridgeData(BridgeDataTemplate):
    """Configuration object"""

    def __init__(self):
        super().__init__(args)
        self.kai_available = False
        self.model = None
        self.kai_url = "http://localhost:5000"
        self.max_length = int(os.environ.get("HORDE_MAX_LENGTH", "80"))
        self.max_context_length = int(os.environ.get("HORDE_MAX_CONTEXT_LENGTH", "1024"))
        self.branded_model = os.environ.get("HORDE_BRANDED_MODEL", "false") == "true"
        self.softprompts = {}
        self.current_softprompt = None

        self.nsfw = os.environ.get("HORDE_NSFW", "true") == "true"
        self.blacklist = list(filter(lambda a: a, os.environ.get("HORDE_BLACKLIST", "").split(",")))

    @logger.catch(reraise=True)
    def reload_data(self):
        """Reloads configuration data"""
        previous_url = self.horde_url
        super().reload_data()
        if hasattr(self, "scribe_name") and not self.args.worker_name:
            self.worker_name = self.scribe_name
        if args.kai_url:
            self.kai_url = args.kai_url
        if args.sfw:
            self.nsfw = False
        if args.blacklist:
            self.blacklist = args.blacklist
        self.validate_kai()
        if self.kai_available and not self.initialized and previous_url != self.horde_url:
            logger.init(
                (
                    f"Username '{self.username}'. Server Name '{self.worker_name}'. "
                    f"Horde URL '{self.horde_url}'. KoboldAI Client URL '{self.kai_url}'"
                    "Worker Type: Scribe"
                ),
                status="Joining Horde",
            )

    @logger.catch(reraise=True)
    def validate_kai(self):
        logger.debug("Retrieving settings from KoboldAI Client...")
        # Prepare headers with the API key if available.
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            # Request the model with authentication headers.
            req = requests.get(self.kai_url + "/api/latest/model", headers=headers)
            logger.debug("Response from /api/latest/model: [{}] {}", req.status_code, req.text)
            req.raise_for_status()  # raises an error if the status isn't 200
            json_data = req.json()
            logger.debug("JSON decoded: {}", json_data)
            
            if "result" not in json_data:
                logger.error("Expected key 'result' not found in response: {}", json_data)
                self.kai_available = False
                return
            
            self.model = json_data["result"]
            # Normalize huggingface and local downloaded model names
            if "/" not in self.model:
                self.model = self.model.replace("_", "/", 1)
            
            # Retrieve soft prompts list if needed.
            if self.model not in self.softprompts:
                req = requests.get(self.kai_url + "/api/latest/config/soft_prompts_list", headers=headers)
                logger.debug("Response from /api/latest/config/soft_prompts_list: [{}] {}", req.status_code, req.text)
                req.raise_for_status()
                sp_data = req.json()
                if "values" in sp_data:
                    self.softprompts[self.model] = [sp["value"] for sp in sp_data["values"]]
                else:
                    logger.error("Unexpected format for soft_prompts_list: {}", sp_data)
            
            # Retrieve current soft prompt.
            req = requests.get(self.kai_url + "/api/latest/config/soft_prompt", headers=headers)
            logger.debug("Response from /api/latest/config/soft_prompt: [{}] {}", req.status_code, req.text)
            req.raise_for_status()
            soft_prompt_data = req.json()
            if "value" not in soft_prompt_data:
                logger.error("Expected key 'value' not found in soft_prompt response: {}", soft_prompt_data)
                self.kai_available = False
                return
            self.current_softprompt = soft_prompt_data["value"]

        except requests.exceptions.RequestException as e:
            logger.error("Request error while validating KAI at {}: {}", self.kai_url, e)
            self.kai_available = False
            return
        except Exception as e:
            logger.error("Unexpected error during KAI validation: {}", e)
            self.kai_available = False
            return

        self.kai_available = True
