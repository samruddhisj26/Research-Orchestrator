#!/usr/bin/env python3
"""Main orchestrator entry point. Called by run.sh."""

import os
import sys
from pathlib import Path

# Ensure the project root (parent of orchestrator/) is on sys.path
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Set RESEARCH_ROOT to the project directory
os.environ.setdefault("RESEARCH_ROOT", str(_PROJECT_ROOT))

# Import phase handlers (top-level to catch import errors before any agent work)
from orchestrator import state
from orchestrator.errors import ConfigError, GateFailedError, OrchestratorError
from orchestrator.logging_utils import banner, log
from orchestrator.phases import (
    phase_1,
    phase_2,
    phase_3,
    phase_5,
    phase_6,
    phase_7,
    phase_8,
)

MANUAL_PHASES = {
    "0": (
        "Phase 0: research-spec.md is not filled in yet.\n\n"
        "Open research-spec.md and fill in:\n"
        "  • Research Question (one sentence)\n"
        "  • Hypotheses H1, H2, H3\n"
        "  • Proposed Method (2 paragraphs)\n"
        "  • Datasets, Baselines, Primary metric\n"
        "  • Target venue and deadline\n\n"
        "Then re-run ./run.sh"
    ),
    "3C": (
        "Phase 3C: Codex is still generating code.\n\n"
        "Wait for the Codex session to finish and commit code/run_experiments.sh,\n"
        "then re-run ./run.sh"
    ),
    "4": (
        "Phase 4: Experiments must run on your compute.\n\n"
        "  bash code/run_experiments.sh\n\n"
        "This writes results to results/run_*.csv (one file per experiment run).\n"
        "Commit results when done:\n"
        "  git add results/ && git commit -m 'experiments: main results'\n\n"
        "Then re-run ./run.sh"
    ),
}

PHASE_HANDLERS = {
    "1":  phase_1.run,
    "2A": phase_2.run_2a,
    "2B": phase_2.run_2b,
    "2C": phase_2.run_2c,
    "2G": phase_2.run_2g,
    "3A": phase_3.run_3a,
    "3B": phase_3.run_3b,
    "3D": phase_3.run_3d,
    "5A": phase_5.run_5a,
    "5B": phase_5.run_5b,
    "5G": phase_5.run_5g,
    "6A": phase_6.run_6a,
    "6B": phase_6.run_6b,
    "6C": phase_6.run_6c,
    "6D": phase_6.run_6d,
    "6E": phase_6.run_6e,
    "7":  phase_7.run,
    "8":  phase_8.run,
}

DRY_RUN = "--dry-run" in sys.argv


def _validate_env() -> None:
    """Fail fast if required environment is missing."""
    # ANTHROPIC_API_KEY is checked lazily in claude_agent._get_client()
    # but we can warn early here if it's absent and a Claude phase is next
    pass


def main() -> None:
    _validate_env()

    phase = state.detect_phase()
    banner(f"Research Orchestrator — Phase {phase}")

    if phase in MANUAL_PHASES:
        print(MANUAL_PHASES[phase])
        sys.exit(0)

    handler = PHASE_HANDLERS.get(phase)
    if handler is None:
        print(f"Unknown phase: {phase}", file=sys.stderr)
        sys.exit(1)

    if DRY_RUN:
        routing = __import__("orchestrator.config", fromlist=["PHASE_ROUTING"]).PHASE_ROUTING
        agent = routing.get(phase, "unknown")
        print(f"[DRY RUN] Phase {phase} → agent: {agent}")
        print(f"[DRY RUN] Handler: {handler.__module__}.{handler.__name__}")
        sys.exit(0)

    try:
        handler()
        next_phase = state.detect_phase()
        if next_phase != phase:
            log(f"\n✓ Phase {phase} complete. Next phase: {next_phase}")
            log("Re-run ./run.sh to continue.")
        else:
            log(
                f"\nPhase {phase} handler completed but phase did not advance. "
                "Check output above for errors or missing files."
            )
    except GateFailedError as e:
        print(f"\n[GATE FAILED]\n{e}", file=sys.stderr)
        sys.exit(2)
    except ConfigError as e:
        print(f"\n[CONFIG ERROR]\n{e}", file=sys.stderr)
        sys.exit(1)
    except OrchestratorError as e:
        print(f"\n[ORCHESTRATOR ERROR]\n{e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
