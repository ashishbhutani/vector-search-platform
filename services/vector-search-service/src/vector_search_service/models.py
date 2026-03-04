"""Pydantic request and response contracts."""

from __future__ import annotations

from pydantic import BaseModel


class QueryRequest(BaseModel):
    vector: list[float]
    k: int
    ef_search: int | None = None


class Neighbor(BaseModel):
    id: str | int
    score: float


class QueryResponse(BaseModel):
    neighbors: list[Neighbor]
    index_version: int
    partial_results: bool = False


class VectorRecord(BaseModel):
    id: str | int
    vector: list[float]


class IngestRequest(BaseModel):
    vectors: list[VectorRecord]
