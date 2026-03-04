"""FastAPI application scaffolding."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .models import QueryRequest, QueryResponse, SnapshotRequest
from .state import ServiceState


def create_app(state: ServiceState) -> FastAPI:
    app = FastAPI(title="vector-search-service", version="0.1.0")

    @app.get("/status")
    def status() -> dict[str, object]:
        return state.status_payload()

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

    @app.post("/snapshot")
    def snapshot(request: SnapshotRequest) -> dict[str, object]:
        return state.save_snapshot(request.path)

    return app
