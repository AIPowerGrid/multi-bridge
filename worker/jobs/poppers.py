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
_waiting_start_time = None  # Track when we started waiting for jobs
_last_job_completed = None  # Track when last job was completed
_last_job_info = None  # Store information about the last job

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
        global _last_status_update, _status_counter, _waiting_start_time, _last_job_completed, _last_job_info
        
        current_time = time.time()
        
        # Initialize waiting start time if this is our first check
        if _waiting_start_time is None:
            _waiting_start_time = current_time
        
        # Only show status updates every 5 seconds
        if current_time - _last_status_update < 5:
            _status_counter += 1
            return
        
        # Get worker count - this shows active inference threads
        worker_count = len(self.bridge_data.get_running_models()) if hasattr(self.bridge_data, 'get_running_models') else 0
        
        # Get stats from bridge_stats
        stats_parts = []
        
        # Add kudos per hour if available
        if "kudos_per_hour" in bridge_stats.stats:
            kudos_val = bridge_stats.stats['kudos_per_hour']
            # Format kudos value - if over 1000, use K format
            if kudos_val >= 1000:
                kudos_str = f"{kudos_val/1000:.1f}K"
            else:
                kudos_str = f"{kudos_val}"
            # Add kudos with extra spacing for growing numbers
            stats_parts.append(f"🌟 {kudos_str:<5} kudos/hr")
        
        # Add jobs per hour if available
        if "jobs_per_hour" in bridge_stats.stats:
            jobs_val = bridge_stats.stats['jobs_per_hour']
            # Format jobs value - if over 1000, use K format
            if jobs_val >= 1000:
                jobs_str = f"{jobs_val/1000:.1f}K"
            else:
                jobs_str = f"{jobs_val}"
            # Add jobs with extra spacing for growing numbers
            stats_parts.append(f"🔄 {jobs_str:<4}jobs/hr")
        
        # Show time since last job if we have that info
        last_job_str = ""
        if _last_job_completed is not None:
            time_since_job = current_time - _last_job_completed
            last_job_str = f"⏱️ Last job: {self._format_time_period(time_since_job)} ago"
            
            # Add kudos from last job if available
            if _last_job_info and 'kudos' in _last_job_info:
                last_job_str += f" ({_last_job_info['kudos']} kudos)"
                
            # Add model from last job if available
            if _last_job_info and 'model' in _last_job_info:
                model_name = _last_job_info['model']
                # Truncate model name if too long
                if len(model_name) > 15:
                    model_name = model_name[:12] + "..."
                last_job_str += f" [{model_name}]"
        
        # Build status message with cool indicators
        # Choose a random waiting message occasionally to add variety
        waiting_messages = [
            "⏳ Hunting for jobs...",
            "⏳ Searching the grid...",
            "⏳ Standing by...",
            "⏳ Grid scanning...",
            "⏳ Awaiting inference work..."
        ]
        
        # Choose a message based on waiting time
        waiting_time = current_time - _waiting_start_time
        if waiting_time > 300:  # More than 5 minutes
            waiting_idx = int((current_time // 30) % len(waiting_messages))  # Change message every 30 seconds
            wait_msg = waiting_messages[waiting_idx]
        else:
            wait_msg = "⏳ Waiting for jobs..."
            
        # COLUMN DEFINITIONS - all messages must adhere to these column widths
        # COL1: Status message (21 chars) | COL2: Thread info (18 chars) | COL3: Stats (variable)
        
        # Format the status message with colorful indicators - note we use exactly 21 chars
        status_msg = f"{wait_msg:<21}"
        
        # Format thread info - fixed width of 16 chars (reduced to tighten spacing)
        thread_msg = f"👥 Threads: {worker_count}/{self.bridge_data.max_threads}"
        thread_col = f"{thread_msg:<16}"  # Reduced width to tighten spacing
        
        # Build the message with consistent pipe spacing
        message_parts = [status_msg]
            
        # Add thread column with proper pipe spacing
        message_parts.append(f"| {thread_col}")
        
        # Always add at least one pipe after threads for consistent alignment
        if not stats_parts:
            message_parts.append("|")
        else:
            # Add stats with consistent separator style
            for stat in stats_parts:
                message_parts.append(f"| {stat}")
        
        # Log the status with consistent formatting - pipes with exact spacing
        formatted_message = "".join(message_parts)
        
        logger.info(formatted_message)
        
        # Reset counter and update timestamp
        _status_counter = 0
        _last_status_update = current_time

    def _format_time_period(self, seconds):
        """Format time period in a human-readable way"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


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
