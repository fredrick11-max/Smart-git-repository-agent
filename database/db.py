"""SQLite storage for analysis history (standard library sqlite3 only)."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_name TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    commit_count INTEGER NOT NULL,
    ai_used INTEGER NOT NULL,
    summary_preview TEXT,
    result_json TEXT NOT NULL
)
"""


class AnalysisDatabase:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(SCHEMA)

    def _connect(self):
        return sqlite3.connect(self.path)

    def save_analysis(self, analysis: dict) -> int:
        row = (
            analysis["repository"]["name"], analysis["meta"]["source"], analysis["meta"]["analyzed_at"],
            len(analysis["commits"]), int(analysis["meta"]["ai_used"]),
            analysis["summary"]["summary"][:300], json.dumps(analysis, default=str),
        )
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "INSERT INTO analyses (repo_name, source, created_at, commit_count, ai_used, summary_preview, result_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", row)
            return cursor.lastrowid

    def list_analyses(self, limit: int = 50) -> list:
        with closing(self._connect()) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, repo_name, source, created_at, commit_count, ai_used, summary_preview "
                "FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_analysis(self, analysis_id: int):
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT result_json FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        data["id"] = analysis_id
        return data

    def delete_analysis(self, analysis_id: int) -> bool:
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,)).rowcount > 0
