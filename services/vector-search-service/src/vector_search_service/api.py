"""FastAPI application scaffolding."""

from __future__ import annotations

from fastapi import FastAPI



def create_app() -> FastAPI:
    app = FastAPI(title="vector-search-service", version="0.1.0")

    @app.get("/status")
    def status() -> dict[str, str]:
        return {"status": "bootstrapped"}

    return app
