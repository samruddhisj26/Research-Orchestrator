import subprocess
from pathlib import Path


def git_commit(files: list[str], message: str, cwd: Path | None = None) -> None:
    """Stage specific files and create a commit."""
    _run(["git", "add", "--"] + files, cwd=cwd)
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=cwd,
    )
    if not result.stdout.strip():
        return  # nothing to commit
    _run(["git", "commit", "-m", message], cwd=cwd)


def git_add(files: list[str], cwd: Path | None = None) -> None:
    _run(["git", "add", "--"] + files, cwd=cwd)


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, check=True, cwd=cwd)
