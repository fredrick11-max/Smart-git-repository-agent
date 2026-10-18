"""Agent 2 - Commit Classifier.

Combines three kinds of evidence (message, file paths, diff) and keeps a score per category.
Every decision stores a human-readable reason, so results can be explained.
"""
import re

from backend.analysis import CATEGORIES
from backend.file_types import is_doc_path, is_test_path

PREFIX_MAP = {
    "feat": "feature", "feature": "feature", "fix": "bug_fix", "bugfix": "bug_fix", "hotfix": "bug_fix",
    "refactor": "refactoring", "perf": "refactoring", "docs": "documentation", "doc": "documentation",
    "test": "testing", "tests": "testing",
}
CONVENTIONAL = re.compile(r"^(\w+)(\([^)]*\))?!?:\s")

KEYWORDS = [
    ("bug_fix", 2, r"\b(fix|fixes|fixed|fixing|bug|bugs|bugfix|hotfix|patch|resolve|resolves|resolved|crash|crashes|error|issue|regression|correct|corrected)\b"),
    ("feature", 1, r"\b(add|adds|added|implement|implements|implemented|introduce|introduces|feature|new|support|create|created|enable)\b"),
    ("refactoring", 2, r"\b(refactor|refactors|refactored|restructure|reorganize|reorganise|cleanup|clean up|rename|renamed|simplify|simplified|extract|extracted|rewrite|optimi[sz]e|optimi[sz]ed|move|moved)\b"),
    ("documentation", 2, r"\b(doc|docs|documentation|readme|comment|comments|docstring|changelog|typo|usage)\b"),
    ("testing", 2, r"\b(test|tests|testing|pytest|unittest|coverage|spec)\b"),
]
PRIORITY = ["bug_fix", "feature", "refactoring", "documentation", "testing"]


def classify_commit(commit: dict) -> dict:
    scores = {cat: 0 for cat in PRIORITY}
    reasons = {cat: [] for cat in PRIORITY}
    subject = commit["message"].lower()

    if commit.get("is_merge") or subject.startswith("merge "):
        return {"category": "other", "confidence": "high", "reason": "merge commit"}

    match = CONVENTIONAL.match(subject)
    if match and match.group(1) in PREFIX_MAP:
        cat = PREFIX_MAP[match.group(1)]
        scores[cat] += 5
        reasons[cat].append(f"message prefix '{match.group(1)}:'")

    for cat, weight, pattern in KEYWORDS:
        found = re.search(pattern, subject)
        if found:
            scores[cat] += weight
            reasons[cat].append(f"message contains '{found.group(0)}'")

    paths = [f["path"] for f in commit["files"]]
    if paths:
        if all(is_doc_path(p) for p in paths):
            scores["documentation"] += 3
            reasons["documentation"].append("only documentation files changed")
        elif all(is_test_path(p) for p in paths):
            scores["testing"] += 3
            reasons["testing"].append("only test files changed")
        elif any(is_test_path(p) for p in paths):
            scores["testing"] += 1
            reasons["testing"].append("test files changed")

    diff = commit.get("diff_excerpt", "")
    added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    ins, dele = commit["insertions"], commit["deletions"]
    if "new file mode" in diff and ins > 0:
        scores["feature"] += 1
        reasons["feature"].append("adds new file(s)")
    elif ins >= 5 and dele >= 5 and 0.5 <= dele / ins <= 2:
        scores["refactoring"] += 1
        reasons["refactoring"].append("similar amount of code added and removed")
    if any("def test_" in l or "assert " in l for l in added):
        scores["testing"] += 1
        reasons["testing"].append("diff adds test code")

    best = max(PRIORITY, key=lambda c: (scores[c], -PRIORITY.index(c)))
    if scores[best] == 0:
        return {"category": "other", "confidence": "low", "reason": "no strong evidence in message, files or diff"}
    confidence = "high" if scores[best] >= 5 else "medium" if scores[best] >= 3 else "low"
    return {"category": best, "confidence": confidence, "reason": "; ".join(reasons[best])}


class CommitClassifier:
    name = "Commit Classifier"

    def run(self, commits: list) -> list:
        for commit in commits:
            result = classify_commit(commit)
            commit["category"] = result["category"]
            commit["confidence"] = result["confidence"]
            commit["reason"] = result["reason"]
        assert all(c["category"] in CATEGORIES for c in commits)
        return commits
