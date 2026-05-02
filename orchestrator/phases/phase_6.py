"""Phase 6A–6E: sequential paper writing pipeline."""
from orchestrator import git_utils, state
from orchestrator.agents import claude_agent
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT

METHODS_PROMPT = """Write the Methods section of the paper (600–1000 words).

Include:
1. Problem formulation with notation (define inputs, outputs, and the task formally)
2. Proposed method description — algorithm, architecture, key operations
3. Key design choices with justification (why these choices vs. alternatives)
4. Training procedure and loss function

Write directly to writing/methods.md, then run:
  git add writing/methods.md && git commit -m "writing: methods section"
"""

RESULTS_PROMPT = """Write the Results section of the paper (600–900 words).

Include:
1. Experimental setup: datasets, baselines, implementation details, compute used
2. Main results: prose description of the results table, citing specific numbers
3. Ablation analysis: what each intervention contributes
4. Analysis / qualitative observations

Write directly to writing/results.md, then run:
  git add writing/results.md && git commit -m "writing: results section"
"""

RELATED_WORK_POLISH_PROMPT = """Polish the related work draft below.

Improvements to make:
- Sharpen transitions between paragraphs
- Ensure each paragraph ends with an explicit "Unlike X and Y, our approach does Z" statement
- Verify every cited paper is correctly positioned relative to our contribution
- Remove any redundancy or vague claims

Write the polished version to writing/related-work.md, then run:
  git add writing/related-work.md && git commit -m "writing: related work polished"
"""

INTRO_PROMPT = """Write the Introduction section of the paper (500–700 words).
The introduction is written LAST because it must be grounded in actual results.

Structure:
1. Hook: one striking result or observation from the results section
2. Problem: what fails and why it matters (1 paragraph)
3. Gap: what existing work misses (cite 3–5 papers from related work)
4. Our approach: one paragraph summary of the method
5. Contributions: numbered list of exactly 3 concrete contributions
6. Roadmap: one sentence per remaining section

Write to writing/intro.md, then run:
  git add writing/intro.md && git commit -m "writing: introduction"
"""

DRAFT_PROMPT = """Assemble the complete paper draft.

1. Write a 250-word abstract: problem → gap → method → key result → implication
2. Assemble writing/draft.md in this order:
   # Abstract
   [250-word abstract]

   # Introduction
   [content from writing/intro.md]

   # Related Work
   [content from writing/related-work.md]

   # Methods
   [content from writing/methods.md]

   # Results
   [content from writing/results.md]

   # Conclusion
   [write 150 words: summarize contributions, acknowledge 2–3 limitations, suggest future work]

Write to writing/draft.md, then run:
  git add writing/draft.md && git commit -m "writing: full draft assembled"
"""


def run_6a() -> None:
    banner("Phase 6A — Methods Section (Claude)")
    if not state.has_placeholder("writing/methods.md"):
        log("Methods already written — skipping", "6A")
        return
    spec = (ROOT / "research-spec.md").read_text()
    code_spec = (ROOT / "code/code-spec.md").read_text()
    result = claude_agent.call_with_files(
        METHODS_PROMPT,
        {"research-spec.md": spec, "code/code-spec.md": code_spec},
    )
    (ROOT / "writing/methods.md").write_text(result)
    git_utils.git_commit(["writing/methods.md"], "writing: methods section")
    log("Methods written", "6A")


def run_6b() -> None:
    banner("Phase 6B — Results Section (Claude)")
    if not state.has_placeholder("writing/results.md") if (ROOT / "writing/results.md").exists() else True:
        pass  # need to run
    spec = (ROOT / "research-spec.md").read_text()
    analysis = (ROOT / "results/analysis.md").read_text()
    result = claude_agent.call_with_files(
        RESULTS_PROMPT,
        {"research-spec.md": spec, "results/analysis.md": analysis},
    )
    (ROOT / "writing/results.md").write_text(result)
    git_utils.git_commit(["writing/results.md"], "writing: results section")
    log("Results written", "6B")


def run_6c() -> None:
    banner("Phase 6C — Related Work Polish (Claude)")
    if not state.has_placeholder("writing/related-work.md"):
        log("Related work already polished — skipping", "6C")
        return
    synthesis = (ROOT / "literature/synthesis.md").read_text()
    related_work = (ROOT / "writing/related-work.md").read_text()
    result = claude_agent.call_with_files(
        RELATED_WORK_POLISH_PROMPT,
        {"literature/synthesis.md": synthesis, "writing/related-work.md": related_work},
    )
    (ROOT / "writing/related-work.md").write_text(result)
    git_utils.git_commit(["writing/related-work.md"], "writing: related work polished")
    log("Related work polished", "6C")


def run_6d() -> None:
    banner("Phase 6D — Introduction (Claude, written last)")
    if not state.has_placeholder("writing/intro.md"):
        log("Introduction already written — skipping", "6D")
        return
    files = {
        "writing/methods.md":      (ROOT / "writing/methods.md").read_text(),
        "writing/results.md":      (ROOT / "writing/results.md").read_text() if (ROOT / "writing/results.md").exists() else "",
        "writing/related-work.md": (ROOT / "writing/related-work.md").read_text(),
        "results/analysis.md":     (ROOT / "results/analysis.md").read_text(),
    }
    result = claude_agent.call_with_files(INTRO_PROMPT, files)
    (ROOT / "writing/intro.md").write_text(result)
    git_utils.git_commit(["writing/intro.md"], "writing: introduction")
    log("Introduction written", "6D")


def run_6e() -> None:
    banner("Phase 6E — Abstract + Full Draft Assembly (Claude)")
    if not state.has_placeholder("writing/draft.md"):
        log("Draft already assembled — skipping", "6E")
        return
    files = {
        "writing/intro.md":        (ROOT / "writing/intro.md").read_text(),
        "writing/related-work.md": (ROOT / "writing/related-work.md").read_text(),
        "writing/methods.md":      (ROOT / "writing/methods.md").read_text(),
        "writing/results.md":      (ROOT / "writing/results.md").read_text() if (ROOT / "writing/results.md").exists() else "",
        "results/analysis.md":     (ROOT / "results/analysis.md").read_text(),
    }
    result = claude_agent.call_with_files(DRAFT_PROMPT, files)
    (ROOT / "writing/draft.md").write_text(result)
    git_utils.git_commit(["writing/draft.md"], "writing: full draft assembled")
    log("Full draft assembled", "6E")
