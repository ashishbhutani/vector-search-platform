"""Distance function contracts for hnsw-core."""

from __future__ import annotations

from typing import Literal

import numpy as np

MetricName = Literal["l2", "cosine", "dot"]


def distance(a: np.ndarray, b: np.ndarray, metric: MetricName) -> float:
    raise NotImplementedError("Implemented in P1-02")
