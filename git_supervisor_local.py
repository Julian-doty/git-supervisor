#!/usr/bin/env python3
"""
Git Supervisor — local backend (Ollama / qwen3:14b, or whatever model you
created modelfiles/Modelfile.git-supervisor with).

Setup (once):
    ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
    export GITHUB_TOKEN=...          # or put it in a .env file

Usage:
    python git_supervisor_local.py "something to track habits in Python"
    python git_supervisor_local.py "topic:habit-tracker language:python" --raw
    python git_supervisor_local.py "self-hosted note app" --format ods --limit 10
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.backends.ollama_backend import DEFAULT_HOST, OllamaBackend
from core.pipeline import PipelineError, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Git Supervisor — local (Ollama) backend.")
    parser.add_argument("topic", help="What you're looking for, in plain language (or a raw GitHub search query with --raw).")
    parser.add_argument("--raw", action="store_true", help="Treat `topic` as a literal GitHub search query instead of asking the model to synthesize one.")
    parser.add_argument("--format", choices=["xlsx", "ods"], default="xlsx", help="Output spreadsheet format (default: xlsx).")
    parser.add_argument("--limit", type=int, default=15, help="Max repositories to analyze (default: 15).")
    parser.add_argument("--out-dir", type=Path, default=Path("./output"), help="Output directory (default: ./output).")
    parser.add_argument("--model", default="git-supervisor", help="Ollama model name (default: git-supervisor).")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Ollama host (default: {DEFAULT_HOST}).")
    parser.add_argument("--no-readme", action="store_true", help="Skip fetching README excerpts (faster, but the model has less to ground its analysis in).")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output on stderr.")
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN", "")

    backend = OllamaBackend(model=args.model, host=args.host)

    try:
        out_path = run(
            args.topic,
            backend,
            github_token,
            raw_query=args.raw,
            limit=args.limit,
            fmt=args.format,
            out_dir=args.out_dir,
            fetch_readmes=not args.no_readme,
            verbose=not args.quiet,
        )
    except PipelineError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(out_path)


if __name__ == "__main__":
    main()
