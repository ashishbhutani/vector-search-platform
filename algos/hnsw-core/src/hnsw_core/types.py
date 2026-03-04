"""Shared type aliases for hnsw-core."""

from __future__ import annotations

from typing import Sequence, Union

VectorId = Union[str, int]
VectorLike = Sequence[float]
