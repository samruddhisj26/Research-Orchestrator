import shutil
import subprocess

from orchestrator.config import AGENT_TIMEOUTS
from orchestrator.errors import AgentError
from orchestrator.state import ROOT

CODEX_BIN = shutil.which("codex") or "/opt/homebrew/bin/codex"


def run(prompt: str, timeout: int | None = None, label: str = "") -> str:
    """
    Run Codex in non-interactive mode via `codex exec`.
    The prompt is passed as a positional argument.
    cwd is set to ROOT so generated files land in the project directory.
    """
    timeout = timeout or AGENT_TIMEOUTS["codex"]
    tag = f" [{label}]" if label else ""
    try:
        proc = subprocess.run(
            [CODEX_BIN, "exec", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=ROOT,
        )
    except subprocess.TimeoutExpired as e:
        raise AgentError(
            f"Codex{tag} timed out after {timeout}s"
        ) from e

    if proc.returncode != 0:
        raise AgentError(
            f"Codex{tag} failed (exit {proc.returncode}):\n"
            f"{proc.stderr[-2000:]}"
        )
    return proc.stdout
