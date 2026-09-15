"""
Deterministic GitHub API access. No model involved here — everything this
module returns is a direct, verifiable fact from GitHub, which is what lets
the model's later judgement stay grounded instead of guessing at stats.

Search API docs: https://docs.github.com/en/rest/search/search
"""

from __future__ import annotations

import base64
import dataclasses
import sys
import time
from typing import Optional

import requests

API_ROOT = "https://api.github.com"
USER_AGENT = "git-supervisor (+https://github.com/)"


class GitHubAPIError(RuntimeError):
    """Raised for any non-recoverable GitHub API failure."""


@dataclasses.dataclass
class RepoResult:
    full_name: str          # "owner/name"
    owner: str
    name: str
    url: str
    description: str
    stars: int
    forks: int
    language: Optional[str]
    license_name: Optional[str]
    pushed_at: str           # ISO 8601 date of last push
    open_issues: int
    topics: list[str]
    readme_excerpt: Optional[str] = None


def _headers(token: str) -> dict:
    if not token:
        raise GitHubAPIError(
            "No GitHub token provided. Set GITHUB_TOKEN in your environment "
            "(see .env.example) — unauthenticated search is heavily rate "
            "limited and this tool needs a token to work reliably."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }


def _request(url: str, token: str, params: Optional[dict] = None,
             extra_headers: Optional[dict] = None) -> requests.Response:
    headers = _headers(token)
    if extra_headers:
        headers.update(extra_headers)

    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        reset = resp.headers.get("X-RateLimit-Reset")
        wait_hint = ""
        if reset:
            wait_s = max(0, int(reset) - int(time.time()))
            wait_hint = f" Resets in ~{wait_s // 60}m {wait_s % 60}s."
        raise GitHubAPIError(f"GitHub rate limit exceeded.{wait_hint}")

    if resp.status_code == 422:
        raise GitHubAPIError(
            f"GitHub rejected the search query as invalid: {url}?{params}. "
            f"Response: {resp.text[:300]}"
        )

    if not resp.ok:
        raise GitHubAPIError(
            f"GitHub API request failed ({resp.status_code}): {resp.text[:300]}"
        )

    return resp


def search_repositories(query: str, token: str, limit: int = 15,
                         sort: str = "stars", order: str = "desc") -> list[RepoResult]:
    """
    Runs GET /search/repositories and returns up to `limit` results as
    RepoResult objects. Does not fetch README excerpts — call
    fetch_readme_excerpt separately for the shortlist you actually intend
    to send to the model, to keep this cheap for exploratory queries.
    """
    if not query or not query.strip():
        raise GitHubAPIError("Empty search query.")

    per_page = min(max(limit, 1), 100)
    resp = _request(
        f"{API_ROOT}/search/repositories",
        token,
        params={"q": query, "sort": sort, "order": order, "per_page": per_page},
    )
    data = resp.json()
    items = data.get("items", [])[:limit]

    results = []
    for item in items:
        license_info = item.get("license") or {}
        results.append(RepoResult(
            full_name=item["full_name"],
            owner=item["owner"]["login"],
            name=item["name"],
            url=item["html_url"],
            description=item.get("description") or "",
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            language=item.get("language"),
            license_name=license_info.get("spdx_id") or license_info.get("name"),
            pushed_at=item.get("pushed_at", ""),
            open_issues=item.get("open_issues_count", 0),
            topics=item.get("topics", []) or [],
        ))
    return results


def fetch_readme_excerpt(owner: str, name: str, token: str,
                          max_chars: int = 1200) -> Optional[str]:
    """
    Fetches the repo's README (raw text) and returns the first `max_chars`
    characters. Returns None if the repo has no README or the fetch fails —
    callers should treat that as "no evidence available", not as an error;
    the system prompt tells the model to say so rather than pad over it.
    """
    try:
        resp = _request(
            f"{API_ROOT}/repos/{owner}/{name}/readme",
            token,
            extra_headers={"Accept": "application/vnd.github.raw"},
        )
    except GitHubAPIError:
        return None

    text = resp.text
    if not text:
        return None

    # Fallback in case the raw media type wasn't honored and we got JSON
    # with base64-encoded content instead.
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            payload = resp.json()
            content = payload.get("content", "")
            text = base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return None

    return text[:max_chars].strip() or None


def enrich_with_readmes(repos: list[RepoResult], token: str,
                         max_chars: int = 1200, verbose: bool = True) -> None:
    """Mutates each RepoResult in place, adding its readme_excerpt."""
    for repo in repos:
        if verbose:
            print(f"  fetching README: {repo.full_name}", file=sys.stderr)
        repo.readme_excerpt = fetch_readme_excerpt(repo.owner, repo.name, token, max_chars)
