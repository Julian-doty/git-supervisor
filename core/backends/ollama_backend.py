"""
Local backend — talks to a running Ollama instance. The persona is baked
into the model at `ollama create` time from modelfiles/Modelfile.git-supervisor,
so this class sends nothing but the task prompt; it never sends a system
prompt itself. Same stateless, single-shot call pattern as council.py's
call_model — no chat history, one request per task.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import Backend

DEFAULT_HOST = "http://localhost:11434"


class OllamaBackend(Backend):
    def __init__(self, model: str = "git-supervisor", host: str = DEFAULT_HOST,
                 temperature: float | None = None):
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = temperature

    @property
    def label(self) -> str:
        return f"ollama:{self.model}"

    def generate(self, prompt: str) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if self.temperature is not None:
            payload["options"] = {"temperature": self.temperature}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.host}. Is it running, and "
                f"has `ollama create {self.model} -f "
                f"modelfiles/Modelfile.git-supervisor` been run? ({e})"
            ) from e

        if "error" in body:
            raise RuntimeError(
                f"Ollama returned an error for model '{self.model}': {body['error']}. "
                f"If this says the model doesn't exist, run: "
                f"ollama create {self.model} -f modelfiles/Modelfile.git-supervisor"
            )

        return body.get("response", "").strip()
