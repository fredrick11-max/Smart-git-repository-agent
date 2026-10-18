"""Agent 4 - Summary Generator: asks Gemini for a readable summary/changelog, with a rule-based fallback."""
import json
import re

from backend.config import MAX_DIFF_CHARS, MAX_PROMPT_COMMITS, MAX_PROMPT_DIFFS
from llm.fallback import basic_summary, build_changelog


def build_evidence(repo_info: dict, commits: list, stats: dict, insights: list) -> str:
    """Compact, evidence-only text that is sent to Gemini (limited in size to save quota)."""
    lines = [
        f"Repository: {repo_info['name']} | branch: {repo_info['active_branch']} | total commits: {repo_info['total_commits']} "
        f"| analyzed: {stats['total_commits']} | branches: {repo_info['branch_count']}",
        "Languages: " + ", ".join(f"{l['language']} {l['percent']}%" for l in repo_info["languages"]),
        f"Date range: {(stats['first_commit_date'] or '')[:10]} to {(stats['last_commit_date'] or '')[:10]}",
        "Category counts: " + json.dumps(stats["category_counts"]),
        "Top files: " + "; ".join(f"{f['path']} ({f['commits']} commits)" for f in stats["top_files"][:8]),
        "Contributors: " + "; ".join(f"{c['author']} ({c['commits']} commits)" for c in stats["contributors"][:8]),
        "Detected risks/patterns: " + " | ".join(f"{i['title']} - {i['evidence'][0]}" for i in insights if i["evidence"]),
        "", f"Newest {min(len(commits), MAX_PROMPT_COMMITS)} commits (sha | date | author | category | subject | files +added/-removed):",
    ]
    for c in commits[:MAX_PROMPT_COMMITS]:
        lines.append(f"{c['short_sha']} | {c['date'][:10]} | {c['author']} | {c['category']} | {c['message'][:120]} | "
                     f"{c['files_changed']} files +{c['insertions']}/-{c['deletions']}")
    with_diff = sorted((c for c in commits if c.get("diff_excerpt")),
                       key=lambda c: c["insertions"] + c["deletions"], reverse=True)[:MAX_PROMPT_DIFFS]
    if with_diff:
        lines += ["", "Diff excerpts of the largest recent commits:"]
        for c in with_diff:
            lines.append(f"--- {c['short_sha']} {c['message'][:80]}\n{c['diff_excerpt'][:min(600, MAX_DIFF_CHARS)]}")
    return "\n".join(lines)


PROMPT = """You are a senior software engineer writing a report about a Git repository's history.
Use ONLY the evidence below. Do not invent features, files, people or numbers. Refer to commits by their short hash.

Return a JSON object with exactly these keys:
  "summary": string, 3-5 sentences describing what the project is and how it evolved,
  "major_changes": array of 3-6 strings, the most important changes (mention short hashes),
  "development_insights": array of 3-6 strings about patterns, hotspots and risks supported by the evidence,
  "changelog": markdown string grouped under ### Features, ### Bug Fixes, ### Refactoring, ### Documentation, ### Tests, ### Other (omit empty groups).

EVIDENCE:
{evidence}
"""


def parse_json_reply(text: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(cleaned)
    except ValueError:
        found = re.search(r"\{.*\}", cleaned, re.S)
        return json.loads(found.group(0)) if found else None


def _as_list(value):
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)] if value else []


class SummaryGenerator:
    name = "Summary Generator"

    def __init__(self, gemini=None):
        self.gemini = gemini

    def run(self, repo_info: dict, commits: list, stats: dict, insights: list, use_ai: bool = True) -> dict:
        fallback = basic_summary(repo_info, commits, stats, insights)
        result = {**fallback, "generated_by": "fallback", "ai_error": None, "model": None}
        if not use_ai:
            result["ai_error"] = "AI summary was turned off."
            return result
        if self.gemini is None or not self.gemini.available:
            result["ai_error"] = "No Gemini API key configured, so a basic rule-based summary was generated."
            return result

        reply = self.gemini.generate(PROMPT.format(evidence=build_evidence(repo_info, commits, stats, insights)), json_mode=True)
        if not reply.ok:
            result["ai_error"] = reply.error
            return result
        try:
            data = parse_json_reply(reply.text)
            if not isinstance(data, dict) or not str(data.get("summary", "")).strip():
                raise ValueError("missing summary")
        except ValueError:
            result["ai_error"] = "Gemini returned text that could not be parsed; a basic summary is shown instead."
            return result
        return {
            "summary": str(data["summary"]).strip(),
            "major_changes": _as_list(data.get("major_changes")) or fallback["major_changes"],
            "development_insights": _as_list(data.get("development_insights")) or fallback["development_insights"],
            "changelog": str(data.get("changelog") or "").strip() or build_changelog(commits),
            "generated_by": "gemini", "ai_error": None, "model": getattr(self.gemini, "model", None),
        }
