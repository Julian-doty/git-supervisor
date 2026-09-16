# Getting Started — Cloud Backend (Claude API)

Walkthrough for `git_supervisor_cloud.py`. This assumes you already have
the repo cloned/unzipped and a `.env` with `GITHUB_TOKEN` set — if not, do
that part of [GETTING_STARTED_LOCAL.md](GETTING_STARTED_LOCAL.md) first
(the "Get the repo" / venv / GitHub token steps are identical for both
backends; only the model backend itself differs).

Unlike the local backend, this one has no install-and-forget setup and no
`ollama create` step — there's nothing local to build. But it does bill
real money per run, so read the [cost](#cost) section before your first
call.

## Install (one time)

1. **Get an Anthropic API key.** This is a separate account from claude.ai
   — go to [console.anthropic.com](https://console.anthropic.com/settings/keys),
   sign in (or create an account), and generate a key. The console account
   needs billing set up (prepaid credits) since API usage is billed per
   token, not covered by a chat subscription.

2. **Add the key to your `.env`** (same file the local backend uses):
   ```bash
   cd ~/Downloads/git-supervisor      # Windows: cd $HOME\Downloads\git-supervisor
   source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
   nano .env                          # or notepad .env on Windows
   ```
   Add: `ANTHROPIC_API_KEY=sk-ant-...`

3. **Confirm the `anthropic` package is installed** — it's already in
   `requirements.txt`, so this just verifies your venv actually has it:
   ```bash
   python -c "import anthropic; print('ok')"
   ```

4. **Run a first test**, small on purpose:
   ```bash
   python git_supervisor_cloud.py "something to track habits in Python" --limit 3
   ```

Check `output/` for the resulting spreadsheet — identical format to the
local backend's output.

## After a restart

```bash
cd ~/Downloads/git-supervisor
source .venv/bin/activate
python git_supervisor_cloud.py "your topic here"
```

Nothing to rebuild or re-authenticate beyond that — the `.env` file with
your API key persists on disk, same as `GITHUB_TOKEN`.

## Cost

Every run makes real, billed API calls: one small call to synthesize the
search query (skipped entirely with `--raw`), and one larger call carrying
all `--limit` repos' metadata and README excerpts for analysis.

Current Claude Sonnet 5 pricing is $2 per million input tokens and $10 per
million output tokens (see
[platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)
for the current rate — pricing can change). At `--limit 3` that works out
to roughly a cent or less per run; it scales up with `--limit` and with
`--no-readme` turned off (README excerpts add input tokens per repo).

To keep costs predictable while testing:
- Start with a low `--limit` (3–5) until you trust the output.
- Use `--raw` once you know the GitHub search syntax you want — it skips
  the query-synthesis call entirely.
- Check real usage at [console.anthropic.com](https://console.anthropic.com)
  after a run rather than trusting an estimate.

## Switching between backends

Both scripts read the same `prompts/system_prompt.md`, write the same
spreadsheet schema, and accept the same flags (`--format`, `--limit`,
`--raw`, `--out-dir`, `--no-readme`). The only thing that changes is which
one you run and which API key it needs — there's no config to switch, no
state shared between them, and no reason you can't use both on the same
machine for different runs.
