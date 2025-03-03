"""Get and process a job from the horde"""
import contextlib
import copy
import json
import sys
import threading
import time

import requests

from worker.enums import JobStatus
from worker.logger import logger


class HordeJobFramework:
    """Get and process a job from the horde"""

    retry_interval = 1

    def __init__(self, mm, bd, pop):
        self.model_manager = mm
        # Make a shallow copy of bridge data instead of deep copy to save memory
        self.bridge_data = bd
        self.pop = pop
        self.loop_retry = 0
        self.status = JobStatus.INIT
        self.start_time = time.time()
        self.process_time = time.time()
        self.stale_time = None
        self.submit_dict = {}
        self.headers = {"apikey": self.bridge_data.api_key}
        self.out_of_memory = False

    def is_finished(self):
        """Check if the job is finished"""
        return self.status not in [JobStatus.WORKING, JobStatus.POLLING, JobStatus.INIT]

    def is_polling(self):
        """Check if the job is polling"""
        return self.status in [JobStatus.POLLING]

    def is_finalizing(self):
        """True if generation has finished even if upload is still remaining"""
        return self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]

    def is_stale(self):
        """Check if the job is stale"""
        if time.time() - self.start_time > 1200:
            return True
        if not self.stale_time:
            return False
        # Jobs which haven't started yet are not considered stale.
        if self.status == JobStatus.INIT:
            return False
        # If the job has been processing longer than stale time, it is stale
        return time.time() > self.stale_time

    def is_faulted(self):
        """Check if the job is faulted"""
        return self.status in [JobStatus.FAULTED, JobStatus.FINALIZING_FAULTED, JobStatus.DONE_FAULTED]

    def is_out_of_memory(self):
        """Check if the job is out of memory"""
        return self.out_of_memory

    @logger.catch(reraise=True)
    def start_job(self):
        """Start a job from a pop request
        The base class just finalizes the job instantly"""
        try:
            # Process the request
            self.status = JobStatus.WORKING
            # The extending class would do stuff here to process the job
            self.status = JobStatus.DONE
            self.submit_dict = {"success": True}
        except Exception as e:
            logger.error("Error while working: {}", e)
            self.status = JobStatus.FAULTED
            if "out of memory" in str(e).lower():
                self.out_of_memory = True

    def start_submit_thread(self):
        """Start a new thread to submit the job result"""
        submit_thread = threading.Thread(target=self.submit_job)
        submit_thread.daemon = True
        submit_thread.start()

    def submit_job(self, endpoint):
        """Submit a job to the API"""
        self.prepare_submit_payload()
        if self.status in [JobStatus.FAULTED, JobStatus.FINALIZING_FAULTED]:
            self.submit_dict = {"success": False, "state": "faulted"}

        with requests.Session() as s:
            s.headers.update(self.headers)
            # Always a good idea to set a timeout in case the horde is down
            while True:
                try:
                    submit_req = s.post(
                        f"{self.bridge_data.horde_url}{endpoint}",
                        json=self.submit_dict,
                        timeout=30,
                    )
                    if submit_req.status_code in [502, 503, 408, 500]:
                        self.loop_retry += 1
                        if self.loop_retry > 3:
                            logger.error(
                                f"Could not submit job after 3 retries: "
                                f"{submit_req.status_code=}, {submit_req.text=}",
                            )
                            if self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]:
                                self.status = JobStatus.DONE_FAULTED
                            else:
                                self.status = JobStatus.FAULTED
                            return
                        time.sleep(self.retry_interval)
                        continue
                    self.loop_retry = 0
                    if submit_req.status_code == 404:
                        logger.warning(f"Job already submitted {submit_req.text=}")
                        # This will happen if the server already has this job submitted
                        if self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]:
                            self.status = JobStatus.DONE
                        return
                    if not submit_req.ok:
                        logger.warning(
                            f"Failed to submit job. "
                            f"{submit_req.status_code=}, {submit_req.text=}, {self.status=}"
                        )
                        if self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]:
                            self.status = JobStatus.DONE
                        return
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
                    self.loop_retry += 1
                    if self.loop_retry > 3:
                        logger.error(f"Retrieving job failed after 3 retries: {e}")
                        if self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]:
                            self.status = JobStatus.DONE_FAULTED
                        else:
                            self.status = JobStatus.FAULTED
                        return
                    time.sleep(self.retry_interval)

        submit_json = submit_req.json()
        
        # Mark job as done and clear any unneeded data to help with memory usage
        if self.status in [JobStatus.FINALIZING, JobStatus.FINALIZING_FAULTED]:
            self.status = JobStatus.DONE
        
        # Help garbage collection by clearing large data
        self.submit_dict = {}
        self.pop = None
        
        # Process any post-submit tasks if needed
        self.post_submit_tasks(submit_req)

    def prepare_submit_payload(self):
        """Prepare payload for submission"""
        pass

    def post_submit_tasks(self, submit_req):
        """Process any post-submit tasks"""
        pass
