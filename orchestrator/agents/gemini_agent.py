import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from orchestrator.config import AGENT_TIMEOUTS
from orchestrator.errors import AgentError
from orchestrator.state import ROOT

GEMINI_BIN = shutil.which("gemini") or "/opt/homebrew/bin/gemini"


def run(prompt: str, timeout: int | None = None, session_label: str = "") -> str:
    """
    Run Gemini in non-interactive headless mode (-p flag).
    Passes prompt via -p; uses --yolo to auto-approve all tool actions.
    """
    timeout = timeout or AGENT_TIMEOUTS["gemini"]
    label = f" [{session_label}]" if session_label else ""
    try:
        proc = subprocess.run(
            [GEMINI_BIN, "--yolo", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=ROOT,
        )
    except subprocess.TimeoutExpired as e:
        raise AgentError(
            f"Gemini{label} timed out after {timeout}s"
        ) from e

    if proc.returncode != 0:
        raise AgentError(
            f"Gemini{label} failed (exit {proc.returncode}):\n"
            f"{proc.stderr[-2000:]}"
        )
    return proc.stdout


def run_parallel(tasks: list[tuple[str, str]]) -> list[str]:
    """
    Run multiple Gemini tasks in parallel.
    tasks: list of (session_label, prompt) tuples.
    Returns results in the same order as input.
    """
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {
            ex.submit(run, prompt, None, label): i
            for i, (label, prompt) in enumerate(tasks)
        }
        results: dict[int, str] = {}
        for f in as_completed(futures):
            idx = futures[f]
            results[idx] = f.result()
    return [results[i] for i in range(len(tasks))]
