"""Local registry and transactional approval artifacts; all values parameterized."""

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

from review_tools import fingerprint


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ReviewStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "artifacts.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, router TEXT NOT NULL, created TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS artifacts (run_id TEXT PRIMARY KEY, hash TEXT NOT NULL, body TEXT NOT NULL, approved_at TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=20)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def valid_id(run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("Invalid review ID.")

    def register(self, run_id, router):
        self.valid_id(run_id)
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?)", (run_id, router, utc_now()))

    def exists(self, run_id):
        self.valid_id(run_id)
        with self.connect() as db:
            return db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone() is not None

    def list_runs(self):
        with self.connect() as db:
            return [{"id": row[0], "router": row[1], "created": row[2]}
                    for row in db.execute("SELECT id, router, created FROM runs ORDER BY created DESC")]

    def save_approved(self, state):
        self.valid_id(state["run_id"])
        report = state.get("report")
        expected = state.get("report_hash")
        if state.get("status") != "approved" or not report or not expected or (
                state.get("approved_hash") != expected or fingerprint(report) != expected):
            raise ValueError("Exact report approval required.")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT hash FROM artifacts WHERE run_id=?", (state["run_id"],)).fetchone()
            if previous:
                if previous[0] != expected:
                    raise ValueError("A different artifact already exists for this review.")
            else:
                db.execute("INSERT INTO artifacts VALUES (?, ?, ?, ?)",
                           (state["run_id"], expected, json.dumps(report, ensure_ascii=False), utc_now()))
        return {"run_id": state["run_id"], "sha256": expected, "storage": "approved report in local SQLite"}

    def artifact(self, run_id):
        self.valid_id(run_id)
        with self.connect() as db:
            row = db.execute("SELECT body FROM artifacts WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None
