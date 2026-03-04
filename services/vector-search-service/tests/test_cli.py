import argparse
import json
from pathlib import Path

from hnsw_core import HNSWIndex
from vector_search_service.cli import build_parser, command_build


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_build_command_creates_snapshot(tmp_path: Path) -> None:
    vectors_file = tmp_path / "vectors.jsonl"
    _write_jsonl(
        vectors_file,
        [
            {"id": "a", "vector": [0.0, 0.0]},
            {"id": "b", "vector": [1.0, 0.0]},
        ],
    )

    out_path = tmp_path / "index.json"
    args = argparse.Namespace(
        vectors_dir=str(vectors_file),
        out=str(out_path),
        metric="l2",
        dim=2,
        m=16,
        ef_construction=200,
    )

    code = command_build(args)
    assert code == 0
    assert out_path.exists()

    index = HNSWIndex.load(out_path)
    assert len(index) == 2
    assert index.search([0.0, 0.0], k=1)[0][0] == "a"


def test_build_parser_has_expected_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["build", "--vectors-dir", "./x", "--out", "./y", "--dim", "2"]
    )
    assert args.command == "build"


def test_build_requires_jsonl_files(tmp_path: Path) -> None:
    args = argparse.Namespace(
        vectors_dir=str(tmp_path),
        out=str(tmp_path / "index.json"),
        metric="l2",
        dim=2,
        m=16,
        ef_construction=200,
    )

    try:
        command_build(args)
        assert False, "Expected ValueError"
    except ValueError:
        pass
