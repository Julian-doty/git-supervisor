# Platform notes

The Modelfile and all the Python in this repo are plain, cross-platform code
— nothing here is Linux-specific by design. But only Linux has actually been
run and verified. Windows and macOS notes below are written carefully, not
tested. **If you run this on Windows or macOS, please open an issue saying
what worked and what didn't** — that's how those get upgraded from "should
work" to "confirmed."

## Linux (tested — primary development platform)

Developed and run on Linux Mint 22.3 (Cinnamon), Python 3.x, Ollama
installed natively (not Docker).

```bash
export GITHUB_TOKEN=ghp_xxx
export ANTHROPIC_API_KEY=sk-ant-xxx   # only needed for the cloud backend
```

Add those to `~/.bashrc` (or `~/.zshrc` on a zsh setup) to persist them
across sessions, or use a `.env` file in the repo root (copy
`.env.example` to `.env`) — both entry scripts load it automatically if
`python-dotenv` is installed.

## Windows 11 (untested)

Python 3.14, PowerShell.

```powershell
setx GITHUB_TOKEN "ghp_xxx"
setx ANTHROPIC_API_KEY "sk-ant-xxx"
```

`setx` persists the variable for future terminal sessions but **not** the
one you just ran it in — close and reopen PowerShell, or just use a `.env`
file instead (simpler, and what's recommended here): copy `.env.example` to
`.env` in the repo root and fill it in; `python-dotenv` picks it up
automatically.

For the local backend, install Ollama for Windows from
[ollama.com/download](https://ollama.com/download) and confirm `ollama
list` works in a terminal before running `git_supervisor_local.py`.

Expected friction points nobody has verified yet: whether `pip install -r
requirements.txt` needs anything extra for `odfpy`/`openpyxl` on a fresh
Windows Python install, and whether file paths in `--out-dir` behave with
backslashes vs the forward slashes used in this repo's docs (Python's
`pathlib`, which this code uses throughout, should handle that
transparently — but "should" is exactly what needs confirming).

## macOS (untested)

Expected to work the same as Linux — same shell conventions
(`~/.zshrc` is the default shell config on modern macOS), same `export`
syntax, Ollama has a native macOS build. No known differences, but none of
this has been run on a Mac.

## Reporting platform results

If you try this on Windows or macOS, opening a short issue with the OS
version, Python version, and what happened (worked cleanly / hit an error —
paste it) is genuinely useful. This file gets updated from real reports,
not assumptions.
