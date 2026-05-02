"""Phases 5A–5G: statistical analysis, figures, results gate."""
import glob

from orchestrator import git_utils, state
from orchestrator.agents import claude_agent, codex_agent
from orchestrator.errors import GateFailedError
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT


def run_5a() -> None:
    """Phase 5A: statistical analysis (Claude)."""
    banner("Phase 5A — Statistical Analysis (Claude)")

    result_files: dict[str, str] = {}
    for path in glob.glob(str(ROOT / "results" / "*.csv")):
        result_files[path.split("/")[-1]] = open(path).read()

    template = (ROOT / "results/analysis.md").read_text()
    spec = (ROOT / "research-spec.md").read_text()

    csv_block = "".join(f"=== {k} ===\n{v}\n" for k, v in result_files.items())

    prompt = f"""Fill in the results analysis template with actual numbers from the CSV files.

For each comparison (Ours vs. each baseline):
- Describe a paired t-test and show scipy.stats code in a fenced Python block
- Report p-value and Cohen's d
- Label: Significant (p < 0.05) or Not Significant

Write the completed analysis to results/analysis.md, then run:
  git add results/analysis.md && git commit -m "phase-5: statistical analysis complete"

=== research-spec.md ===
{spec}

=== results/analysis.md (template to fill) ===
{template}

=== Results CSV files ===
{csv_block}
"""
    claude_agent.call(prompt)
    log("Analysis complete", "5A")


def run_5b() -> None:
    """Phase 5B: figure generation (Codex)."""
    banner("Phase 5B — Figures (Codex)")

    (ROOT / "results/figures").mkdir(parents=True, exist_ok=True)

    analysis = (ROOT / "results/analysis.md").read_text()
    csv_files = glob.glob(str(ROOT / "results" / "*.csv"))

    prompt = f"""Read the analysis and CSV files below. Generate publication-quality figures and LaTeX tables.

=== results/analysis.md ===
{analysis}

CSV files available: {", ".join(csv_files)}

Generate these files:
  results/figures/main_results.pdf  — bar chart or line plot of main results, error bars from std across seeds, grayscale-readable
  results/figures/ablation.pdf      — ablation results visualization
  results/tables.tex                — LaTeX booktabs table of main results (bold our method's row)

Requirements:
  - Use matplotlib or seaborn
  - 300 DPI minimum
  - Font size ≥ 10pt (readable at column width)
  - All axes labeled, all legends present
  - Grayscale distinguishable without color

After generating:
  git add results/figures/ results/tables.tex && git commit -m "codex: figures generated"
"""
    codex_agent.run(prompt, label="figures")
    log("Figures complete", "5B")


def run_5g() -> None:
    """Phase 5G: results gate (santa-loop simulation)."""
    banner("Phase 5G — Results Gate (santa-loop)")

    analysis = (ROOT / "results/analysis.md").read_text()
    spec = (ROOT / "research-spec.md").read_text()

    prompt = f"""Simulate TWO peer reviewers assessing the experimental results before paper writing begins.

=== research-spec.md ===
{spec}

=== results/analysis.md ===
{analysis}

REVIEWER 1 — Conservative statistician:
- Are the reported improvements statistically significant (p < 0.05)?
- Are effect sizes (Cohen's d) practically meaningful or marginal?
- Are there enough seeds/runs to trust the variance estimates?
Score: Accept / Weak Accept / Weak Reject / Reject

REVIEWER 2 — Aggressive ML reviewer:
- Do the results actually support all three hypotheses in the spec?
- Are there missing baselines a reviewer would demand?
- Is there cherry-picking risk in how results are selected or reported?
Score: Accept / Weak Accept / Weak Reject / Reject

Output format (use EXACTLY these labels):
REVIEWER_1_SCORE: <score>
REVIEWER_2_SCORE: <score>
GATE: PASS
FAIL_REASONS: none

OR if either scores Weak Reject or below:
GATE: FAIL
FAIL_REASONS: <bulleted list>
"""
    result = claude_agent.call(prompt)
    print(result)

    if "GATE: PASS" not in result:
        raise GateFailedError(
            "Results gate FAILED.\n\nReviewer feedback printed above.\n\n"
            "Run additional experiments or analysis to address FAIL_REASONS, then re-run ./run.sh"
        )

    gate = state.write_gate("results-passed")
    git_utils.git_commit([str(gate.relative_to(ROOT))], "gate: results review passed")
    log("Results gate passed — advancing to Phase 6", "5G")
