"""Creates a small local Git repository with real commits for testing the app.

Usage:  python examples/create_sample_repo.py [target_folder]
Default target: examples/sample_repo
"""
import sys
import time
from pathlib import Path

CALC_V1 = '''def add(a, b):
    return a + b


def subtract(a, b):
    return a - b
'''
CALC_V2 = CALC_V1 + '''

def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b
'''
CALC_V3 = CALC_V2.replace("    return a / b\n", "    if b == 0:\n        raise ValueError(\"Cannot divide by zero\")\n    return a / b\n")
CALC_V4 = '''def _check_numbers(*values):
    for value in values:
        if not isinstance(value, (int, float)):
            raise TypeError("Only numbers are allowed")


def add(a, b):
    _check_numbers(a, b)
    return a + b


def subtract(a, b):
    _check_numbers(a, b)
    return a - b


def multiply(a, b):
    _check_numbers(a, b)
    return a * b


def divide(a, b):
    _check_numbers(a, b)
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
TESTS = '''import unittest

from calc import add, divide


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError):
            divide(1, 0)
'''
README = "# Calculator\n\nA tiny calculator library.\n\n## Usage\n\n```python\nfrom calc import add\nprint(add(1, 2))\n```\n"
POWER = '\n\ndef power(a, b):\n    return a ** b\n'


def create_sample_repo(target=None) -> Path:
    """Create (or reuse) the sample repository and return its path."""
    from git import Actor, Repo

    path = Path(target) if target else Path(__file__).resolve().parent / "sample_repo"
    if (path / ".git").exists():
        return path
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    alice, bob = Actor("Alice Dev", "alice@example.com"), Actor("Bob Coder", "bob@example.com")
    now = int(time.time())

    def commit(files: dict, message: str, actor, days_ago: float):
        for name, content in files.items():
            file_path = path / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        repo.index.add(list(files))
        stamp = f"{int(now - days_ago * 86400)} +0000"
        repo.index.commit(message, author=actor, committer=actor, author_date=stamp, commit_date=stamp)

    commit({"calc.py": CALC_V1}, "Add calculator module with add and subtract", alice, 6)
    commit({"calc.py": CALC_V2}, "Add multiply and divide functions", alice, 5)
    commit({"calc.py": CALC_V3}, "Fix division by zero crash in divide()", bob, 4)
    commit({"calc.py": CALC_V4}, "Refactor calculator: extract input validation helper", alice, 3)
    commit({"tests/test_calc.py": TESTS}, "Add unit tests for calculator", bob, 2)
    commit({"README.md": README}, "Add README with usage instructions", alice, 1)

    main = repo.active_branch
    branch = repo.create_head("feature/power")
    branch.checkout()
    commit({"calc.py": CALC_V4 + POWER}, "Add power function", bob, 0.5)
    main.checkout()
    return path


if __name__ == "__main__":
    created = create_sample_repo(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"Sample repository ready: {created}")
