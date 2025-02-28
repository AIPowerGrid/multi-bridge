"""This is the scribe worker, it's the main workhorse that deals with getting requests, and spawning data processing"""
import time

from worker.jobs.poppers import ScribePopper
from worker.jobs.scribe import ScribeHordeJob
from worker.workers.framework import WorkerFramework
from loguru import logger


class ScribeWorker(WorkerFramework):
    def __init__(self, this_bridge_data):
        super().__init__(None, this_bridge_data)
        self.PopperClass = ScribePopper
        self.JobClass = ScribeHordeJob

    def can_process_jobs(self):
        # Check availability based on API type
        if self.bridge_data.api_type == "openai":
            openai_avail = self.bridge_data.openai_available
            if not openai_avail:
                # Try to reload the config every 5 seconds until the OpenAI connection is established
                self.last_config_reload = time.time() - 55
                logger.debug("OpenAI API not available, will retry configuration reload shortly")
            return openai_avail
        else:
            # Default to KoboldAI
            kai_avail = self.bridge_data.kai_available
            if not kai_avail:
                # We do this to allow the worker to try and reload the config every 5 seconds until the KAI server is up
                self.last_config_reload = time.time() - 55
                logger.debug("KoboldAI not available, will retry configuration reload shortly")
            return kai_avail

    # We want this to be extendable as well
    def add_job_to_queue(self):
        super().add_job_to_queue()

    def pop_job(self):
        return super().pop_job()

    def get_running_models(self):
        running_job_models = [job.current_model for job_thread, start_time, job in self.running_jobs]
        queued_jobs_models = [job.current_model for job in self.waiting_jobs]
        return list(set(running_job_models + queued_jobs_models))
