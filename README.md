# Smart Git Repository Agent

An AI-assisted Streamlit app that analyzes a Git repository and explains its development history: what changed, who changed it, which files are hotspots, and where the risks are. All statistics come from real Git data (GitPython); Google Gemini only writes the readable summary and answers free-form questions.

## Features
- Analyze a **local repository path** or a **public GitHub URL**
- Overview: metadata, languages, branches, recent commits, charts
- Commit classification: feature, bug fix, refactoring, documentation, testing, other (with the evidence for each decision)
- Contributor statistics, most frequently modified files, evidence-based risks
- Gemini summary, major changes, insights and changelog (rule-based fallback if Gemini is unavailable)
- Natural-language questions ("What changed this week?")
- SQLite analysis history, downloadable Markdown and JSON reports

## Architecture and agent workflow
```
Path/URL -> Orchestrator
              1. Repository Inspector  : metadata, branches, languages, important files
              2. Git extraction        : commits, file stats, short diff excerpts (limited size)
              3. Commit Classifier     : message + file paths + diff -> category and reason
              4. Insight Analyst       : statistics, hotspots, recurring changes, risks (with evidence)
              5. Summary Generator     : ONE Gemini call -> summary + changelog (fallback if it fails)
              -> SQLite history + Markdown/JSON reports -> Streamlit dashboard
```
Only the Summary Generator and the "Ask" tab call Gemini. Agents 1-3 and the Orchestrator are plain deterministic Python, so the app works without an API key. Each agent passes its output to the next one, and the Orchestrator records a workflow log (shown in the AI Summary tab).

```
app.py            Streamlit UI
backend/          git_utils (open/clone), extractor, analysis (stats), qa, reports, config
agents/           repository_inspector, commit_classifier, insight_analyst, summary_generator, orchestrator
database/         SQLite operations
llm/              Gemini client + rule-based fallback
tests/            essential tests
examples/         create_sample_repo.py (local repo with real commits)
reports/          generated reports (ignored by Git)
```

## Windows setup (PowerShell)
Requires Python 3.10+ and Git for Windows.
```powershell
cd smart-git-repository-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env                      # replace the placeholder with your Gemini key
```
Get a free key at https://aistudio.google.com/apikey and set `GEMINI_API_KEY=...` in `.env`. Optionally change `GEMINI_MODEL` if Google renames or retires the default model. Never commit `.env`.

## Run
```powershell
streamlit run app.py
```
Open http://localhost:8501.

## Analyze a repository
- **Local:** paste a folder path such as `C:\projects\my-repo` and click *Analyze Repository*.
- **GitHub:** paste `https://github.com/owner/repo` (public only). It is cloned shallowly into `.cache/`.
- **Quick demo:** click *Create sample repository* in the sidebar (or run `python examples\create_sample_repo.py`), then analyze it.

## Run the tests
```powershell
python -m pytest -v
# or without pytest:
python -m unittest discover -s tests -t . -v
```
The Git tests need GitPython and are skipped automatically if it is not installed.

## Limitations
- Classification is rule-based (message keywords, file paths, diff hints); vague messages such as "update" end up as *other*.
- Only recent commits are analyzed (default 100, max 500); diffs are truncated; GitHub clones are shallow (300 commits).
- Gemini free-tier quotas apply; on failure the app shows a basic summary and says why.
- Public GitHub repositories only; no authentication.

## Future improvements
Use Gemini to classify ambiguous commits, analyze multiple branches, support private repositories, track trends between saved analyses, scheduled monitoring.

## Publish to GitHub (PowerShell)
Create an empty repository named `smart-git-repository-agent` on github.com first (no README), then:
```powershell
git init
git add .
git status                         # check that .env and data/ are NOT listed
git commit -m "Initial commit: Smart Git Repository Agent"
git branch -M main
git remote add origin https://github.com/<your-username>/smart-git-repository-agent.git
git push -u origin main
```
