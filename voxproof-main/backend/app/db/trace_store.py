import sqlite3
import json
from datetime import datetime
from app.config import DB_PATH
from app.schemas import SuiteResult


class TraceStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suite_name TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    scenario_id TEXT NOT NULL,
                    events_json TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                )
            """)
            conn.commit()

    def save_run(self, result: SuiteResult) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO runs (suite_name, result_json, created_at) VALUES (?, ?, ?)",
                (result.suite_name, result.model_dump_json(), datetime.now().isoformat()),
            )
            run_id = cursor.lastrowid
            for sr in result.results:
                conn.execute(
                    "INSERT INTO traces (run_id, scenario_id, events_json) VALUES (?, ?, ?)",
                    (run_id, sr.scenario_id, json.dumps([e.model_dump() for e in sr.trace])),
                )
            conn.commit()
            return run_id

    def get_run(self, run_id: int) -> SuiteResult | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT result_json FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row:
                return SuiteResult.model_validate_json(row[0])
        return None

    def list_runs(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, suite_name, created_at FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [{"id": r[0], "suite_name": r[1], "created_at": r[2]} for r in rows]
