"""Deterministic statistics computed from the extracted commits (no AI involved)."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CATEGORIES = ["feature", "bug_fix", "refactoring", "documentation", "testing", "other"]


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def file_frequency(commits: list, top: int = 15) -> list:
    data = defaultdict(lambda: {"commits": 0, "insertions": 0, "deletions": 0, "authors": set(), "bug_fixes": 0})
    for c in commits:
        for f in c["files"]:
            d = data[f["path"]]
            d["commits"] += 1
            d["insertions"] += f["insertions"]
            d["deletions"] += f["deletions"]
            d["authors"].add(c["author"])
            if c.get("category") == "bug_fix":
                d["bug_fixes"] += 1
    rows = [
        {"path": p, "commits": d["commits"], "insertions": d["insertions"], "deletions": d["deletions"],
         "authors": len(d["authors"]), "bug_fixes": d["bug_fixes"]}
        for p, d in data.items()
    ]
    rows.sort(key=lambda r: (-r["commits"], -(r["insertions"] + r["deletions"]), r["path"]))
    return rows[:top]


def contributor_stats(commits: list) -> list:
    data = {}
    for c in commits:
        key = c["email"] or c["author"].lower()
        d = data.setdefault(key, {
            "author": c["author"], "commits": 0, "insertions": 0, "deletions": 0,
            "files": set(), "first": c["date"], "last": c["date"], "categories": Counter(),
        })
        d["commits"] += 1
        d["insertions"] += c["insertions"]
        d["deletions"] += c["deletions"]
        d["files"].update(f["path"] for f in c["files"])
        if parse_dt(c["date"]) < parse_dt(d["first"]):
            d["first"] = c["date"]
        if parse_dt(c["date"]) > parse_dt(d["last"]):
            d["last"] = c["date"]
        d["categories"][c.get("category", "other")] += 1
    total = len(commits) or 1
    rows = [
        {"author": d["author"], "commits": d["commits"], "share": round(100 * d["commits"] / total, 1),
         "insertions": d["insertions"], "deletions": d["deletions"], "files_touched": len(d["files"]),
         "first_commit": d["first"], "last_commit": d["last"], "categories": dict(d["categories"])}
        for d in data.values()
    ]
    rows.sort(key=lambda r: (-r["commits"], r["author"]))
    return rows


def weekly_activity(commits: list) -> list:
    weeks = defaultdict(lambda: {"commits": 0, "insertions": 0, "deletions": 0})
    for c in commits:
        d = parse_dt(c["date"]).date()
        monday = (d - timedelta(days=d.weekday())).isoformat()
        weeks[monday]["commits"] += 1
        weeks[monday]["insertions"] += c["insertions"]
        weeks[monday]["deletions"] += c["deletions"]
    return [{"week": w, **v} for w, v in sorted(weeks.items())]


def weekday_activity(commits: list) -> dict:
    counts = Counter(WEEKDAYS[parse_dt(c["date"]).weekday()] for c in commits)
    return {day: counts.get(day, 0) for day in WEEKDAYS}


def build_statistics(commits: list) -> dict:
    counts = Counter(c.get("category", "other") for c in commits)
    total = len(commits)
    dates = [parse_dt(c["date"]) for c in commits]
    return {
        "total_commits": total,
        "total_insertions": sum(c["insertions"] for c in commits),
        "total_deletions": sum(c["deletions"] for c in commits),
        "category_counts": {cat: counts.get(cat, 0) for cat in CATEGORIES},
        "category_percent": {cat: round(100 * counts.get(cat, 0) / total, 1) if total else 0 for cat in CATEGORIES},
        "top_files": file_frequency(commits),
        "contributors": contributor_stats(commits),
        "weekly_activity": weekly_activity(commits),
        "weekday_activity": weekday_activity(commits),
        "first_commit_date": min(dates).isoformat() if dates else None,
        "last_commit_date": max(dates).isoformat() if dates else None,
    }
