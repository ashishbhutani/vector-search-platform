"""Background worker that applies queued vector ingestion jobs."""

from __future__ import annotations

import threading
import time

from .queue_sqlite import SQLiteIngestQueue
from .state import ServiceState


class IngestWorker:
    def __init__(
        self,
        queue: SQLiteIngestQueue,
        state: ServiceState,
        poll_interval_sec: float = 0.2,
    ) -> None:
        self.queue = queue
        self.state = state
        self.poll_interval_sec = poll_interval_sec
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._status = "stopped"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._status = "idle"
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._status = "stopped"

    def status(self) -> str:
        return self._status

    def _loop(self) -> None:
        while not self._stop.is_set():
            processed = self.run_once()
            if not processed:
                self._status = "idle"
                time.sleep(self.poll_interval_sec)

    def run_once(self) -> bool:
        claimed = self.queue.claim_next_job()
        if claimed is None:
            return False

        job_id, vectors = claimed
        self._status = "running"
        applied = 0
        try:
            for vector_id, vector in vectors:
                self.state.index.add(vector, id=vector_id)
                applied += 1
            self.state.bump_index_version(applied)
            self.queue.mark_done(job_id, applied)
        except Exception as exc:  # pragma: no cover - defensive path
            self.queue.mark_failed(job_id, applied, str(exc))
        return True
