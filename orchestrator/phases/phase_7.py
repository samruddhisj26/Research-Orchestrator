"""Phase 7: adversarial review loop until both reviewers pass."""
from orchestrator import git_utils, state
from orchestrator.agents import claude_agent
from orchestrator.errors import GateFailedError
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT

MAX_ITERATIONS = 5

REVIEW_PROMPT_TEMPLATE = """Simulate TWO peer reviewers (NeurIPS/EMNLP level) reviewing the full paper draft.

=== writing/draft.md ===
{draft}

REVIEWER 1 — Conservative area chair:
Evaluate on:
- Novelty (1–5): Is the contribution incremental or significant?
- Soundness (1–5): Are claims backed by evidence? Statistical validity?
- Presentation (1–5): Clear and well-organized?
- Top 3 issues that MUST be addressed before acceptance.
Overall score: Strong Accept / Accept / Weak Accept / Weak Reject / Reject

REVIEWER 2 — Aggressive area chair:
Evaluate on:
- Significance: Does this advance the state of the art meaningfully?
- Reproducibility: Can the community reproduce this from the paper alone?
- Related work: Are the right papers cited and correctly positioned?
- Top 3 issues that MUST be addressed.
Overall score: Strong Accept / Accept / Weak Accept / Weak Reject / Reject

If BOTH reviewers score Weak Accept or better, output:
GATE: PASS
ISSUES: none

Otherwise output:
GATE: FAIL
ISSUES:
- [section name]: [specific issue to fix]
- [section name]: [specific issue to fix]
(list every CRITICAL and HIGH issue that blocks acceptance)
"""

FIX_PROMPT_TEMPLATE = """The draft has received reviewer feedback. Fix each issue listed below.

=== Issues to fix ===
{issues}

=== Current writing/draft.md ===
{draft}

For each issue:
1. Identify which section of the draft needs to change
2. Make the change directly
3. Output the full revised draft

Output ONLY the complete revised draft.md content.
"""


def run() -> None:
    banner("Phase 7 — Adversarial Review Loop (santa-loop)")

    for iteration in range(1, MAX_ITERATIONS + 1):
        log(f"Review iteration {iteration}/{MAX_ITERATIONS}", "7")
        draft = (ROOT / "writing/draft.md").read_text()
        result = claude_agent.call(
            REVIEW_PROMPT_TEMPLATE.format(draft=draft),
            max_tokens=4096,
        )
        print(result)

        if "GATE: PASS" in result:
            gate = state.write_gate("draft-passed")
            git_utils.git_commit([str(gate.relative_to(ROOT))], "gate: draft review passed")
            log(f"Draft gate passed on iteration {iteration}", "7")
            return

        # Extract issues and fix
        issues_start = result.find("ISSUES:")
        issues_text = result[issues_start:].strip() if issues_start >= 0 else result

        log(f"Iteration {iteration} failed — applying fixes...", "7")
        revised = claude_agent.call(
            FIX_PROMPT_TEMPLATE.format(issues=issues_text, draft=draft),
            max_tokens=8192,
        )
        (ROOT / "writing/draft.md").write_text(revised)
        git_utils.git_commit(
            ["writing/draft.md"],
            f"writing: revision {iteration} addressing reviewer feedback",
        )

    raise GateFailedError(
        f"Draft did not pass review after {MAX_ITERATIONS} iterations.\n\n"
        "Read writing/draft.md and the reviewer feedback above, then revise manually.\n"
        "Delete .gate-draft-passed if it was partially written, and re-run ./run.sh"
    )
