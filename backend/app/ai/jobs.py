import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict


class JobManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def submit(self, name: str, fn: Callable):
        job_id = str(uuid.uuid4())
        with self.lock:
            self.jobs[job_id] = {
                "id": job_id,
                "name": name,
                "status": "queued",
                "progress": 0.0,
                "message": "Queued",
                "result": None,
                "error": None,
                "created_at": datetime.utcnow().isoformat(),
            }

        def progress(value: float, message: str):
            with self.lock:
                if job_id in self.jobs:
                    self.jobs[job_id]["progress"] = max(0.0, min(1.0, float(value)))
                    self.jobs[job_id]["message"] = message

        def run():
            with self.lock:
                self.jobs[job_id]["status"] = "running"
                self.jobs[job_id]["message"] = "Running"
            try:
                result = fn(progress)
                with self.lock:
                    self.jobs[job_id]["status"] = "done"
                    self.jobs[job_id]["progress"] = 1.0
                    self.jobs[job_id]["message"] = "Done"
                    self.jobs[job_id]["result"] = result
            except Exception as exc:
                with self.lock:
                    self.jobs[job_id]["status"] = "error"
                    self.jobs[job_id]["message"] = str(exc)
                    self.jobs[job_id]["error"] = traceback.format_exc()

        self.executor.submit(run)
        return self.jobs[job_id].copy()

    def get(self, job_id: str):
        with self.lock:
            job = self.jobs.get(job_id)
            return job.copy() if job else None

    def recent(self):
        with self.lock:
            return list(self.jobs.values())[-10:][::-1]


jobs = JobManager()
