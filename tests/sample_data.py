"""Synthetic commit data so the analysis pipeline can be tested without Git."""
from datetime import datetime, timedelta, timezone


def make_commit(i, message, files, author="Alice", days_ago=1, diff=""):
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    file_rows = [{"path": p, "insertions": a, "deletions": d} for p, a, d in files]
    return {
        "sha": f"{i:040x}", "short_sha": f"{i:07x}", "author": author, "email": f"{author.lower()}@example.com",
        "date": when.isoformat(), "message": message, "body": "", "is_merge": False, "files": file_rows,
        "files_changed": len(file_rows), "insertions": sum(f["insertions"] for f in file_rows),
        "deletions": sum(f["deletions"] for f in file_rows), "diff_excerpt": diff,
    }


def sample_commits():
    return [
        make_commit(6, "Add README with usage instructions", [("README.md", 10, 0)], "Alice", 1),
        make_commit(5, "Add unit tests for calculator", [("tests/test_calc.py", 12, 0)], "Bob", 2),
        make_commit(4, "Refactor calculator: extract input validation helper", [("calc.py", 20, 15)], "Alice", 3),
        make_commit(3, "Fix division by zero crash in divide()", [("calc.py", 3, 1)], "Bob", 4),
        make_commit(2, "Add multiply and divide functions", [("calc.py", 8, 0)], "Alice", 5),
        make_commit(1, "Add calculator module with add and subtract", [("calc.py", 6, 0)], "Alice", 6,
                    diff="diff --git a/calc.py b/calc.py\nnew file mode 100644\n+def add(a, b):"),
    ]


def sample_repo_info():
    return {
        "name": "sample", "source": "memory", "remote_url": "", "active_branch": "main", "total_commits": 6,
        "branches": [{"name": "main", "remote": False, "is_active": True, "last_commit": "2026-10-17T10:00:00+00:00", "last_author": "Alice"}],
        "branch_count": 1, "tag_count": 0, "file_count": 3,
        "languages": [{"language": "Python", "bytes": 500, "percent": 100.0}],
        "important_files": ["README.md"], "has_tests": True, "top_level": [],
    }
