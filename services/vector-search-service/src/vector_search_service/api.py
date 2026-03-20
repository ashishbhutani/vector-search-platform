"""FastAPI application scaffolding."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from .cluster import HttpShardClient, ShardHealthRegistry
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
    if state.runtime_role not in {"gateway", "shard_node"}:
        raise ValueError("runtime_role must be 'gateway' or 'shard_node'")
    if state.health_registry is None:
        state.health_registry = ShardHealthRegistry()
    if state.shard_client is None:
        state.shard_client = HttpShardClient(timeout_sec=state.gateway_timeout_sec)

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

    def _refresh_gateway_health() -> None:
        if not state.shard_map:
            return
        for entry in state.shard_map:
            healthy = state.shard_client.is_healthy(entry.base_url, timeout_sec=0.2)
            state.health_registry.set_state(entry.shard_id, "healthy" if healthy else "unavailable")

    def _merge_neighbors(
        responses: list[dict[str, object]],
        *,
        k: int,
        partial_results: bool,
    ) -> QueryResponse:
        merged: list[dict[str, object]] = []
        max_index_version = 0
        for response in responses:
            neighbors = response.get("neighbors", [])
            if isinstance(neighbors, list):
                for row in neighbors:
                    if isinstance(row, dict) and "id" in row and "score" in row:
                        merged.append({"id": row["id"], "score": float(row["score"])})
            version = response.get("index_version")
            if isinstance(version, int):
                max_index_version = max(max_index_version, version)
        merged.sort(key=lambda row: row["score"])
        return QueryResponse(
            neighbors=merged[:k],
            index_version=max_index_version,
            partial_results=partial_results,
        )

    def _gateway_query(request: QueryRequest) -> QueryResponse:
        if not state.shard_map:
            raise HTTPException(status_code=503, detail="gateway shard map is not configured")
        _refresh_gateway_health()
        shard_ids = [entry.shard_id for entry in state.shard_map]
        healthy_ids = state.health_registry.healthy_shards(shard_ids)
        if not healthy_ids:
            return QueryResponse(neighbors=[], index_version=0, partial_results=True)

        top_n = (
            state.router_config.semantic_top_n
            if state.router_config.strategy == "semantic_lsh"
            else None
        )
        target_ids = state.shard_router.route_for_query(request, healthy_ids, top_n=top_n)
        if not target_ids:
            return QueryResponse(neighbors=[], index_version=0, partial_results=False)

        by_id = {entry.shard_id: entry for entry in state.shard_map}
        failures = 0
        responses: list[dict[str, object]] = []
        payload = {
            "vector": request.vector,
            "k": request.k,
            "ef_search": request.ef_search,
        }

        with ThreadPoolExecutor(max_workers=max(1, len(target_ids))) as pool:
            future_map = {}
            for shard_id in target_ids:
                entry = by_id.get(shard_id)
                if entry is None:
                    failures += 1
                    continue
                future = pool.submit(
                    state.shard_client.query_shard,
                    entry.base_url,
                    payload,
                    timeout_sec=state.gateway_timeout_sec,
                )
                future_map[future] = entry

            for future in as_completed(future_map):
                entry = future_map[future]
                try:
                    response = future.result()
                    responses.append(response)
                    state.health_registry.set_state(entry.shard_id, "healthy")
                except Exception:
                    failures += 1
                    state.health_registry.set_state(entry.shard_id, "unavailable")

        if not responses:
            return QueryResponse(neighbors=[], index_version=0, partial_results=True)
        return _merge_neighbors(
            responses,
            k=request.k,
            partial_results=(failures > 0),
        )

    def _gateway_ingest(request: IngestRequest) -> IngestResponse:
        if not state.shard_map:
            raise HTTPException(status_code=503, detail="gateway shard map is not configured")
        by_id = {entry.shard_id: entry for entry in state.shard_map}

        def _resolve_entry(shard_id: str):
            entry = by_id.get(shard_id)
            if entry is not None:
                return entry
            if shard_id.startswith("shard-"):
                raw_index = shard_id.removeprefix("shard-")
                if raw_index.isdigit():
                    idx = int(raw_index)
                    if 0 <= idx < len(state.shard_map):
                        return state.shard_map[idx]
            return None

        groups: dict[str, list[dict[str, object]]] = {}
        shard_count = len(state.shard_map)
        for record in request.vectors:
            shard_id = state.shard_router.route_for_ingest(record, shard_count=shard_count)
            groups.setdefault(shard_id, []).append({"id": record.id, "vector": record.vector})

        total_queued = 0
        for shard_id, vectors in groups.items():
            entry = _resolve_entry(shard_id)
            if entry is None:
                raise HTTPException(status_code=502, detail=f"router returned unknown shard '{shard_id}'")
            try:
                response = state.shard_client.ingest_shard(entry.base_url, {"vectors": vectors})
            except Exception as exc:
                state.health_registry.set_state(shard_id, "unavailable")
                raise HTTPException(status_code=502, detail=f"failed to ingest on shard '{shard_id}'") from exc

            queued = response.get("queued")
            if isinstance(queued, int):
                total_queued += queued
            state.health_registry.set_state(shard_id, "healthy")
        return IngestResponse(job_id=f"gw-{uuid4()}", queued=total_queued)

    @app.post("/query", response_model=QueryResponse)
    def query(request: QueryRequest) -> QueryResponse:
        if state.runtime_role == "gateway":
            return _gateway_query(request)

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
            shard_id=state.shard_id,
        )

    @app.post("/vectors", response_model=IngestResponse)
    def vectors(request: IngestRequest) -> IngestResponse:
        if state.runtime_role == "gateway":
            return _gateway_ingest(request)

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
