# Getting Started — Local AI Backend (Ollama)

Full install walkthrough for `git_supervisor_local.py` on Linux, macOS, and
Windows, plus what to do each time you come back to it after a restart.
Looking for the Claude API backend instead? See
[GETTING_STARTED_CLOUD.md](GETTING_STARTED_CLOUD.md).

**Linux is the only platform this has actually been run on and confirmed
working.** macOS and Windows steps below are written carefully from how
those tools normally behave, but neither has been verified end-to-end —
see the note at the top of each section. If you try one and it works (or
doesn't), an issue on the repo with what happened is genuinely useful; see
[PLATFORM_NOTES.md](PLATFORM_NOTES.md).

Each section has two parts: **Install** (do once) and **After a restart**
(do every time you come back to a fresh terminal).

---

## Linux (verified)

### Install (one time)

1. **Install Ollama**, if you haven't already:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull the base model:**
   ```bash
   ollama pull qwen3:14b
   ```

3. **Get the repo** onto this machine and move into it:
   ```bash
   cd ~/Downloads
   unzip git-supervisor.zip
   cd git-supervisor
   ```

4. **Create a virtual environment.** If this errors saying `ensurepip is
   not available`, install the venv package it names (e.g. `sudo apt
   install python3.12-venv`) and retry:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. **Install Python dependencies** (you should see `(.venv)` at the start
   of your prompt — that confirms the venv is active first):
   ```bash
   pip install -r requirements.txt
   ```

6. **Set up your GitHub token.** Create one with no special scopes at
   [github.com/settings/tokens](https://github.com/settings/tokens) — it's
   only used to lift the search API rate limit.
   ```bash
   cp .env.example .env
   nano .env   # paste your token as GITHUB_TOKEN=ghp_...
   ```

7. **Build the git-supervisor model:**
   ```bash
   ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
   ollama list   # confirm git-supervisor shows up
   ```

8. **Run a first test**, small on purpose:
   ```bash
   python git_supervisor_local.py "something to track habits in Python" --limit 3
   ```
   Check `output/` for the resulting spreadsheet.

### After a restart

Ollama runs as a systemd service and normally comes back on its own after
a reboot — everything below is what a fresh terminal needs, not a rebuild.

```bash
cd ~/Downloads/git-supervisor
source .venv/bin/activate
ollama list          # confirms Ollama is actually up; if this hangs, run:
                      #   sudo systemctl start ollama
python git_supervisor_local.py "your topic here"
```

Nothing else needs redoing — the venv, installed packages, `.env` file, and
`git-supervisor` Ollama model all persist on disk across restarts.

---

## macOS (untested)

### Install (one time)

1. **Install Ollama** — either the macOS app from
   [ollama.com/download](https://ollama.com/download) (adds a menu-bar
   icon, launches on login), or via Homebrew:
   ```bash
   brew install ollama
   brew services start ollama
   ```

2. **Pull the base model:**
   ```bash
   ollama pull qwen3:14b
   ```

3. **Get the repo:**
   ```bash
   cd ~/Downloads
   unzip git-supervisor.zip
   cd git-supervisor
   ```

4. **Create a virtual environment.** macOS's built-in `python3` normally
   includes `venv` already (no separate package needed, unlike Debian/
   Ubuntu). If `python3` isn't found at all, install it via
   `brew install python` or from python.org first.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Set up your GitHub token** (same as Linux):
   ```bash
   cp .env.example .env
   nano .env   # or `open -e .env` for TextEdit
   ```

7. **Build the model:**
   ```bash
   ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
   ollama list
   ```

8. **First test:**
   ```bash
   python git_supervisor_local.py "something to track habits in Python" --limit 3
   ```

### After a restart

```bash
cd ~/Downloads/git-supervisor
source .venv/bin/activate
ollama list          # if this fails, either reopen the Ollama app, or:
                      #   brew services start ollama
python git_supervisor_local.py "your topic here"
```

Unverified specifically: whether the Ollama app auto-launches on login the
same way it does on Linux's systemd service, or whether you'll need to
reopen it manually each time. Report back if you find out either way.

---

## Windows 11 (untested)

Commands below are PowerShell.

### Install (one time)

1. **Install Ollama for Windows** from
   [ollama.com/download](https://ollama.com/download) and run the
   installer. It installs as a background app (system tray icon).

2. **Pull the base model:**
   ```powershell
   ollama pull qwen3:14b
   ```

3. **Get the repo** and move into it:
   ```powershell
   cd $HOME\Downloads
   Expand-Archive git-supervisor.zip
   cd git-supervisor
   ```

4. **Create a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell refuses to run the activation script with a message about
   execution policy, that's a security default, not an error in this
   project — you can allow scripts for just this terminal session with:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

5. **Install dependencies** (confirm `(.venv)` appears in your prompt
   first):
   ```powershell
   pip install -r requirements.txt
   ```

6. **Set up your GitHub token:**
   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

7. **Build the model:**
   ```powershell
   ollama create git-supervisor -f modelfiles/Modelfile.git-supervisor
   ollama list
   ```

8. **First test:**
   ```powershell
   python git_supervisor_local.py "something to track habits in Python" --limit 3
   ```

### After a restart

```powershell
cd $HOME\Downloads\git-supervisor
.venv\Scripts\Activate.ps1
ollama list          # if this fails, open Ollama from the Start menu
python git_supervisor_local.py "your topic here"
```

Unverified specifically: whether the Windows Ollama app auto-starts on
boot by default, and whether `Expand-Archive` handles the zip cleanly
(vs. right-click → Extract All, which definitely works). Report back if
you hit either.

---

## Quick reference — every restart, once installed

| Step | Linux / macOS | Windows (PowerShell) |
|---|---|---|
| Move into the repo | `cd ~/Downloads/git-supervisor` | `cd $HOME\Downloads\git-supervisor` |
| Activate the venv | `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` |
| Confirm Ollama is up | `ollama list` | `ollama list` |
| Run it | `python git_supervisor_local.py "topic"` | `python git_supervisor_local.py "topic"` |
