#!/usr/bin/env python3
"""
Regenerates modelfiles/Modelfile.git-supervisor from prompts/system_prompt.md.

The persona text is authored once, in prompts/system_prompt.md, and used by
both backends: this script wraps it into an Ollama Modelfile for the local
backend, while git_supervisor_cloud.py loads the same file directly and
passes it to the Claude API as the `system` parameter. Editing the
Modelfile's SYSTEM block by hand instead of editing the source and
re-running this script is how the two backends drift apart — don't do that.

Usage:
    python tools/build_modelfile.py
"""

import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "system_prompt.md"
MODELFILE_PATH = ROOT / "modelfiles" / "Modelfile.git-supervisor"

BASE_MODEL = "qwen3:14b"

HEADER = """# Purpose: Git Supervisor — GitHub research & implementation advisor
# Base model: {base_model}
# Generated: {date} — DO NOT EDIT THE SYSTEM BLOCK BY HAND.
#   Source of truth is prompts/system_prompt.md; run
#   `python tools/build_modelfile.py` after editing it to regenerate this file.
# Create: ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor

FROM {base_model}

SYSTEM \"\"\"
{system_prompt}
\"\"\"

# Thinking-mode preset (project default): reasoning about repo fit,
# maintenance signal, and license implications benefits from thinking mode.
# temp 0 is avoided here on purpose — it loops in thinking mode.
PARAMETER num_ctx 32768
PARAMETER temperature 0.6
PARAMETER top_p 0.95
PARAMETER top_k 20
"""


def main() -> None:
    if not PROMPT_PATH.exists():
        raise SystemExit(f"Missing {PROMPT_PATH} — nothing to build from.")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()

    content = HEADER.format(
        base_model=BASE_MODEL,
        date=datetime.date.today().isoformat(),
        system_prompt=system_prompt,
    )

    MODELFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODELFILE_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {MODELFILE_PATH}")


if __name__ == "__main__":
    main()
