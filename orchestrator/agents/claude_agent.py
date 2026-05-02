import os
import anthropic
from orchestrator.config import CLAUDE_MODEL_MAIN
from orchestrator.errors import ConfigError

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ConfigError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it before running: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = anthropic.Anthropic()
    return _client


def call(
    prompt: str,
    system: str = "You are an expert research assistant helping with academic paper writing and analysis.",
    model: str = CLAUDE_MODEL_MAIN,
    max_tokens: int = 8192,
) -> str:
    """Call Claude API and return the text response."""
    client = _get_client()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def call_with_files(prompt: str, file_contents: dict[str, str], **kwargs) -> str:
    """Call Claude with multiple file contents embedded in the prompt."""
    file_block = "\n\n".join(
        f"=== {name} ===\n{content}" for name, content in file_contents.items()
    )
    full_prompt = f"{file_block}\n\n---\n\n{prompt}"
    return call(full_prompt, **kwargs)
