#!/usr/bin/env python3
"""
Git Supervisor — cloud backend (Claude API). For people without a local
model set up, at the cost of a real API bill per run — see the README for
what that looks like in practice.

Setup (once):
    pip install anthropic
    export ANTHROPIC_API_KEY=...     # or put it in a .env file
    export GITHUB_TOKEN=...

Usage:
    python git_supervisor_cloud.py "something to track habits in Python"
    python git_supervisor_cloud.py "topic:habit-tracker language:python" --raw
    python git_supervisor_cloud.py "self-hosted note app" --format ods --limit 10
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

from core.backends.claude_backend import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, ClaudeBackend
from core.pipeline import PipelineError, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Git Supervisor — cloud (Claude API) backend.")
    parser.add_argument("topic", help="What you're looking for, in plain language (or a raw GitHub search query with --raw).")
    parser.add_argument("--raw", action="store_true", help="Treat `topic` as a literal GitHub search query instead of asking the model to synthesize one.")
    parser.add_argument("--format", choices=["xlsx", "ods"], default="xlsx", help="Output spreadsheet format (default: xlsx).")
    parser.add_argument("--limit", type=int, default=15, help="Max repositories to analyze (default: 15). Directly affects API cost — see README.")
    parser.add_argument("--out-dir", type=Path, default=Path("./output"), help="Output directory (default: ./output).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model ID (default: {DEFAULT_MODEL}). Check https://docs.claude.com/en/docs/about-claude/models for current options.")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help=f"Max tokens per model response (default: {DEFAULT_MAX_TOKENS}).")
    parser.add_argument("--no-readme", action="store_true", help="Skip fetching README excerpts (faster, but the model has less to ground its analysis in).")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output on stderr.")
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    try:
        backend = ClaudeBackend(api_key=api_key, model=args.model, max_tokens=args.max_tokens)
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
    except (PipelineError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(out_path)


if __name__ == "__main__":
    main()
