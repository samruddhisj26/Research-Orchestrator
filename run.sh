#!/usr/bin/env bash
# Research Orchestrator — standalone entry point.
#
# Usage:
#   ./run.sh                    # run from inside a research project directory
#   ./run.sh /path/to/project   # run targeting a specific project directory
#   ./run.sh --dry-run          # show which agent/phase would run, without executing
#
# Detects current phase and drives all tasks autonomously:
#   Claude API  → synthesis, gates, writing (high-quality judgment tasks)
#   Gemini CLI  → bulk screening, data extraction, data prep (cheap + fast)
#   Codex CLI   → code generation, figures (purpose-built)
#
# Re-run at any time to resume from where you left off — idempotent.

set -euo pipefail

ORCHESTRATOR_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Resolve project directory ───────────────────────────────────────────────

PROJECT_DIR=""
EXTRA_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    EXTRA_ARGS+=("$arg")
  elif [[ -d "$arg" ]]; then
    PROJECT_DIR="$(cd "$arg" && pwd)"
  else
    EXTRA_ARGS+=("$arg")
  fi
done

if [[ -z "$PROJECT_DIR" ]]; then
  PROJECT_DIR="$(pwd)"
fi

# ── Dependency checks ───────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Install Python 3.11+ first." >&2
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info.major * 100 + sys.version_info.minor)')
if [[ "$PYTHON_VERSION" -lt 311 ]]; then
  echo "Error: Python 3.11+ required (found $(python3 --version))." >&2
  exit 1
fi

if ! command -v gemini &>/dev/null; then
  echo "Error: 'gemini' CLI not found. Install it first." >&2
  exit 1
fi

if ! command -v codex &>/dev/null; then
  echo "Error: 'codex' CLI not found. Install it first." >&2
  exit 1
fi

# ── Virtual environment + deps ──────────────────────────────────────────────

VENV="$ORCHESTRATOR_DIR/.venv"
if [[ ! -d "$VENV" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV"
fi

PYTHON="$VENV/bin/python3"

if ! "$PYTHON" -c "import anthropic" &>/dev/null; then
  echo "Installing anthropic SDK into .venv..."
  "$VENV/bin/pip" install -q "anthropic>=0.40.0"
fi

# ── Run ─────────────────────────────────────────────────────────────────────

echo "══════════════════════════════════════════"
echo "  Research Orchestrator"
echo "  Project: $(basename "$PROJECT_DIR")"
echo "══════════════════════════════════════════"
echo ""

export RESEARCH_ROOT="$PROJECT_DIR"
export ORCHESTRATOR_ROOT="$ORCHESTRATOR_DIR"

"$PYTHON" "$ORCHESTRATOR_DIR/orchestrator/run.py" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
