"""FastAPI application scaffolding."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .models import (
    IngestRequest,
    IngestResponse,
    JobResponse,
    QueryRequest,
    QueryResponse,
    SnapshotRequest,
)
from .queue_sqlite import SQLiteIngestQueue
from .routing import create_router
from .state import ServiceState
from .worker import IngestWorker


def create_app(
    state: ServiceState,
    *,
    queue_db_path: str = ":memory:",
    start_worker: bool = False,
) -> FastAPI:
    if state.shard_router is None:
        state.shard_router = create_router(state.router_config)

    queue = SQLiteIngestQueue(queue_db_path)
    worker = IngestWorker(queue=queue, state=state)

    if start_worker:
        worker.start()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            worker.stop()

    app = FastAPI(title="vector-search-service", version="0.1.0", lifespan=lifespan)
    app.state.ingest_queue = queue
    app.state.ingest_worker = worker
    app.state.shard_router = state.shard_router
    app.state.router_config = state.router_config

    @app.get("/status")
    def status() -> dict[str, object]:
        payload = state.status_payload(
            queue_depth=queue.queue_depth(),
            worker_status=worker.status(),
        )
        payload["routing_strategy"] = state.router_config.strategy
        return payload

    @app.post("/query", response_model=QueryResponse)
    def query(request: QueryRequest) -> QueryResponse:
        try:
            results = state.index.search(
                query=request.vector,
                k=request.k,
                ef_search=request.ef_search,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        neighbors = [{"id": item[0], "score": item[1]} for item in results]
        return QueryResponse(
            neighbors=neighbors,
            index_version=state.index_version,
            partial_results=False,
        )

    @app.post("/vectors", response_model=IngestResponse)
    def vectors(request: IngestRequest) -> IngestResponse:
        payload = [{"id": record.id, "vector": record.vector} for record in request.vectors]
        try:
            job_id, queued = queue.enqueue(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return IngestResponse(job_id=job_id, queued=queued)

    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str) -> JobResponse:
        job = queue.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return JobResponse(**job)

    @app.post("/snapshot")
    def snapshot(request: SnapshotRequest) -> dict[str, object]:
        return state.save_snapshot(request.path)

    return app
