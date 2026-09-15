# Git Supervisor

Give it a topic — "something to track habits in Python," or a raw GitHub
search query if you already know what you want — and it searches GitHub for
real repositories, has a model judge each one's actual fit and maintenance
health (not just star count), and writes the results into a spreadsheet you
can open in Excel or LibreOffice Calc.

Two ways to run it:

- **`git_supervisor_local.py`** — uses a local [Ollama](https://ollama.com)
  model (built for `qwen3:14b`, the persona should port to other models with
  no changes needed). Free to run, needs a decent local GPU/VRAM budget.
- **`git_supervisor_cloud.py`** — uses the [Claude API](https://docs.claude.com)
  instead. No local model required, but costs real money per run (see
  [Cost](#cost-cloud-backend) below).

Both produce identical output. Pick whichever fits your setup.

## Why not just have the model search and write the file itself?

It can't. A model — local or cloud — only generates text; it has no way to
call the GitHub API or produce a binary spreadsheet file on its own. This
tool is a small Python harness that does the actual API calls and file
writing deterministically, and only hands the model the specific judgement
calls that need reasoning: turning a rough topic into a search query, and
explaining why each result is (or isn't) a good fit. Every number in the
output spreadsheet — stars, license, last-push date — comes straight from
GitHub's API, never from the model, so it can't be misremembered or
invented.

## How it works

```
topic ("habit tracker in python")
  │
  ├─ (unless --raw) model converts it to a GitHub search query
  │
  ▼
GitHub Search API  →  candidate repos (real metadata: stars, license,
  │                    last push, open issues, topics)
  ▼
GitHub Contents API →  README excerpt per candidate (grounds the model's
  │                    analysis in the repo's actual description of itself)
  ▼
model judges each repo: relevance, maintenance signal, implementation
notes, verdict — using ONLY the metadata/README it was given, never
inventing facts
  │
  ▼
spreadsheet (.xlsx or .ods)
```

## Setup

For the local (Ollama) backend, a full step-by-step walkthrough — install
through first run, and what to do after a restart — is in
[docs/GETTING_STARTED_LOCAL.md](docs/GETTING_STARTED_LOCAL.md), covering
Linux, macOS, and Windows. Short version:

```bash
git clone <this repo>
cd git-supervisor
python3 -m venv .venv && source .venv/bin/activate   # Windows: python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# edit .env — fill in GITHUB_TOKEN, and ANTHROPIC_API_KEY if using the cloud backend
```

`GITHUB_TOKEN` is required for both backends — create one at
[github.com/settings/tokens](https://github.com/settings/tokens) (no special
scopes needed, it's only used for public repo/README reads). Unauthenticated
search is limited to 10 requests/minute, which this tool will burn through
fast between the search call and one README fetch per result.

### Local backend

Requires [Ollama](https://ollama.com) installed and running. See
[docs/GETTING_STARTED_LOCAL.md](docs/GETTING_STARTED_LOCAL.md) for the full
walkthrough per OS.

```bash
ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
python git_supervisor_local.py "something to track habits in Python"
```

### Cloud backend

No local model to build, but it bills real money per run — see
[docs/GETTING_STARTED_CLOUD.md](docs/GETTING_STARTED_CLOUD.md) for the full
walkthrough including current pricing and how to keep costs predictable
while testing.

```bash
pip install anthropic   # already in requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python git_supervisor_cloud.py "something to track habits in Python"
```

## Usage

```bash
# Natural-language topic — the model writes the GitHub search query itself
python git_supervisor_local.py "lightweight self-hosted note-taking app"

# You already know the exact GitHub search syntax you want
python git_supervisor_local.py "topic:note-taking language:python stars:>500" --raw

# LibreOffice Calc output, fewer results
python git_supervisor_local.py "cli habit tracker" --format ods --limit 8

# Skip README fetching (faster, less-grounded analysis)
python git_supervisor_cloud.py "self-hosted analytics" --no-readme
```

Run either script with `--help` for the full flag list.

## Output

One row per repository:

| Column | Source |
|---|---|
| Repo, URL, Stars, Forks, Language, License, Last Updated, Open Issues, Topics, Description | GitHub API (deterministic — never touched by the model) |
| Relevance | Model — why it does or doesn't fit the topic |
| Maintenance Read | Model — activity/staleness read from push date + issue count |
| Implementation | Model — concrete next steps, grounded in the README excerpt it was given; marked as inferred where it wasn't |
| Verdict | Model — Strong / Moderate / Weak / Skip |

## Cost (cloud backend)

Every run of `git_supervisor_cloud.py` makes real, billed API calls: one
small call to synthesize the search query (skipped with `--raw`), and one
larger call carrying all `--limit` repos' metadata and README excerpts for
analysis. Lower `--limit` and use `--no-readme` to cut cost per run if
you're experimenting. The local backend has no per-run cost beyond your own
electricity.

## Project layout

```
modelfiles/Modelfile.git-supervisor   Ollama model definition (generated — see below)
prompts/system_prompt.md              The persona, single source of truth for both backends
tools/build_modelfile.py              Regenerates the Modelfile from the prompt above
core/github_search.py                 Deterministic GitHub API calls
core/spreadsheet.py                   .xlsx / .ods writer
core/pipeline.py                      Orchestration shared by both entry scripts
core/backends/                        Backend interface + Ollama and Claude implementations
git_supervisor_local.py               CLI entry point — Ollama backend
git_supervisor_cloud.py               CLI entry point — Claude backend
docs/PLATFORM_NOTES.md                Windows / macOS setup notes (untested — see file)
```

The persona is written once, in `prompts/system_prompt.md`. If you edit it,
regenerate the Modelfile with:

```bash
python tools/build_modelfile.py
ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
```

The cloud backend reads `prompts/system_prompt.md` directly at runtime — no
regeneration step needed on that side.

## Using a different model or runner

Built around `qwen3:14b` on Ollama, but not locked to either. Swapping in
a different model (e.g. DeepSeek) while staying on Ollama is a one-line
config change; adding support for a different local runner (LM Studio,
vLLM, llama.cpp-server) means writing one small backend class, with
nothing else in the repo needing to change. See
[docs/CHANGEABILITY.md](docs/CHANGEABILITY.md) for exactly what to touch
and where, plus the honest difficulty/caveats for each.

## Platform support

Developed and tested on Linux (Linux Mint, Ollama installed natively).
Windows and macOS should work — the code is plain cross-platform Python —
but neither has actually been run yet. See
[docs/PLATFORM_NOTES.md](docs/PLATFORM_NOTES.md) before assuming it just
works there, and please open an issue with your results either way.

## License

[MIT](LICENSE).
