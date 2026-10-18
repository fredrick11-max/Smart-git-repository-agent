"""Agent 3 - Insight Analyst: finds hotspots, recurring changes and risks.

Every insight carries evidence (numbers taken from the commits), so nothing is guesswork.
"""
from datetime import datetime, timezone

from backend.analysis import build_statistics, parse_dt

VAGUE = {"update", "updates", "wip", "fix", "fixes", "changes", "change", "commit", "misc", "stuff", "test", ".", "temp"}


def _insight(kind, severity, title, evidence):
    return {"type": kind, "severity": severity, "title": title, "evidence": evidence}


def find_insights(repo_info: dict, commits: list, stats: dict) -> list:
    n = len(commits)
    if n == 0:
        return []
    out = []
    counts = stats["category_counts"]

    for f in stats["top_files"][:3]:
        share = f["commits"] / n
        if f["commits"] >= 3 and share >= 0.3:
            out.append(_insight("hotspot", "medium" if share >= 0.5 else "low", f"Change hotspot: {f['path']}", [
                f"Changed in {f['commits']} of {n} commits ({share:.0%}), "
                f"+{f['insertions']}/-{f['deletions']} lines, {f['authors']} author(s)"]))

    for f in stats["top_files"]:
        if f["bug_fixes"] >= 2:
            out.append(_insight("recurring_change", "medium", f"Repeated bug fixes in {f['path']}", [
                f"{f['bug_fixes']} bug-fix commits touched this file; it may be fragile or poorly covered by tests"]))

    top = stats["contributors"][0]
    if n >= 5 and top["share"] >= 80:
        out.append(_insight("risk", "medium", "Knowledge concentrated in one contributor", [
            f"{top['author']} made {top['commits']} of {n} commits ({top['share']}%)"]))

    big = [c for c in commits if not c.get("is_merge") and (c["insertions"] + c["deletions"] >= 500 or c["files_changed"] >= 15)]
    if big:
        out.append(_insight("risk", "low", "Very large commits are hard to review", [
            f"`{c['short_sha']}` '{c['message']}': +{c['insertions']}/-{c['deletions']} in {c['files_changed']} files"
            for c in big[:3]]))

    code_changes = counts["feature"] + counts["bug_fix"] + counts["refactoring"]
    if code_changes >= 3 and not repo_info.get("has_tests"):
        out.append(_insight("risk", "medium", "No test files found", [
            f"{code_changes} code-changing commits but no test files exist in the latest commit"]))
    elif code_changes >= 5 and counts["testing"] / n < 0.1:
        out.append(_insight("risk", "medium", "Little testing activity", [
            f"Only {counts['testing']} of {n} commits are test-related versus {code_changes} code-changing commits"]))

    if n >= 5 and counts["bug_fix"] / n >= 0.4:
        out.append(_insight("risk", "medium", "High proportion of bug-fix commits", [
            f"{counts['bug_fix']} of {n} commits ({counts['bug_fix'] / n:.0%}) are bug fixes"]))

    vague = [c for c in commits if c["message"].lower().strip(" .!") in VAGUE or len(c["message"].split()) <= 1]
    if len(vague) >= 3 and len(vague) / n >= 0.3:
        out.append(_insight("risk", "low", "Many vague commit messages", [
            f"{len(vague)} of {n} commits have messages like '{vague[0]['message']}', which hides intent"]))

    last = parse_dt(stats["last_commit_date"])
    age_days = (datetime.now(timezone.utc) - last).days
    if age_days > 90:
        out.append(_insight("risk", "low", "No recent activity", [f"The last commit was {age_days} days ago"]))

    weekdays = stats["weekday_activity"]
    busiest = max(weekdays, key=weekdays.get)
    out.append(_insight("pattern", "info", f"Most commits happen on {busiest}", [
        f"{weekdays[busiest]} of {n} commits were made on {busiest}"]))
    recent = sum(1 for c in commits if (datetime.now(timezone.utc) - parse_dt(c["date"])).days <= 30)
    out.append(_insight("pattern", "info", "Recent activity", [f"{recent} of the analyzed commits are from the last 30 days"]))
    return out


class InsightAnalyst:
    name = "Insight Analyst"

    def run(self, repo_info: dict, commits: list) -> dict:
        stats = build_statistics(commits)
        return {"statistics": stats, "insights": find_insights(repo_info, commits, stats)}
