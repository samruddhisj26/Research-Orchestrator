import os
import glob as _glob
from pathlib import Path

ROOT = Path(os.environ.get("RESEARCH_ROOT", ".")).resolve()


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def has_placeholder(rel: str) -> bool:
    """Return True if the file is missing or contains unfilled template markers."""
    p = ROOT / rel
    if not p.exists():
        return True
    content = p.read_text()
    return "<!--" in content or "[X]" in content or "| | |" in content


def write_gate(name: str) -> Path:
    """Write an empty gate marker file and return its absolute path."""
    p = ROOT / f".gate-{name}"
    p.touch()
    return p


def detect_phase() -> str:
    """Return the string phase ID for the current project state."""

    def _figures_empty() -> bool:
        fig_dir = ROOT / "results/figures"
        if not fig_dir.exists():
            return True
        return not any(fig_dir.iterdir())

    checks = [
        ("0",  lambda: has_placeholder("research-spec.md")),
        ("1",  lambda: not exists("literature/search-queries.md") or has_placeholder("literature/search-queries.md")),
        ("2A", lambda: any(not exists(f"literature/screening-batch-{i}.csv") for i in [1, 2, 3])),
        ("2B", lambda: not exists("literature/extraction-data.json")),
        ("2C", lambda: not exists("literature/synthesis.md")),
        ("2G", lambda: not exists(".gate-lit-passed")),
        ("3A", lambda: has_placeholder("code/code-spec.md")),
        ("3B", lambda: not exists("code/model.py")),
        ("3C", lambda: exists("code/model.py") and not exists("code/run_experiments.sh")),
        ("3D", lambda: exists("code/model.py") and not exists(".gate-code-reviewed")),
        ("4",  lambda: not _glob.glob(str(ROOT / "results" / "*.csv")) and not _glob.glob(str(ROOT / "results" / "*.json"))),
        ("5A", lambda: has_placeholder("results/analysis.md")),
        ("5B", lambda: _figures_empty()),
        ("5G", lambda: not exists(".gate-results-passed")),
        ("6A", lambda: has_placeholder("writing/methods.md")),
        ("6B", lambda: not exists("writing/results.md") or has_placeholder("writing/results.md")),
        ("6C", lambda: has_placeholder("writing/related-work.md")),
        ("6D", lambda: has_placeholder("writing/intro.md")),
        ("6E", lambda: has_placeholder("writing/draft.md")),
        ("7",  lambda: not exists(".gate-draft-passed")),
        ("8",  lambda: True),
    ]
    for phase_id, check in checks:
        if check():
            return phase_id
    return "8"
