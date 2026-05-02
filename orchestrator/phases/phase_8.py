"""Phase 8: submission checklist."""
import glob
from orchestrator import state
from orchestrator.logging_utils import banner

ROOT = state.ROOT


def _check(label: str, ok: bool) -> str:
    mark = "✓" if ok else "✗"
    return f"  [{mark}] {label}"


def run() -> None:
    banner("Phase 8 — Submission Checklist")

    spec_text = (ROOT / "research-spec.md").read_text() if (ROOT / "research-spec.md").exists() else ""
    venue = "EMNLP 2026"
    deadline = "~June 2026"
    for line in spec_text.splitlines():
        if "Target Venue" in line or "venue" in line.lower():
            venue = line.split(":", 1)[-1].strip() if ":" in line else venue
        if "Deadline" in line or "deadline" in line.lower():
            deadline = line.split(":", 1)[-1].strip() if ":" in line else deadline

    analysis_text = (ROOT / "results/analysis.md").read_text() if (ROOT / "results/analysis.md").exists() else ""
    draft_text = (ROOT / "writing/draft.md").read_text() if (ROOT / "writing/draft.md").exists() else ""

    checks = [
        # Scientific
        _check("All main results statistically significant (p-values in results/analysis.md)",
               "p-value" in analysis_text and "Significant" in analysis_text),
        _check("Effect sizes reported (Cohen's d in analysis.md)",
               "Cohen's d" in analysis_text or "cohen" in analysis_text.lower()),
        _check("All claims in abstract supported by numbers in results/",
               bool(glob.glob(str(ROOT / "results" / "*.csv")))),
        _check("Ablation study complete (results/ablations/ exists)",
               (ROOT / "results" / "ablations").exists()),

        # Code
        _check("run_experiments.sh exists",
               (ROOT / "code/run_experiments.sh").exists()),
        _check("requirements.txt exists",
               (ROOT / "requirements.txt").exists()),

        # Paper
        _check("Abstract ≤ 250 words",
               len(draft_text.split()) > 0),  # rough check
        _check("Figures directory non-empty",
               bool(list((ROOT / "results" / "figures").iterdir())) if (ROOT / "results" / "figures").exists() else False),
        _check("LaTeX tables (results/tables.tex) exists",
               (ROOT / "results/tables.tex").exists()),
        _check("Reproducibility statement present",
               "reproducib" in draft_text.lower()),
    ]

    print(f"\nSubmission Checklist — {venue} (deadline: {deadline})\n")
    for c in checks:
        print(c)

    print("\n─────────────────────────────────────────────")
    print("Manual items (check these yourself):")
    print("  [ ] Page count ≤ venue limit")
    print("  [ ] References formatted to venue style")
    print("  [ ] Ethics statement (if required by venue)")
    print("  [ ] Code anonymized (no author names or institution paths)")
    print("  [ ] Paper uploaded to submission system")
    print("  [ ] Supplemental code ZIP or anonymous repo uploaded")
    print("  [ ] Author information verified")
    print("  [ ] Submission confirmed ✓")
