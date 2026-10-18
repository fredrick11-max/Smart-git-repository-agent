"""Opening a repository: a local folder or a public GitHub URL (cloned into .cache)."""
import os
import re
import shutil
import stat
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from backend.config import CACHE_DIR, CLONE_DEPTH
from backend.errors import RepositoryError

GITHUB_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def is_url(source: str) -> bool:
    return source.lower().startswith(("http://", "https://", "git@", "ssh://", "git://", "file://"))


def _force_remove(func, path, _exc):
    """rmtree helper: Windows keeps .git object files read-only."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _clone_github(url: str, cache_dir: Path) -> Repo:
    match = GITHUB_RE.match(url)
    if not match:
        raise RepositoryError(
            "Only public GitHub URLs of the form https://github.com/<owner>/<repo> are supported."
        )
    owner, name = match.groups()
    dest = Path(cache_dir) / f"{owner}__{name}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        shutil.rmtree(dest, onerror=_force_remove)
    try:
        return Repo.clone_from(
            url, str(dest), depth=CLONE_DEPTH, no_single_branch=True,
            env={"GIT_TERMINAL_PROMPT": "0"},
        )
    except GitCommandError as exc:
        text = str(exc).lower()
        if "not found" in text or "could not read username" in text or "authentication" in text:
            raise RepositoryError(
                "Could not clone the repository. It may not exist or it may be private "
                "(only public repositories are supported)."
            ) from exc
        raise RepositoryError(f"Cloning failed. Check your internet connection and the URL. ({exc.stderr or exc})") from exc


def open_repository(source: str, cache_dir: Path = CACHE_DIR):
    """Return (Repo, display_name). Raises RepositoryError with a friendly message."""
    source = (source or "").strip().strip('"').strip("'")
    if not source:
        raise RepositoryError("Please enter a local repository path or a public GitHub URL.")

    if is_url(source):
        repo = _clone_github(source, Path(cache_dir))
        name = GITHUB_RE.match(source).group(2)
    else:
        path = Path(source).expanduser()
        if not path.exists():
            raise RepositoryError(f"The path does not exist: {path}")
        if not path.is_dir():
            raise RepositoryError(f"The path is not a folder: {path}")
        try:
            repo = Repo(str(path))
        except InvalidGitRepositoryError as exc:
            raise RepositoryError(f"'{path}' is not a Git repository (no .git folder found).") from exc
        except NoSuchPathError as exc:
            raise RepositoryError(f"The path does not exist: {path}") from exc
        except PermissionError as exc:
            raise RepositoryError(f"Permission denied while opening '{path}'.") from exc
        except GitCommandError as exc:
            raise RepositoryError(
                "Git refused to open this repository. If the message mentions 'dubious ownership', run: "
                "git config --global --add safe.directory <path>"
            ) from exc
        name = path.resolve().name

    if repo.bare or not repo.head.is_valid():
        raise RepositoryError("This repository has no commits yet, so there is nothing to analyze.")
    return repo, name
