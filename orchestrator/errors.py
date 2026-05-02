class OrchestratorError(Exception):
    """Base for all orchestrator errors."""


class AgentError(OrchestratorError):
    """An external agent (Gemini/Codex) failed or timed out."""


class GateFailedError(OrchestratorError):
    """A quality gate (santa-loop simulation) did not pass."""


class PhaseError(OrchestratorError):
    """A phase handler raised an unexpected error."""


class ConfigError(OrchestratorError):
    """Missing environment variable or config value."""
