"""
The actual orchestration: topic -> (optional) query synthesis -> GitHub
search -> README enrichment -> model analysis -> parsed rows -> spreadsheet.

Both entry scripts (git_supervisor_local.py, git_supervisor_cloud.py) call
run() with a Backend instance already constructed for their own model. This
module doesn't know or care whether that backend is Ollama or Claude —
that's the point of the Backend interface in core/backends/base.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .backends.base import Backend
from .github_search import GitHubAPIError, RepoResult, enrich_with_readmes, search_repositories
from .spreadsheet import write_spreadsheet

SEARCH_QUERY_RE = re.compile(
    r"---\s*START SEARCH QUERY\s*---\s*(.*?)\s*---\s*END SEARCH QUERY\s*---",
    re.DOTALL,
)

REPO_BLOCK_RE = re.compile(
    r"###\s*REPO:\s*(?P<full_name>\S+)\s*\n"
    r"RELEVANCE:\s*(?P<relevance>.*?)\s*\n"
    r"MAINTENANCE:\s*(?P<maintenance>.*?)\s*\n"
    r"IMPLEMENTATION:\s*(?P<implementation>.*?)\s*\n"
    r"VERDICT:\s*(?P<verdict>.*?)"
    r"(?=\n###\s*REPO:|\Z)",
    re.DOTALL,
)


class PipelineError(RuntimeError):
    pass


def synthesize_search_query(topic: str, backend: Backend) -> str:
    prompt = f"TASK: SEARCH_QUERY\n\nRough request: {topic}"
    response = backend.generate(prompt)
    match = SEARCH_QUERY_RE.search(response)
    if not match:
        raise PipelineError(
            f"Model response didn't contain the expected search-query markers. "
            f"Raw response:\n{response}"
        )
    return match.group(1).strip()


def _repo_metadata_block(index: int, repo: RepoResult) -> str:
    topics = ", ".join(repo.topics) if repo.topics else "(none)"
    excerpt = repo.readme_excerpt or "(no README excerpt available)"
    return (
        f"--- REPO {index} ---\n"
        f"Full name: {repo.full_name}\n"
        f"URL: {repo.url}\n"
        f"Description: {repo.description or '(none)'}\n"
        f"Stars: {repo.stars}\n"
        f"Forks: {repo.forks}\n"
        f"Language: {repo.language or '(unknown)'}\n"
        f"License: {repo.license_name or '(none)'}\n"
        f"Last pushed: {repo.pushed_at or '(unknown)'}\n"
        f"Open issues: {repo.open_issues}\n"
        f"Topics: {topics}\n"
        f"README excerpt:\n{excerpt}\n"
    )


def build_analysis_prompt(topic: str, repos: list[RepoResult]) -> str:
    blocks = "\n".join(_repo_metadata_block(i, r) for i, r in enumerate(repos, start=1))
    return (
        f"TASK: REPO_ANALYSIS\n\n"
        f"Topic: {topic}\n\n"
        f"Candidate repositories ({len(repos)} total):\n\n"
        f"{blocks}\n"
        f"Analyze all {len(repos)} repositories above using the REPO_ANALYSIS "
        f"format from your system prompt. Preserve this exact order."
    )


_FENCE_LINE_RE = re.compile(r"^\s*`{2,3}\w*\s*$")


def _clean_field(text: str) -> str:
    """
    Models sometimes wrap structured output in markdown code fences despite
    being told not to (imitating the fences used to illustrate the format
    in the system prompt). A stray ``` line sitting between one block's
    last field and the next block's "### REPO:" marker gets swallowed into
    that field by the regex below, since it has nowhere else to go. Strip
    any line that's purely a code-fence marker, and any leftover fence
    characters stuck to the start/end of the text, rather than trusting
    the model to never do this.
    """
    lines = [ln for ln in text.splitlines() if not _FENCE_LINE_RE.match(ln)]
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"`{2,3}\s*$", "", cleaned).strip()
    cleaned = re.sub(r"^\s*`{2,3}", "", cleaned).strip()
    return cleaned


def parse_analysis_response(response: str, repos: list[RepoResult]) -> list[dict]:
    by_name = {r.full_name: r for r in repos}
    rows = []
    seen = set()

    for match in REPO_BLOCK_RE.finditer(response):
        full_name = match.group("full_name").strip()
        repo = by_name.get(full_name)
        if repo is None:
            print(f"  warning: model referenced unknown repo '{full_name}', skipping", file=sys.stderr)
            continue
        seen.add(full_name)
        rows.append({
            "full_name": repo.full_name,
            "url": repo.url,
            "stars": repo.stars,
            "forks": repo.forks,
            "language": repo.language,
            "license_name": repo.license_name,
            "pushed_at": repo.pushed_at,
            "open_issues": repo.open_issues,
            "topics": repo.topics,
            "description": repo.description,
            "relevance": _clean_field(match.group("relevance")),
            "maintenance": _clean_field(match.group("maintenance")),
            "implementation": _clean_field(match.group("implementation")),
            "verdict": _clean_field(match.group("verdict")),
        })

    missing = [r.full_name for r in repos if r.full_name not in seen]
    if missing:
        print(f"  warning: model produced no analysis block for: {', '.join(missing)}", file=sys.stderr)
        for repo in repos:
            if repo.full_name in missing:
                rows.append({
                    "full_name": repo.full_name,
                    "url": repo.url,
                    "stars": repo.stars,
                    "forks": repo.forks,
                    "language": repo.language,
                    "license_name": repo.license_name,
                    "pushed_at": repo.pushed_at,
                    "open_issues": repo.open_issues,
                    "topics": repo.topics,
                    "description": repo.description,
                    "relevance": "(model produced no analysis for this repo)",
                    "maintenance": "",
                    "implementation": "",
                    "verdict": "",
                })

    return rows


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60] or "topic"


def run(topic: str, backend: Backend, github_token: str, *, raw_query: bool = False,
        limit: int = 15, fmt: str = "xlsx", out_dir: Path = Path("./output"),
        fetch_readmes: bool = True, verbose: bool = True) -> Path:
    if verbose:
        print(f"Backend: {backend.label}", file=sys.stderr)

    if raw_query:
        query = topic
    else:
        if verbose:
            print("Synthesizing GitHub search query from topic...", file=sys.stderr)
        query = synthesize_search_query(topic, backend)
    if verbose:
        print(f"Search query: {query}", file=sys.stderr)

    try:
        repos = search_repositories(query, github_token, limit=limit)
    except GitHubAPIError as e:
        raise PipelineError(str(e)) from e

    if not repos:
        raise PipelineError(f"No repositories found for query: {query}")

    if verbose:
        print(f"Found {len(repos)} repositories. Fetching README excerpts...", file=sys.stderr)
    if fetch_readmes:
        enrich_with_readmes(repos, github_token, verbose=verbose)

    if verbose:
        print("Requesting analysis from model...", file=sys.stderr)
    prompt = build_analysis_prompt(topic, repos)
    response = backend.generate(prompt)
    rows = parse_analysis_response(response, repos)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"git-supervisor_{slugify(topic)}.{fmt}"
    write_spreadsheet(rows, out_path, fmt)

    if verbose:
        print(f"Wrote {out_path}", file=sys.stderr)
    return out_path
