"""Phase 1: Council simulation + search query generation."""
from orchestrator import git_utils, state
from orchestrator.agents import claude_agent
from orchestrator.logging_utils import banner, log

ROOT = state.ROOT

COUNCIL_SYSTEM = (
    "You are simulating a four-voice research council evaluating a research proposal. "
    "Be rigorous, specific, and actionable."
)

COUNCIL_PROMPT_TEMPLATE = """Read the research specification below and simulate a four-voice decision council.

=== research-spec.md ===
{spec}

Simulate these four reviewers:

ARCHITECT: Is this technically feasible with the proposed datasets and compute in 8–10 weeks?
SKEPTIC: What is the novelty risk? Is this already published or obviously in progress at a major lab?
PRAGMATIST: Is the scope right for a single conference paper? What should be cut?
CRITIC: What is the weakest assumption? What would make reviewers reject this outright?

Then output:
COUNCIL_VERDICT: GO | CONDITIONAL-GO | NO-GO
JUSTIFICATION: one paragraph per voice
CONDITIONS: list of conditions to apply before proceeding (or "none" if GO)

If CONDITIONAL-GO, also output:
SPEC_UPDATES: list of concrete changes to apply to research-spec.md (or "none")
"""

SEARCH_QUERY_TEMPLATE = """You have reviewed the research spec below. Now write a fully populated literature/search-queries.md file.

=== research-spec.md ===
{spec}

Replace EVERY placeholder in the template below with real, specific values tailored to this research project.
Include 8 concrete query strings targeting the specific hypotheses H1, H2, H3.
Set realistic expected hit counts. Write real inclusion/exclusion criteria.

=== Current literature/search-queries.md (template to populate) ===
{current_queries}

Output ONLY the complete populated file content. Do not include any commentary before or after.
"""


def run() -> None:
    banner("Phase 1 — Idea Validation + Search Query Generation")
    spec = (ROOT / "research-spec.md").read_text()

    # 1a. Council simulation
    log("Running council simulation...", "1")
    council_result = claude_agent.call(
        COUNCIL_PROMPT_TEMPLATE.format(spec=spec),
        system=COUNCIL_SYSTEM,
    )
    print(council_result)

    if "COUNCIL_VERDICT: NO-GO" in council_result:
        raise RuntimeError(
            "Council returned NO-GO. Revise research-spec.md to address the issues above, then re-run."
        )

    # 1b. Generate search queries
    log("Generating search queries...", "1")
    current_queries = (ROOT / "literature/search-queries.md").read_text() if (ROOT / "literature/search-queries.md").exists() else ""
    queries_result = claude_agent.call(
        SEARCH_QUERY_TEMPLATE.format(spec=spec, current_queries=current_queries),
    )
    (ROOT / "literature").mkdir(exist_ok=True)
    (ROOT / "literature/search-queries.md").write_text(queries_result)

    # 1c. Commit
    git_utils.git_commit(
        ["research-spec.md", "literature/search-queries.md"],
        "phase-1: council passed, search queries generated",
    )
    log("Phase 1 complete. Search queries written to literature/search-queries.md", "1")
