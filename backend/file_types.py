"""Small helpers that recognise languages, test files and documentation files."""
import os

LANGUAGE_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".c": "C", ".h": "C", ".cpp": "C++",
    ".hpp": "C++", ".cs": "C#", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin", ".dart": "Dart", ".r": "R",
    ".html": "HTML", ".css": "CSS", ".scss": "CSS", ".sql": "SQL", ".sh": "Shell",
    ".ps1": "PowerShell", ".ipynb": "Jupyter Notebook",
}
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", ".venv", "venv", "__pycache__", "site-packages"}
TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}
DOC_DIRS = {"docs", "doc", "documentation"}
DOC_EXTS = {".md", ".rst", ".adoc"}
DOC_NAMES = ("readme", "changelog", "contributing", "authors")


def _parts(path: str):
    return path.replace("\\", "/").lower().split("/")


def is_test_path(path: str) -> bool:
    parts = _parts(path)
    name = parts[-1]
    return (
        any(p in TEST_DIRS for p in parts[:-1])
        or name.startswith("test_")
        or "_test." in name
        or ".test." in name
        or ".spec." in name
    )


def is_doc_path(path: str) -> bool:
    parts = _parts(path)
    name = parts[-1]
    return (
        any(p in DOC_DIRS for p in parts[:-1])
        or os.path.splitext(name)[1] in DOC_EXTS
        or name.startswith(DOC_NAMES)
    )


def language_of(path: str):
    return LANGUAGE_BY_EXT.get(os.path.splitext(path.lower())[1])
