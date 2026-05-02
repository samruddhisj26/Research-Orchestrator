PHASE_ROUTING = {
    "1":  "claude",
    "2A": "gemini",
    "2B": "gemini",
    "2C": "claude",
    "2G": "claude",
    "3A": "claude",
    "3B": "codex",
    "3D": "claude",
    "5A": "claude",
    "5B": "codex",
    "5G": "claude",
    "6A": "claude",
    "6B": "claude",
    "6C": "claude",
    "6D": "claude",
    "6E": "claude",
    "7":  "claude",
    "8":  "internal",
}

CLAUDE_MODEL_FAST = "claude-haiku-4-5-20251001"
CLAUDE_MODEL_MAIN = "claude-sonnet-4-6"

CLAUDE_MODEL_FOR_PHASE: dict[str, str] = {
    phase: CLAUDE_MODEL_MAIN
    for phase in ("1", "2C", "2G", "3A", "3D", "5A", "5G", "6A", "6B", "6C", "6D", "6E", "7")
}

AGENT_TIMEOUTS = {
    "gemini": 1800,
    "codex":  3600,
    "claude": 300,
}
