import copy
import json
import time

import requests

from worker.consts import BRIDGE_VERSION
from worker.logger import logger
from worker.stats import bridge_stats

# Add a timestamp for rate limiting status messages
_last_status_update = 0
_status_counter = 0

class JobPopper:
    retry_interval = 1
    BRIDGE_AGENT = f"AI Horde Worker:{BRIDGE_VERSION}:https://github.com/db0/AI-Horde-Worker"

    def __init__(self, mm, bd):
        self.model_manager = mm
        self.bridge_data = copy.deepcopy(bd)
        self.pop = None
        self.headers = {"apikey": self.bridge_data.api_key}
        # This should be set by the extending class
        self.endpoint = None

    def horde_pop(self):
        """Get a job from the horde"""
        try:
            # logger.debug(self.headers)
            # logger.debug(self.pop_payload)
            pop_req = requests.post(
                self.bridge_data.horde_url + self.endpoint,
                json=self.pop_payload,
                headers=self.headers,
                timeout=40,
            )
            # logger.debug(self.pop_payload)
            node = pop_req.headers.get("horde-node", "unknown")
            logger.debug(f"Job pop took {pop_req.elapsed.total_seconds()} (node: {node})")
            bridge_stats.update_pop_stats(node, pop_req.elapsed.total_seconds())
        except requests.exceptions.ConnectionError:
            logger.warning(f"Server {self.bridge_data.horde_url} unavailable during pop. Waiting 10 seconds...")
            time.sleep(10)
            return None
        except TypeError:
            logger.warning(f"Server {self.bridge_data.horde_url} unavailable during pop. Waiting 2 seconds...")
            time.sleep(2)
            return None
        except requests.exceptions.ReadTimeout:
            logger.warning(f"Server {self.bridge_data.horde_url} timed out during pop. Waiting 2 seconds...")
            time.sleep(2)
            return None
        except requests.exceptions.InvalidHeader:
            logger.warning(
                f"Server {self.bridge_data.horde_url} Something is wrong with the API key you are sending. "
                "Please check your bridgeData api_key variable. Waiting 10 seconds...",
            )
            time.sleep(10)
            return None

        try:
            self.pop = pop_req.json()  # I'll use it properly later
        except json.decoder.JSONDecodeError:
            logger.error(
                f"Could not decode response from {self.bridge_data.horde_url} as json. "
                "Please inform its administrator!",
            )
            time.sleep(2)
            return None
        if not pop_req.ok:
            logger.warning(f"{self.pop['message']} ({pop_req.status_code})")
            if "errors" in self.pop:
                logger.warning(f"Detailed Request Errors: {self.pop['errors']}")
            time.sleep(2)
            return None
        return [self.pop]

    def report_skipped_info(self, reason):
        """Report why we skipped a job"""
        global _last_status_update, _status_counter
        
        # Only show status updates every 10 seconds
        current_time = time.time()
        if current_time - _last_status_update < 10:
            _status_counter += 1
            return
        
        # Create a simple ASCII status indicator
        status_chars = ["-", "\\", "|", "/"]
        worker_count = len(self.bridge_data.get_running_models()) if hasattr(self.bridge_data, 'get_running_models') else 0
        
        # Show a compact status line with a spinner
        status_char = status_chars[int(current_time) % 4]
        if _status_counter > 0:
            logger.info(f"{status_char} Waiting for jobs... ({_status_counter} checks) | Workers: {worker_count} | {reason}")
        else:
            logger.info(f"{status_char} Waiting for jobs... | Workers: {worker_count} | {reason}")
        
        # Reset counter and update timestamp
        _status_counter = 0
        _last_status_update = current_time


class ScribePopper(JobPopper):
    def __init__(self, mm, bd):
        super().__init__(mm, bd)
        self.endpoint = "/api/v2/generate/text/pop"
        
        # For both OpenAI and KoboldAI, use the model_name from bridge_data
        # This will already have the domain prefix from our modifications in start_worker.py
        self.available_models = [self.bridge_data.model_name]
        
        # Add branding if needed
        if hasattr(bd, 'branded_model') and bd.branded_model and hasattr(bd, 'username') and bd.username:
            self.available_models = [f"{self.available_models[0]}::{bd.username}"]
        
        # Build the payload based on what's available
        self.pop_payload = {
            "name": self.bridge_data.worker_name,
            "models": self.available_models,
            "max_length": self.bridge_data.max_length,
            "max_context_length": self.bridge_data.max_context_length,
            "priority_usernames": self.bridge_data.priority_usernames,
            "threads": self.bridge_data.max_threads,
            "bridge_agent": self.BRIDGE_AGENT,
        }
        
        # Add softprompts only for KoboldAI
        if hasattr(bd, 'api_type') and bd.api_type == "koboldai" and hasattr(bd, 'softprompts') and hasattr(bd, 'model') and bd.model in bd.softprompts:
            self.pop_payload["softprompts"] = bd.softprompts[bd.model]

    def horde_pop(self):
        if not super().horde_pop():
            return None
        if not self.pop.get("id"):
            self.report_skipped_info(f"No valid generations for us to do.")
            return None
        return [self.pop]
