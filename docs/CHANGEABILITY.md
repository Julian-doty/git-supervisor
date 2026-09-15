# Changeability — using a different model or a different runner

This repo was built around `qwen3:14b` served by Ollama, but two separate
design decisions were made specifically so that isn't a hard dependency:
the persona lives once in a plain text file instead of being welded to any
one tool, and every model-calling piece goes through one small interface
(`core/backends/base.py`) instead of being hardcoded into the pipeline.
This doc explains what that buys you, and exactly what to touch for the
two kinds of change people are likely to want.

These are two independent axes — you can change either without touching
the other:

- **The model** — which weights actually answer the questions (qwen3,
  DeepSeek, Llama, Mistral, whatever).
- **The runner** — which local app serves those weights and exposes them
  over HTTP (Ollama, LM Studio, vLLM, llama.cpp's server,
  text-generation-webui).

---

## 1. Changing the model, keeping Ollama

The easy case. Ollama's model library includes DeepSeek and most other
popular open models directly (`ollama pull deepseek-r1:14b`, for
instance), so nothing about how the harness talks to Ollama changes.

**Where to make the change:** `tools/build_modelfile.py`, not
`modelfiles/Modelfile.git-supervisor` directly — that file is generated,
and hand-editing it gets overwritten the next time someone runs the build
script.

1. Edit `BASE_MODEL` near the top of `tools/build_modelfile.py`:
   ```python
   BASE_MODEL = "deepseek-r1:14b"   # was "qwen3:14b"
   ```
2. Check whether the sampling parameters at the bottom of the `HEADER`
   template (`temperature`, `top_p`, `top_k`) still make sense. The
   current values are qwen3's documented "thinking mode" preset — a
   different model family usually publishes its own recommended sampling
   values, and they're often different enough to matter.
3. Pull the model and rebuild:
   ```bash
   ollama pull deepseek-r1:14b
   python tools/build_modelfile.py
   ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
   ```
4. **Retest before trusting it.** Run with `--limit 3` and actually read
   the spreadsheet, not just confirm the command exits cleanly.

That last step isn't boilerplate caution — it's exactly how the
[code-fence bug](GETTING_STARTED_LOCAL.md) got caught on the first real
run with qwen3. Every model has its own habits, and the only way to find
them is to run it and look. DeepSeek-R1 specifically is worth extra
attention here: its own documentation discourages relying on system
prompts the way this project's persona does, and it emits its own
`<think>...</think>` reasoning traces — Ollama's built-in template for it
handles that, but it's a real behavioral difference from qwen3, not a
guaranteed drop-in.

If a new model's output stops matching the expected block format (empty
Verdict columns, warnings in the terminal about "no analysis block for"),
the contract it's failing to meet lives in two places that have to agree
with each other:

- `prompts/system_prompt.md` — what format the model is told to produce
- `core/pipeline.py`, `REPO_BLOCK_RE` and `SEARCH_QUERY_RE` — what format
  the parser expects to receive

Loosening the parser's regex or tightening the prompt's instructions are
both legitimate fixes, depending on which side is actually wrong for that
model.

---

## 2. Changing the runner (LM Studio, vLLM, llama.cpp-server, etc.)

Also smaller than it sounds, because of one fact: LM Studio, vLLM,
llama.cpp's built-in server, text-generation-webui, and Ollama itself
(via its `/v1` endpoint, separate from the native one this repo currently
uses) all expose the same OpenAI-compatible `/v1/chat/completions` API.
One backend class covers all of them — they only differ in `base_url` and
model name.

**Where to make the change:** add a file, don't modify existing ones.
`core/github_search.py`, `core/spreadsheet.py`, `core/pipeline.py`, and
`prompts/system_prompt.md` don't know or care which backend is running —
none of them need to change.

### Step 1 — a new backend class

`core/backends/openai_compatible_backend.py`, implementing the same
`Backend` interface as `ollama_backend.py` and `claude_backend.py`. This
is a sketch to adapt and test, not a finished/verified file:

```python
"""
Generic backend for any local runner that speaks the OpenAI-compatible
chat completions API: LM Studio, vLLM, llama.cpp's server,
text-generation-webui, or Ollama's own /v1 endpoint.
"""

from __future__ import annotations

from pathlib import Path

import requests

from .base import Backend

ROOT = Path(__file__).resolve().parent.parent.parent
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system_prompt.md"


class OpenAICompatibleBackend(Backend):
    def __init__(self, base_url: str, model: str, api_key: str = "not-needed",
                 temperature: float = 0.6,
                 system_prompt_path: Path = SYSTEM_PROMPT_PATH):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.system_prompt = system_prompt_path.read_text(encoding="utf-8").strip()

    @property
    def label(self) -> str:
        return f"openai-compatible:{self.model}@{self.base_url}"

    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=600,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
```

No new dependency needed — `requests` is already in `requirements.txt`.

### Step 2 — a thin entry script

`git_supervisor_openai.py`, mirroring `git_supervisor_cloud.py`'s
structure: parse `--base-url` and `--model` flags, construct
`OpenAICompatibleBackend`, call `core.pipeline.run(...)` exactly like the
other two scripts do. No Modelfile involved — LM Studio and the other
OpenAI-compatible runners load GGUF files through their own UI or config,
they don't use Ollama's Modelfile concept at all.

### Step 3 — point it at LM Studio specifically

1. In LM Studio, load whichever model you want (its own model browser,
   or a GGUF you downloaded separately).
2. Enable the local server (LM Studio's "Local Server" tab), default port
   1234.
3. Run with `--base-url http://localhost:1234/v1 --model <whatever LM
   Studio reports as the model's identifier>`.

Known unknown: not every OpenAI-compatible server implements every
parameter identically — some are stricter about `temperature` bounds,
some report `finish_reason` differently, some don't support every
sampling knob this project might eventually want to use. Same rule as
changing the model: run it, read the actual output, don't assume
compatibility because the endpoint shape matches.

---

## Quick reference

| Change | Files to touch | New code? |
|---|---|---|
| Different model, same Ollama | `tools/build_modelfile.py` | No — regenerate + `ollama create` |
| Different sampling only | `tools/build_modelfile.py` | No |
| New local runner (OpenAI-compatible) | new `core/backends/*.py` + new entry script | Yes — one backend class, one thin CLI script |
| A model's output stops matching the parser | `prompts/system_prompt.md` and/or `core/pipeline.py`'s regexes | Maybe, only if parsing actually breaks |

## What never needs to change

`core/github_search.py`, `core/spreadsheet.py`, `core/pipeline.py`'s
orchestration logic, and the spreadsheet column schema. The GitHub API
calls and file-writing are deterministic and don't know a model exists.

## Honest difficulty summary

- Swapping the model on Ollama: trivial, minutes of work, plus however
  long it takes you to actually read the output and confirm it's sane.
- Adding a new OpenAI-compatible runner: small, a few hours, and most of
  that time goes to testing against whatever you actually loaded, not
  writing code.
- The real bottleneck in both cases isn't code — it's that every model
  has its own habits, and the only way to find them is to run it and
  read what comes back, the same way the code-fence bug in the current
  setup was actually found.
