"""Phases 2A–2G: screening, extraction, synthesis, hypothesis gate."""
from orchestrator import git_utils, state
from orchestrator.agents import claude_agent, gemini_agent
from orchestrator.errors import GateFailedError
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT


def run_2a() -> None:
    """Phase 2A: parallel abstract screening via 3 Gemini sessions."""
    banner("Phase 2A — Abstract Screening (Gemini × 3)")
    queries_text = (ROOT / "literature/search-queries.md").read_text()
    spec_text = (ROOT / "research-spec.md").read_text()

    tasks: list[tuple[str, str]] = []
    for i, (start, end) in enumerate([(1, 60), (61, 120), (121, 180)], start=1):
        out_file = ROOT / f"literature/screening-batch-{i}.csv"
        if out_file.exists():
            log(f"Batch {i} already exists — skipping", "2A")
            continue
        prompt = f"""You are screening academic papers for a systematic literature review.

Research context:
{spec_text}

Search queries and inclusion/exclusion criteria:
{queries_text}

Task:
1. Use the queries above to search arXiv, Semantic Scholar, and Papers With Code.
2. Collect papers {start}–{end} (by query hit order, deduplicated).
3. For each paper, read the title and abstract, then decide: Include / Exclude / Unsure.

Output ONLY a CSV file saved to: literature/screening-batch-{i}.csv
CSV columns (header required): id,title,year,authors,arxiv_id,decision,reason
- decision: exactly one of Include / Exclude / Unsure
- reason: one sentence

After writing the file, run:
  git add literature/screening-batch-{i}.csv && git commit -m "gemini: screening batch {i}"
"""
        tasks.append((f"screening-batch-{i}", prompt))

    if tasks:
        log(f"Launching {len(tasks)} parallel Gemini screening jobs...", "2A")
        gemini_agent.run_parallel(tasks)

    # Verify outputs exist (Gemini may have committed them)
    missing = [i for i in [1, 2, 3] if not (ROOT / f"literature/screening-batch-{i}.csv").exists()]
    if missing:
        log(f"Warning: batches {missing} not found on disk — Gemini may have committed but not written locally.", "2A")

    log("Screening complete", "2A")


def run_2b() -> None:
    """Phase 2B: data extraction via Gemini."""
    banner("Phase 2B — Data Extraction (Gemini)")
    spec_text = (ROOT / "research-spec.md").read_text()
    prompt = f"""Read the following CSV files from the project directory:
  literature/screening-batch-1.csv
  literature/screening-batch-2.csv
  literature/screening-batch-3.csv

For every paper marked "Include", extract these fields:
  - authors: last name of first author + "et al." if >2 authors
  - year: publication year
  - method_name: what the authors call their approach
  - datasets_used: comma-separated dataset names
  - primary_metric: metric name
  - primary_metric_value: reported number
  - key_claim: one sentence
  - relevance_to: which hypothesis (H1 / H2 / H3 / general)

Research context for relevance mapping:
{spec_text}

Output: a JSON array saved to literature/extraction-data.json
Each element is an object with the fields above.

After writing the file, run:
  git add literature/extraction-data.json && git commit -m "gemini: data extraction complete"
"""
    gemini_agent.run(prompt, session_label="extraction")
    log("Extraction complete", "2B")


def run_2c() -> None:
    """Phase 2C: literature synthesis (Claude)."""
    banner("Phase 2C — Literature Synthesis (Claude)")
    extraction = (ROOT / "literature/extraction-data.json").read_text()
    spec = (ROOT / "research-spec.md").read_text()

    prompt = f"""Based on the extraction data and research spec below, write two files to disk.

FILE 1: literature/synthesis.md
Include these sections:
1. Dominant methods and their benchmark results (table with Method | Dataset | Metric | Value columns)
2. Datasets and benchmarks used across the literature
3. Open problems and explicit "future work" statements from included papers
4. Papers most relevant to each hypothesis — H1, H2, H3 in separate subsections
5. Research gaps: untried combinations of method + dataset + metric

FILE 2: writing/related-work.md
Write a 700-word related work section grouped by thematic cluster.
End each paragraph with: "Unlike X and Y, our approach does Z."

After writing both files, run:
  git add literature/synthesis.md writing/related-work.md
  git commit -m "phase-2: synthesis and related work draft complete"

=== research-spec.md ===
{spec}

=== literature/extraction-data.json ===
{extraction}
"""
    claude_agent.call(prompt)
    log("Synthesis complete", "2C")


def run_2g() -> None:
    """Phase 2G: hypothesis gate (santa-loop simulation)."""
    banner("Phase 2G — Hypothesis Gate (santa-loop)")
    spec = (ROOT / "research-spec.md").read_text()
    synthesis = (ROOT / "literature/synthesis.md").read_text()

    prompt = f"""Simulate TWO peer reviewers assessing research hypotheses before any code is written.

=== research-spec.md ===
{spec}

=== literature/synthesis.md ===
{synthesis}

REVIEWER 1 — Conservative area chair:
- Is there a clearly stated gap in the existing literature?
- Are the hypotheses falsifiable and specific?
- Is the evaluation plan adequate (right datasets, right metrics)?
Score: Strong Accept / Accept / Weak Accept / Weak Reject / Reject

REVIEWER 2 — Aggressive ML researcher:
- Is this genuinely novel vs. the included papers? Cite specific papers if overlap exists.
- Would the expected findings move the field, or is the delta too small?
- Are there fatal confounds in the experiment design?
Score: Strong Accept / Accept / Weak Accept / Weak Reject / Reject

Output format (use EXACTLY these labels):
REVIEWER_1_SCORE: <score>
REVIEWER_1_VERDICT: <one paragraph>
REVIEWER_2_SCORE: <score>
REVIEWER_2_VERDICT: <one paragraph>
GATE: PASS
FAIL_REASONS: none

OR if either reviewer scores Weak Reject or below:
GATE: FAIL
FAIL_REASONS: <bulleted list of what must be addressed>
"""
    result = claude_agent.call(prompt)
    print(result)

    if "GATE: PASS" not in result:
        raise GateFailedError(
            "Hypothesis gate FAILED.\n\nReviewer feedback printed above.\n\n"
            "Update research-spec.md to address the FAIL_REASONS, then re-run ./run.sh"
        )

    gate = state.write_gate("lit-passed")
    git_utils.git_commit([str(gate.relative_to(ROOT))], "gate: hypothesis review passed")
    log("Gate passed — advancing to Phase 3", "2G")
