from pathlib import Path

import json
import pytest

from hnsw_core import HNSWIndex


def test_snapshot_roundtrip(tmp_path: Path) -> None:
    index = HNSWIndex(dim=2, metric="cosine", m=8, ef_construction=100)
    index.add([1.0, 0.0], id="a")
    index.add([0.0, 1.0], id="b")

    snapshot = tmp_path / "hnsw.json"
    index.save(snapshot)

    restored = HNSWIndex.load(snapshot)
    assert restored.dim == 2
    assert restored.metric == "cosine"
    assert len(restored) == 2
    assert restored.search([1.0, 0.0], k=1)[0][0] == "a"


def test_snapshot_metadata_fields_exist(tmp_path: Path) -> None:
    index = HNSWIndex(dim=2)
    index.add([1.0, 2.0], id=1)

    snapshot = tmp_path / "metadata.json"
    index.save(snapshot)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))

    required = {
        "format_version",
        "algo",
        "dim",
        "metric",
        "m",
        "ef_construction",
        "node_count",
        "index_version",
        "created_at",
    }
    assert required.issubset(set(payload.keys()))


def test_unsupported_format_version_rejected(tmp_path: Path) -> None:
    snapshot = tmp_path / "bad.json"
    snapshot.write_text(
        json.dumps(
            {
                "format_version": 999,
                "dim": 2,
                "metric": "l2",
                "m": 16,
                "ef_construction": 200,
                "ids": [],
                "vectors": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        HNSWIndex.load(snapshot)
