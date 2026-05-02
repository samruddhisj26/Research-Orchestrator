"""Phases 3A–3D: code spec, code generation, data prep, code review gate."""
import re
from concurrent.futures import ThreadPoolExecutor

from orchestrator import git_utils, state
from orchestrator.agents import claude_agent, codex_agent, gemini_agent
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT


def run_3a() -> None:
    """Phase 3A: fill code/code-spec.md from research-spec (Claude)."""
    banner("Phase 3A — Code Specification (Claude)")
    spec = (ROOT / "research-spec.md").read_text()
    synthesis = (ROOT / "literature/synthesis.md").read_text()
    template = (ROOT / "code/code-spec.md").read_text()

    prompt = f"""Fill in the code specification template below.
Be precise enough for an AI code generator to implement without asking questions.
Replace every placeholder ([grid], <!--...-->, etc.) with concrete values.

=== research-spec.md ===
{spec}

=== literature/synthesis.md (excerpt for baseline implementation notes) ===
{synthesis[:3000]}

=== code/code-spec.md (template to populate) ===
{template}

Output ONLY the complete populated code-spec.md content.
Then write it to disk at code/code-spec.md and run:
  git add code/code-spec.md && git commit -m "phase-3: code spec written"
"""
    result = claude_agent.call(prompt)
    # Write the result to disk (in case Claude doesn't do it directly)
    if result.strip():
        (ROOT / "code/code-spec.md").write_text(result)
    git_utils.git_commit(["code/code-spec.md"], "phase-3: code spec written")
    log("Code spec written", "3A")


def run_3b() -> None:
    """Phase 3B: code generation (Codex) + data prep (Gemini), in parallel."""
    banner("Phase 3B — Code Generation + Data Prep (Codex + Gemini)")
    spec = (ROOT / "code/code-spec.md").read_text()
    research_spec = (ROOT / "research-spec.md").read_text()

    codex_prompt = f"""Read the code specification below and generate all required experiment files.

=== code/code-spec.md ===
{spec}

Generate these files exactly (write them to the code/ directory):
  code/model.py         — proposed method class matching the BaseModel interface in the spec
  code/baselines.py     — all baseline classes, same interface
  code/train.py         — training loop: load data, train, checkpoint, log metrics to CSV
  code/evaluate.py      — evaluation harness: load checkpoint, run all metrics, write results/run_<timestamp>.csv
  code/visualize.py     — read results/*.csv, write results/figures/, write results/tables.tex
  code/run_experiments.sh — end-to-end script: runs proposed method + all baselines × 3 seeds
  requirements.txt      — all Python dependencies with pinned versions

After writing all files:
  git add code/ requirements.txt && git commit -m "codex: experiment codebase generated"
"""
    # Extract dataset list from research spec
    datasets_line = "HotPotQA and MuSiQue (see research-spec.md)"
    m = re.search(r"Datasets \(train\)[^\n]*\|\s*([^\n|]+)", research_spec)
    if m:
        datasets_line = m.group(1).strip()

    gemini_prompt = f"""Download and prepare the required datasets for this ML research project.

Datasets needed: {datasets_line}

For each dataset:
1. Download from the canonical public source (HuggingFace datasets, official website, or GitHub release)
2. Validate file integrity (check line/example counts)
3. Create train/val/test splits: 80% / 10% / 10% (unless the paper specifies different splits)
4. Write data/README.md documenting: schema, split sizes, download commands

Output: populate the data/ directory.
After writing:
  git add data/ && git commit -m "gemini: datasets prepared"
"""
    log("Launching Codex (code generation) and Gemini (data prep) in parallel...", "3B")
    with ThreadPoolExecutor(max_workers=2) as ex:
        codex_future = ex.submit(codex_agent.run, codex_prompt, None, "experiment-code")
        gemini_future = ex.submit(gemini_agent.run, gemini_prompt, None, "data-prep")
        codex_future.result()
        gemini_future.result()

    log("Code generation + data prep complete", "3B")


def run_3d() -> None:
    """Phase 3D: code review gate (Claude)."""
    banner("Phase 3D — Code Review Gate (Claude)")
    code_files: dict[str, str] = {}
    for fname in ["model.py", "baselines.py", "train.py", "evaluate.py", "run_experiments.sh"]:
        p = ROOT / "code" / fname
        if p.exists():
            code_files[fname] = p.read_text()

    spec = (ROOT / "code/code-spec.md").read_text()

    prompt = f"""Review this experiment codebase for four specific issues:

1. CORRECTNESS: Does evaluate.py implement each metric from code-spec.md correctly? Flag formula errors.
2. DATA LEAKAGE: Does train.py ever access the test split before evaluation?
3. REPRODUCIBILITY: Does run_experiments.sh set random seeds for all conditions × seeds?
4. BASELINE FAIRNESS: Do baselines use the same data splits and evaluation code as the proposed method?

For each HIGH or CRITICAL issue found: output the corrected file using this exact format:
=== FIXED: code/<filename> ===
<full corrected file content>

For LOW issues: add an inline comment.

End with:
ISSUES_FIXED: <comma-separated list of filenames fixed, or "none">

=== code/code-spec.md ===
{spec}
"""
    result = claude_agent.call_with_files(prompt, code_files)
    print(result)

    # Parse and write any fixed files
    for match in re.finditer(r"=== FIXED: code/(\S+) ===\n(.*?)(?====|$)", result, re.DOTALL):
        fname, content = match.group(1), match.group(2).strip()
        target = ROOT / "code" / fname
        target.write_text(content)
        log(f"Fixed: code/{fname}", "3D")

    gate = state.write_gate("code-reviewed")
    git_utils.git_commit(
        [str((ROOT / "code").relative_to(ROOT)), str(gate.relative_to(ROOT))],
        "phase-3: code review complete",
    )
    log("Code review gate passed", "3D")
