"""Rule-based summary and changelog used when Gemini is unavailable (no key, quota, network...)."""
from collections import defaultdict

CATEGORY_TITLES = {
    "feature": "Features", "bug_fix": "Bug Fixes", "refactoring": "Refactoring",
    "documentation": "Documentation", "testing": "Tests", "other": "Other",
}
CATEGORY_LABELS = {
    "feature": "feature work", "bug_fix": "bug fixing", "refactoring": "refactoring",
    "documentation": "documentation", "testing": "testing", "other": "other changes",
}


def build_changelog(commits: list, per_group: int = 15) -> str:
    groups = defaultdict(list)
    for c in commits:
        groups[c.get("category", "other")].append(c)
    lines = []
    for cat, title in CATEGORY_TITLES.items():
        if not groups.get(cat):
            continue
        lines.append(f"### {title}")
        for c in groups[cat][:per_group]:
            lines.append(f"- {c['message']} (`{c['short_sha']}`, {c['author']})")
        if len(groups[cat]) > per_group:
            lines.append(f"- ...and {len(groups[cat]) - per_group} more")
        lines.append("")
    return "\n".join(lines).strip() or "No commits to list."


def basic_summary(repo_info: dict, commits: list, stats: dict, insights: list) -> dict:
    total = stats["total_commits"]
    contributors = stats["contributors"]
    counts = stats["category_counts"]
    top_cat = max(counts, key=counts.get) if total else "other"
    langs = ", ".join(l["language"] for l in repo_info.get("languages", [])[:3]) or "no recognised programming languages"
    first = (stats["first_commit_date"] or "")[:10]
    last = (stats["last_commit_date"] or "")[:10]
    top_file = stats["top_files"][0] if stats["top_files"] else None

    summary = (
        f"{repo_info['name']} ({langs}) was analyzed over its {total} most recent commits, "
        f"from {first} to {last}, by {len(contributors)} contributor(s). "
        f"Most activity was {CATEGORY_LABELS[top_cat]} ({stats['category_percent'][top_cat]}% of commits). "
        f"In total {stats['total_insertions']} lines were added and {stats['total_deletions']} removed."
    )
    if top_file:
        summary += f" The most frequently changed file is {top_file['path']} ({top_file['commits']} commits)."

    ranked = sorted(
        (c for c in commits if c.get("category") in ("feature", "bug_fix", "refactoring")),
        key=lambda c: c["insertions"] + c["deletions"], reverse=True,
    )[:5]
    major = [
        f"{c['message']} [{CATEGORY_TITLES[c['category']]}, `{c['short_sha']}`, "
        f"+{c['insertions']}/-{c['deletions']} lines in {c['files_changed']} file(s)]"
        for c in ranked
    ] or ["No feature, bug-fix or refactoring commits were found in the analyzed range."]
    development = [f"{i['title']}: {i['evidence'][0]}" for i in insights[:6] if i["evidence"]] \
        or ["No notable patterns or risks were detected."]
    return {
        "summary": summary, "major_changes": major, "development_insights": development,
        "changelog": build_changelog(commits),
    }
