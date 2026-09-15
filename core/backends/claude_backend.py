"""
Cloud backend — talks to the Claude API. Unlike Ollama, Claude has no
Modelfile-equivalent artifact: the persona is loaded straight from
prompts/system_prompt.md at construction and sent as the `system` parameter
on every call. Same underlying persona text as the Ollama Modelfile, kept
in sync because both read from the one source file (see
tools/build_modelfile.py for how the Modelfile side stays in sync).

Requires: pip install anthropic, and ANTHROPIC_API_KEY set in the
environment. Every call costs money — see the README for how to keep that
predictable (small --limit, cache nothing repeatedly).
"""

from __future__ import annotations

from pathlib import Path

from .base import Backend

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_MAX_TOKENS = 4096

ROOT = Path(__file__).resolve().parent.parent.parent
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system_prompt.md"


class ClaudeBackend(Backend):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL,
                 temperature: float = 0.6, max_tokens: int = DEFAULT_MAX_TOKENS,
                 system_prompt_path: Path = SYSTEM_PROMPT_PATH):
        if not api_key:
            raise RuntimeError(
                "No Anthropic API key provided. Set ANTHROPIC_API_KEY in "
                "your environment (see .env.example)."
            )
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "The 'anthropic' package isn't installed. Run: "
                "pip install anthropic"
            ) from e

        if not system_prompt_path.exists():
            raise RuntimeError(f"Missing persona file: {system_prompt_path}")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt_path.read_text(encoding="utf-8").strip()
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def label(self) -> str:
        return f"claude:{self.model}"

    def generate(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "\n".join(parts).strip()
