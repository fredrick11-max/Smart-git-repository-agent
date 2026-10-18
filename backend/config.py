"""Central settings. Secrets come from the .env file, never from the source code."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "data" / "analyses.db"
REPORTS_DIR = ROOT / "reports"
CACHE_DIR = ROOT / ".cache" / "repos"

DEFAULT_MAX_COMMITS = 100
HARD_MAX_COMMITS = 500
MAX_DIFF_COMMITS = 40
MAX_DIFF_CHARS = 1500
MAX_PROMPT_COMMITS = 60
MAX_PROMPT_DIFFS = 8
CLONE_DEPTH = 300

PLACEHOLDER_KEY = "your_gemini_api_key_here"


def get_gemini_key() -> str:
    """Return the Gemini key from the environment, or '' when missing/placeholder."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return "" if key in ("", PLACEHOLDER_KEY) else key


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"
