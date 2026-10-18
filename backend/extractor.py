"""Reads real data from a GitPython Repo object: commits, branches and file tree.

Only fixed, read-only Git commands are used (log, show, rev-list). No repository code is executed.
"""
import os
from collections import Counter

from backend.config import MAX_DIFF_CHARS, MAX_DIFF_COMMITS
from backend.file_types import SKIP_DIRS, is_test_path, language_of

IMPORTANT_NAMES = (
    "readme", "license", "requirements.txt", "pyproject.toml", "setup.py", "package.json",
    "dockerfile", "docker-compose.yml", "makefile", "contributing", ".gitignore", "pom.xml",
)


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def _scrub(text: str) -> str:
    """Remove undecodable characters so the text can be stored in JSON / SQLite."""
    return text.encode("utf-8", "replace").decode("utf-8")


def extract_commits(repo, max_commits: int, max_diff_commits: int = MAX_DIFF_COMMITS,
                    max_diff_chars: int = MAX_DIFF_CHARS) -> list:
    """Return the newest `max_commits` commits as plain dictionaries (newest first)."""
    commits = []
    for index, commit in enumerate(repo.iter_commits("HEAD", max_count=max_commits)):
        message = _text(commit.message).strip()
        subject = message.splitlines()[0].strip() if message else "(no message)"
        try:
            file_stats = commit.stats.files
        except Exception:
            file_stats = {}
        files = [
            {"path": path, "insertions": int(s.get("insertions", 0)), "deletions": int(s.get("deletions", 0))}
            for path, s in file_stats.items()
        ]
        diff_excerpt = ""
        if index < max_diff_commits:
            try:
                raw = repo.git.show(
                    commit.hexsha, "--format=", "--unified=0", "--no-color", "--no-ext-diff", "--no-textconv"
                )
                diff_excerpt = _scrub(raw)[:max_diff_chars]
            except Exception:
                diff_excerpt = ""
        commits.append({
            "sha": commit.hexsha,
            "short_sha": commit.hexsha[:7],
            "author": _scrub(_text(commit.author.name) or "Unknown"),
            "email": _scrub(_text(commit.author.email) or "").lower(),
            "date": commit.committed_datetime.isoformat(),
            "message": _scrub(subject),
            "body": _scrub("\n".join(message.splitlines()[1:]).strip())[:500],
            "is_merge": len(commit.parents) > 1,
            "files": files,
            "files_changed": len(files),
            "insertions": sum(f["insertions"] for f in files),
            "deletions": sum(f["deletions"] for f in files),
            "diff_excerpt": diff_excerpt,
        })
    return commits


def get_branches(repo, limit: int = 30) -> list:
    try:
        active = repo.active_branch.name
    except (TypeError, ValueError):
        active = None
    branches, seen = [], set()
    for head in repo.heads:
        seen.add(head.name)
        branches.append({
            "name": head.name, "remote": False, "is_active": head.name == active,
            "last_commit": head.commit.committed_datetime.isoformat(),
            "last_author": _text(head.commit.author.name),
        })
    for remote in repo.remotes:
        try:
            refs = list(remote.refs)
        except Exception:
            refs = []
        for ref in refs:
            short = ref.name.split("/", 1)[-1]
            if short == "HEAD" or short in seen:
                continue
            seen.add(short)
            branches.append({
                "name": ref.name, "remote": True, "is_active": False,
                "last_commit": ref.commit.committed_datetime.isoformat(),
                "last_author": _text(ref.commit.author.name),
            })
    return branches[:limit]


def scan_tree(repo, max_files: int = 5000) -> dict:
    """Look at the files in the latest commit: languages, important files, top-level layout."""
    languages, important, count, has_tests = Counter(), [], 0, False
    for item in repo.head.commit.tree.traverse():
        if getattr(item, "type", "") != "blob":
            continue
        count += 1
        if count > max_files:
            break
        path = item.path
        parts = path.lower().split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]):
            continue
        if is_test_path(path):
            has_tests = True
        lang = language_of(path)
        if lang:
            languages[lang] += int(getattr(item, "size", 0) or 0)
        top_level = len(parts) == 1 and parts[0].startswith(IMPORTANT_NAMES)
        if top_level or path.lower().startswith(".github/workflows/"):
            important.append(path)
    total = sum(languages.values()) or 1
    language_list = [
        {"language": name, "bytes": size, "percent": round(100 * size / total, 1)}
        for name, size in languages.most_common(8)
    ]
    top_level_entries = [
        {"name": entry.name, "type": "folder" if entry.type == "tree" else "file"}
        for entry in repo.head.commit.tree
    ][:40]
    return {
        "file_count": min(count, max_files), "languages": language_list,
        "important_files": sorted(important), "has_tests": has_tests,
        "top_level": top_level_entries,
    }


def total_commit_count(repo) -> int:
    try:
        return int(repo.git.rev_list("--count", "HEAD"))
    except Exception:
        return 0


def remote_url(repo) -> str:
    try:
        return repo.remotes.origin.url
    except Exception:
        return ""
