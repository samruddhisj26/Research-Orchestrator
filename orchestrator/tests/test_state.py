"""Tests for orchestrator/state.py — phase detection and gate management."""
import os
import tempfile
from pathlib import Path

import pytest

# Point RESEARCH_ROOT at a temp directory for each test
@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("RESEARCH_ROOT", str(tmp_path))
    # Reload state module so ROOT picks up the new env var
    import importlib
    import orchestrator.state as s
    importlib.reload(s)
    return tmp_path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestHasPlaceholder:
    def test_missing_file_is_placeholder(self, project_dir: Path) -> None:
        import orchestrator.state as s
        assert s.has_placeholder("nonexistent.md") is True

    def test_html_comment_marker(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "test.md", "# Title\n<!-- fill this in -->\n")
        assert s.has_placeholder("test.md") is True

    def test_bracket_x_marker(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "test.md", "Query: [X] something\n")
        assert s.has_placeholder("test.md") is True

    def test_empty_table_row(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "test.md", "| col1 | col2 |\n| | |\n")
        assert s.has_placeholder("test.md") is True

    def test_real_content_not_placeholder(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "test.md", "# Methods\nWe propose a new approach.\n")
        assert s.has_placeholder("test.md") is False


class TestWriteGate:
    def test_creates_gate_file(self, project_dir: Path) -> None:
        import orchestrator.state as s
        gate = s.write_gate("test-gate")
        assert gate.exists()
        assert gate.name == ".gate-test-gate"

    def test_gate_is_empty(self, project_dir: Path) -> None:
        import orchestrator.state as s
        gate = s.write_gate("empty")
        assert gate.read_text() == ""


class TestDetectPhase:
    def _scaffold(self, project_dir: Path) -> None:
        """Create the minimum file structure for a valid project."""
        _write(project_dir / "research-spec.md", "# Spec\nReal content with no placeholders.\n")
        _write(project_dir / "literature/search-queries.md", "# Queries\nReal query content.\n")
        for i in [1, 2, 3]:
            _write(
                project_dir / f"literature/screening-batch-{i}.csv",
                "id,title,year,authors,arxiv_id,decision,reason\n1,Test,2024,Auth,,Include,good\n",
            )
        _write(project_dir / "literature/extraction-data.json", '[{"authors": "Smith et al."}]')
        _write(project_dir / "literature/synthesis.md", "# Synthesis\nReal synthesis content.\n")

    def test_phase_0_when_spec_has_placeholder(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\n<!-- fill in -->\n")
        assert s.detect_phase() == "0"

    def test_phase_1_when_no_search_queries(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\nReal content.\n")
        assert s.detect_phase() == "1"

    def test_phase_1_when_search_queries_has_placeholder(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\nReal content.\n")
        _write(project_dir / "literature/search-queries.md", "# Queries\n| 1 | [X] | H1 | |\n")
        assert s.detect_phase() == "1"

    def test_phase_2a_when_batches_missing(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\nReal content.\n")
        _write(project_dir / "literature/search-queries.md", "# Queries\nReal query.\n")
        assert s.detect_phase() == "2A"

    def test_phase_2a_when_one_batch_missing(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\nReal content.\n")
        _write(project_dir / "literature/search-queries.md", "# Queries\nReal query.\n")
        _write(project_dir / "literature/screening-batch-1.csv", "id,title\n")
        _write(project_dir / "literature/screening-batch-2.csv", "id,title\n")
        # batch-3 missing
        assert s.detect_phase() == "2A"

    def test_phase_2b_after_all_batches(self, project_dir: Path) -> None:
        import orchestrator.state as s
        _write(project_dir / "research-spec.md", "# Spec\nReal content.\n")
        _write(project_dir / "literature/search-queries.md", "# Queries\nReal query.\n")
        for i in [1, 2, 3]:
            _write(project_dir / f"literature/screening-batch-{i}.csv", "id,title\n")
        assert s.detect_phase() == "2B"

    def test_phase_2g_when_gate_missing(self, project_dir: Path) -> None:
        import orchestrator.state as s
        self._scaffold(project_dir)
        assert s.detect_phase() == "2G"

    def test_phase_3a_after_lit_gate(self, project_dir: Path) -> None:
        import orchestrator.state as s
        self._scaffold(project_dir)
        (project_dir / ".gate-lit-passed").touch()
        _write(project_dir / "code/code-spec.md", "# Spec\n<!-- fill in -->\n")
        assert s.detect_phase() == "3A"

    def test_phase_4_when_no_results(self, project_dir: Path) -> None:
        import orchestrator.state as s
        self._scaffold(project_dir)
        (project_dir / ".gate-lit-passed").touch()
        _write(project_dir / "code/code-spec.md", "# Code Spec\nReal content.\n")
        _write(project_dir / "code/model.py", "class Model: pass\n")
        _write(project_dir / "code/run_experiments.sh", "#!/bin/bash\necho done\n")
        (project_dir / ".gate-code-reviewed").touch()
        assert s.detect_phase() == "4"

    def test_phase_8_when_everything_done(self, project_dir: Path) -> None:
        import orchestrator.state as s
        self._scaffold(project_dir)
        (project_dir / ".gate-lit-passed").touch()
        _write(project_dir / "code/code-spec.md", "# Code Spec\nReal content.\n")
        _write(project_dir / "code/model.py", "class Model: pass\n")
        _write(project_dir / "code/run_experiments.sh", "#!/bin/bash\n")
        (project_dir / ".gate-code-reviewed").touch()
        _write(project_dir / "results/run_1.csv", "method,score\nours,0.8\n")
        _write(project_dir / "results/analysis.md", "# Analysis\nReal analysis.\n")
        (project_dir / "results/figures").mkdir()
        _write(project_dir / "results/figures/main.pdf", "fake pdf")
        (project_dir / ".gate-results-passed").touch()
        _write(project_dir / "writing/methods.md", "# Methods\nReal methods.\n")
        _write(project_dir / "writing/results.md", "# Results\nReal results.\n")
        _write(project_dir / "writing/related-work.md", "# Related Work\nReal related work.\n")
        _write(project_dir / "writing/intro.md", "# Introduction\nReal intro.\n")
        _write(project_dir / "writing/draft.md", "# Draft\nReal draft content.\n")
        (project_dir / ".gate-draft-passed").touch()
        assert s.detect_phase() == "8"


class TestConfigModule:
    def test_phase_routing_has_18_entries(self) -> None:
        from orchestrator.config import PHASE_ROUTING
        assert len(PHASE_ROUTING) == 18

    def test_all_claude_phases_have_model(self) -> None:
        from orchestrator.config import CLAUDE_MODEL_FOR_PHASE, PHASE_ROUTING
        claude_phases = {p for p, agent in PHASE_ROUTING.items() if agent == "claude"}
        for phase in claude_phases:
            assert phase in CLAUDE_MODEL_FOR_PHASE, f"Phase {phase} has no Claude model assigned"


class TestErrorsModule:
    def test_all_errors_importable(self) -> None:
        from orchestrator.errors import (
            AgentError,
            ConfigError,
            GateFailedError,
            OrchestratorError,
            PhaseError,
        )
        assert issubclass(AgentError, OrchestratorError)
        assert issubclass(GateFailedError, OrchestratorError)
        assert issubclass(PhaseError, OrchestratorError)
        assert issubclass(ConfigError, OrchestratorError)
