"""SQLite-backed ingestion queue."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteIngestQueue:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    applied INTEGER NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_vectors (
                    job_id TEXT NOT NULL,
                    vector_id TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                )
                """
            )

    def enqueue(self, vectors: list[dict[str, Any]]) -> tuple[str, int]:
        if not vectors:
            raise ValueError("vectors must not be empty")

        job_id = str(uuid.uuid4())
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs(job_id, status, applied, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, "queued", 0, None, now, now),
            )
            conn.executemany(
                "INSERT INTO job_vectors(job_id, vector_id, vector_json) VALUES (?, ?, ?)",
                [
                    (job_id, str(vector["id"]), json.dumps(vector["vector"]))
                    for vector in vectors
                ],
            )
        return job_id, len(vectors)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT job_id, status, applied, error, created_at, updated_at FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return None
        return {
            "job_id": row[0],
            "status": row[1],
            "applied": row[2],
            "error": row[3],
            "created_at": row[4],
            "updated_at": row[5],
        }

    def queue_depth(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'queued'").fetchone()
        return int(row[0])

    def claim_next_job(self) -> tuple[str, list[tuple[str, list[float]]]] | None:
        with self._connect() as conn:
            conn.isolation_level = "IMMEDIATE"
            row = conn.execute(
                "SELECT job_id FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None

            job_id = row[0]
            updated = conn.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? WHERE job_id = ? AND status = 'queued'",
                (_utc_now(), job_id),
            )
            if updated.rowcount != 1:
                return None

            vector_rows = conn.execute(
                "SELECT vector_id, vector_json FROM job_vectors WHERE job_id = ?",
                (job_id,),
            ).fetchall()

        vectors: list[tuple[str, list[float]]] = []
        for vector_id, vector_json in vector_rows:
            parsed = json.loads(vector_json)
            if not isinstance(parsed, list):
                raise ValueError("Stored vector payload is invalid")
            vectors.append((vector_id, parsed))
        return job_id, vectors

    def mark_done(self, job_id: str, applied: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'done', applied = ?, updated_at = ? WHERE job_id = ?",
                (applied, _utc_now(), job_id),
            )

    def mark_failed(self, job_id: str, applied: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', applied = ?, error = ?, updated_at = ? WHERE job_id = ?",
                (applied, error, _utc_now(), job_id),
            )
