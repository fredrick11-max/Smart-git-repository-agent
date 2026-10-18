"""Natural-language questions about the analysed history.

Common questions are answered directly from the Git data (exact and free). Anything else goes to Gemini,
which only receives a compact evidence summary.
"""
import re
from datetime import datetime, timedelta, timezone

from backend.analysis import parse_dt
from llm.fallback import CATEGORY_TITLES

SUGGESTIONS = [
    "What changed this week?",
    "Which files changed most frequently?",
    "Who are the top contributors?",
    "Which bugs were fixed recently?",
    "What features were added?",
]


def _commit_line(c) -> str:
    return f"- `{c['short_sha']}` {c['date'][:10]} - {c['message']} ({c['author']})"


def _recent_commits(commits: list, days: int = 7):
    if not commits:
        return [], "", False
    newest = max(parse_dt(c["date"]) for c in commits)
    now = datetime.now(timezone.utc)
    window = [c for c in commits if parse_dt(c["date"]) >= now - timedelta(days=days)]
    if window:
        return window, "in the last 7 days", False
    window = [c for c in commits if parse_dt(c["date"]) >= newest - timedelta(days=days)]
    return window, f"in the 7 days up to the latest commit ({newest.date()})", True


def _by_category(commits, cat, label):
    items = [c for c in commits if c["category"] == cat][:15]
    if not items:
        return f"No {label} commits were found in the analyzed range."
    return f"**{CATEGORY_TITLES[cat]}** ({len(items)} shown):\n" + "\n".join(_commit_line(c) for c in items)


def answer_deterministic(question: str, analysis: dict):
    """Return an answer string, or None when the question needs the AI."""
    q = question.lower()
    commits, stats = analysis["commits"], analysis["statistics"]
    if re.search(r"\b(week|recent|recently|latest|lately|today)\b", q) and not re.search(r"\b(bug|fix|feature)", q):
        window, label, _ = _recent_commits(commits)
        if not window:
            return "There are no commits in the analyzed range."
        return f"**{len(window)} commit(s) {label}:**\n" + "\n".join(_commit_line(c) for c in window[:20])
    if re.search(r"\bfiles?\b", q) and re.search(r"(frequent|often|most|hotspot|changed)", q):
        rows = stats["top_files"][:10]
        return "**Most frequently changed files:**\n" + "\n".join(
            f"- `{r['path']}` - {r['commits']} commits (+{r['insertions']}/-{r['deletions']})" for r in rows)
    if re.search(r"\b(contributor|contributors|author|authors|who|developer|developers)\b", q):
        return "**Contributors:**\n" + "\n".join(
            f"- {c['author']} - {c['commits']} commits ({c['share']}%), +{c['insertions']}/-{c['deletions']} lines"
            for c in stats["contributors"])
    if re.search(r"\b(bug|bugs|fix|fixes|fixed)\b", q):
        return _by_category(commits, "bug_fix", "bug-fix")
    if re.search(r"\b(feature|features|added|new)\b", q):
        return _by_category(commits, "feature", "feature")
    if re.search(r"\brefactor", q):
        return _by_category(commits, "refactoring", "refactoring")
    if re.search(r"\b(doc|docs|documentation)\b", q):
        return _by_category(commits, "documentation", "documentation")
    if re.search(r"\bbranch", q):
        return "**Branches:**\n" + "\n".join(
            f"- {b['name']}{' (active)' if b['is_active'] else ''} - last commit {b['last_commit'][:10]} by {b['last_author']}"
            for b in analysis["repository"]["branches"])
    if re.search(r"\b(risk|risks|concern|concerns|problem|problems)\b", q):
        items = [i for i in analysis["insights"] if i["type"] != "pattern"]
        if not items:
            return "No risks were detected from the analyzed commits."
        return "**Potential concerns:**\n" + "\n".join(f"- **{i['title']}** - {i['evidence'][0]}" for i in items)
    return None


def build_context(analysis: dict, max_commits: int = 60) -> str:
    stats, repo = analysis["statistics"], analysis["repository"]
    lines = [
        f"Repository {repo['name']}, {stats['total_commits']} analyzed commits, categories {stats['category_counts']}",
        "Top files: " + "; ".join(f"{f['path']} ({f['commits']})" for f in stats["top_files"][:10]),
        "Contributors: " + "; ".join(f"{c['author']} ({c['commits']})" for c in stats["contributors"][:10]),
        "Commits (sha | date | author | category | subject):",
    ]
    lines += [f"{c['short_sha']} | {c['date'][:10]} | {c['author']} | {c['category']} | {c['message'][:120]}"
              for c in analysis["commits"][:max_commits]]
    return "\n".join(lines)


def answer_question(question: str, analysis: dict, gemini=None):
    """Return (answer_markdown, source) where source is 'git data', 'gemini' or 'unavailable'."""
    direct = answer_deterministic(question, analysis)
    if direct is not None:
        return direct, "git data"
    if gemini is None or not gemini.available:
        return ("I can answer questions about recent changes, frequently changed files, contributors, bug fixes, features, "
                "branches and risks directly. Other questions need a Gemini API key in your .env file."), "unavailable"
    prompt = (
        "Answer the question about this Git repository using ONLY the evidence. If the evidence does not contain the "
        "answer, say so. Be concise and mention short commit hashes.\n\n"
        f"EVIDENCE:\n{build_context(analysis)}\n\nQUESTION: {question}"
    )
    reply = gemini.generate(prompt)
    if not reply.ok:
        return f"Gemini could not answer: {reply.error}", "unavailable"
    return reply.text, "gemini"
