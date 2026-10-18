"""Smart Git Repository Agent - Streamlit dashboard.  Run with:  streamlit run app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.orchestrator import Orchestrator
from backend import config
from backend.errors import RepositoryError
from backend.qa import SUGGESTIONS, answer_question
from backend.reports import save_reports, to_json, to_markdown
from database.db import AnalysisDatabase
from llm.fallback import CATEGORY_TITLES
from llm.gemini_client import GeminiClient

st.set_page_config(page_title="Smart Git Repository Agent", page_icon="🧠", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem;}
div[data-testid="stMetric"] {background: rgba(128,128,128,0.10); border-radius: 12px; padding: 12px 16px;}
.badge {display:inline-block; padding:3px 12px; border-radius:999px; font-size:0.85rem; font-weight:600;}
.badge-ai {background:#1f7a4d; color:white;} .badge-basic {background:#8a6d1d; color:white;}
</style>""", unsafe_allow_html=True)

COLORS = {"Features": "#2e86de", "Bug Fixes": "#e74c3c", "Refactoring": "#8e44ad",
          "Documentation": "#27ae60", "Tests": "#f39c12", "Other": "#95a5a6"}
SAMPLE_PATH = Path(__file__).parent / "examples" / "sample_repo"

db = AnalysisDatabase(config.DB_PATH)
gemini = GeminiClient()


def set_source(value: str):
    st.session_state["source"] = value


def create_sample():
    try:
        from examples.create_sample_repo import create_sample_repo
        st.session_state["source"] = str(create_sample_repo(SAMPLE_PATH))
        st.session_state["notice"] = "Sample repository created. Click 'Analyze Repository'."
    except Exception as exc:
        st.session_state["notice"] = f"Could not create the sample repository: {exc}"


with st.sidebar:
    st.title("🧠 Smart Git Agent")
    st.text_input("Repository path or public GitHub URL", key="source",
                  placeholder=r"C:\projects\my-repo   or   https://github.com/owner/repo")
    max_commits = st.slider("Max commits to analyze", 10, config.HARD_MAX_COMMITS, config.DEFAULT_MAX_COMMITS, step=10)
    use_ai = st.checkbox("Use Gemini AI for the summary", value=gemini.available, disabled=not gemini.available)
    if gemini.available:
        st.caption(f"Gemini key found (model: {gemini.model})")
    else:
        st.caption("No Gemini key in .env: a basic rule-based summary will be used.")
    analyze_clicked = st.button("Analyze Repository", type="primary")
    st.button("Create sample repository", on_click=create_sample)
    if st.session_state.get("notice"):
        st.info(st.session_state.pop("notice"))

if analyze_clicked:
    bar, status = st.progress(0.0), st.empty()

    def on_progress(fraction, message):
        bar.progress(min(fraction, 1.0))
        status.text(message)

    try:
        st.session_state["analysis"] = Orchestrator(gemini, db).run(
            st.session_state.get("source", ""), max_commits, use_ai, on_progress)
        saved = save_reports(st.session_state["analysis"], config.REPORTS_DIR)
        st.session_state["report_paths"] = {k: str(v) for k, v in saved.items()}
        st.session_state["qa_history"] = []
    except RepositoryError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Unexpected error while analyzing the repository: {exc}")
    finally:
        bar.empty()
        status.empty()

analysis = st.session_state.get("analysis")
st.title("Smart Git Repository Agent")
st.caption("Understand a repository's development history: what changed, who changed it, and where the risks are.")

if not analysis:
    st.info("Enter a local repository path or a public GitHub URL in the sidebar and click **Analyze Repository**. "
            "No repository handy? Click **Create sample repository** first.")
    st.stop()

repo, stats, summary, meta = analysis["repository"], analysis["statistics"], analysis["summary"], analysis["meta"]
df = pd.DataFrame([{
    "commit": c["short_sha"], "date": c["date"][:16].replace("T", " "), "author": c["author"],
    "category": CATEGORY_TITLES[c["category"]], "message": c["message"], "files": c["files_changed"],
    "added": c["insertions"], "removed": c["deletions"], "confidence": c["confidence"], "reason": c["reason"],
} for c in analysis["commits"]])

st.subheader(f"{repo['name']}")
m = st.columns(5)
m[0].metric("Commits analyzed", stats["total_commits"], help=f"Repository total: {repo['total_commits']}")
m[1].metric("Contributors", len(stats["contributors"]))
m[2].metric("Branches", repo["branch_count"])
m[3].metric("Files", repo["file_count"])
m[4].metric("Last commit", (stats["last_commit_date"] or "")[:10])

tabs = st.tabs(["Overview", "Commits", "Contributors & Files", "AI Summary", "Ask", "Reports", "History"])

with tabs[0]:
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Source:** `{meta['source']}`  \n**Active branch:** `{repo['active_branch']}`  \n**Tags:** {repo['tag_count']}")
        cat = pd.DataFrame({"category": [CATEGORY_TITLES[c] for c in stats["category_counts"]],
                            "commits": list(stats["category_counts"].values())})
        st.plotly_chart(px.pie(cat[cat.commits > 0], names="category", values="commits", hole=0.45,
                               color="category", color_discrete_map=COLORS, title="Commit categories"))
        if repo["languages"]:
            st.plotly_chart(px.pie(pd.DataFrame(repo["languages"]), names="language", values="bytes", title="Languages"))
    with right:
        weekly = pd.DataFrame(stats["weekly_activity"])
        st.plotly_chart(px.bar(weekly, x="week", y="commits", title="Commits per week"))
        st.markdown("**Branches**")
        st.dataframe(pd.DataFrame(repo["branches"])[["name", "is_active", "last_commit", "last_author"]], hide_index=True)
        st.markdown("**Important files:** " + (", ".join(f"`{f}`" for f in repo["important_files"]) or "none found"))
    st.markdown("**Recent commits**")
    st.dataframe(df[["commit", "date", "author", "category", "message"]].head(10), hide_index=True)

with tabs[1]:
    chosen = st.multiselect("Filter by category", sorted(df.category.unique()), default=sorted(df.category.unique()))
    st.dataframe(df[df.category.isin(chosen)], hide_index=True)
    st.caption("'reason' shows the evidence behind each classification (message, file paths or diff).")

with tabs[2]:
    people = pd.DataFrame(stats["contributors"]).drop(columns=["categories"])
    files = pd.DataFrame(stats["top_files"])
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.bar(people, x="author", y="commits", title="Commits per contributor"))
        st.dataframe(people, hide_index=True)
    with c2:
        if not files.empty:
            st.plotly_chart(px.bar(files.head(10).iloc[::-1], x="commits", y="path", orientation="h",
                                   title="Most frequently modified files"))
            st.dataframe(files, hide_index=True)
    st.markdown("**Potential concerns and patterns (each backed by evidence)**")
    for i in analysis["insights"]:
        icon = {"high": "🔴", "medium": "🟠", "low": "🟡", "info": "🔵"}[i["severity"]]
        st.markdown(f"{icon} **{i['title']}** - " + "; ".join(i["evidence"]))

with tabs[3]:
    if summary["generated_by"] == "gemini":
        st.markdown(f"<span class='badge badge-ai'>Generated by Gemini ({summary['model']})</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='badge badge-basic'>Basic summary (no AI)</span>", unsafe_allow_html=True)
        if summary["ai_error"]:
            st.warning(summary["ai_error"])
    st.markdown("### Summary")
    st.write(summary["summary"])
    st.markdown("### Major changes")
    for item in summary["major_changes"]:
        st.markdown(f"- {item}")
    st.markdown("### Development insights")
    for item in summary["development_insights"]:
        st.markdown(f"- {item}")
    st.markdown("### Changelog")
    st.markdown(summary["changelog"])
    with st.expander("Agent workflow log"):
        st.dataframe(pd.DataFrame(analysis["workflow"]), hide_index=True)

with tabs[4]:
    st.write("Ask about the analyzed history. Common questions are answered directly from Git data; others use Gemini.")
    history = st.session_state.setdefault("qa_history", [])
    with st.form("ask_form", clear_on_submit=True):
        question = st.text_input("Your question", placeholder=SUGGESTIONS[0])
        asked = st.form_submit_button("Ask")
    st.caption("Try: " + " | ".join(SUGGESTIONS))
    if asked and question.strip():
        with st.spinner("Thinking..."):
            answer, source = answer_question(question.strip(), analysis, gemini if use_ai else None)
        history.insert(0, (question.strip(), answer, source))
    for q, a, src in history:
        st.markdown(f"**Q: {q}**")
        st.markdown(a)
        st.caption(f"Answer source: {src}")
        st.divider()

with tabs[5]:
    md_text, json_text = to_markdown(analysis), to_json(analysis)
    b1, b2 = st.columns(2)
    b1.download_button("Download Markdown report", md_text, file_name=f"{repo['name']}_report.md", mime="text/markdown")
    b2.download_button("Download JSON report", json_text, file_name=f"{repo['name']}_report.json", mime="application/json")
    paths = st.session_state.get("report_paths")
    if paths:
        st.caption(f"Copies were also saved in: {Path(paths['markdown']).parent}")
    st.markdown("---")
    st.markdown(md_text)

with tabs[6]:
    rows = db.list_analyses()
    if not rows:
        st.write("No saved analyses yet.")
    else:
        hist = pd.DataFrame(rows)
        hist["ai_used"] = hist["ai_used"].astype(bool)
        st.dataframe(hist.drop(columns=["summary_preview"]), hide_index=True)
        pick = st.selectbox("Open a saved analysis", [r["id"] for r in rows],
                            format_func=lambda i: next(f"#{r['id']} - {r['repo_name']} ({r['created_at'][:16]})" for r in rows if r["id"] == i))
        h1, h2 = st.columns(2)
        if h1.button("Load analysis"):
            st.session_state["analysis"] = db.get_analysis(pick)
            st.session_state["qa_history"] = []
            st.rerun()
        if h2.button("Delete analysis"):
            db.delete_analysis(pick)
            st.rerun()
