---
name: browser-install
description: Install and bootstrap browser-harness into the current agent, then connect it to the user's real Chrome with minimal prompting.
---

# `browser-harness` installation

Use this file only for first-time browser-harness install, first time browser connection, browser reconnection, browser connection troubleshooting, or cold-start browser bootstrap. For day-to-day browser work, read `SKILL.md`. Task-specific edits belong in `agent-workspace/agent_helpers.py` and `agent-workspace/domain-skills/`.

## Install prompt contract

When you open a setup or verification tab, activate it so the user can actually see the active browser tab.

## Best browser-harness setup

Clone the repo once into a durable location, then install it as an editable tool so `browser-harness` works from any directory:

```bash
git clone https://github.com/browser-use/browser-harness
cd browser-harness
uv tool install -e .
command -v browser-harness
```

That keeps the command global while still pointing at the real repo checkout, so when the agent edits `agent-workspace/agent_helpers.py` the next `browser-harness` uses the new code immediately. Prefer a stable path like `~/Developer/browser-harness`, not `/tmp`.

## Make browser-harness global for the current agent

After the repo is installed, register this repo's `SKILL.md` with the agent you are using:

- **Codex**: add this file as a global skill at `$CODEX_HOME/skills/browser-harness/SKILL.md` (often `~/.codex/skills/browser-harness/SKILL.md`). A symlink to this repo's `SKILL.md` is fine.
```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/browser-harness" && ln -sf "$PWD/SKILL.md" "${CODEX_HOME:-$HOME/.codex}/skills/browser-harness/SKILL.md"
```
- **Claude Code**: add an import to `~/.claude/CLAUDE.md` that points at this repo's `SKILL.md`, for example `@~/src/browser-harness/SKILL.md`.

This makes new Codex or Claude Code sessions in other folders load the runtime browser harness instructions automatically. An empty `~/.codex/skills/browser-harness/` directory is fine; the symlink command above populates it.


# Browser connection setup and troubleshooting

## Browser connection reference

This section is the source of truth for how browser-harness connects to a browser. It is the canonical reference for every agent and user of this repo. Every statement here is intended to be verifiable against either an official Chrome source or this repo's own code, and is held to that standard deliberately. If anything below is incorrect, incomplete, or misleading, open an issue on the browser-harness repository immediately with clear evidence and explanation so it can be corrected. Do not silently work around an error in this document; the cost of one user being misled is much higher than the cost of one issue.

Browser-harness can connect to any Chrome, Chromium, or Edge browser on your computer, or to a Browser Use cloud browser.

**Cloud browsers** are managed by the Browser Use cloud API. Start one in Python with `start_remote_daemon("work", ...)`. Authentication is via the `BROWSER_USE_API_KEY` environment variable; the harness handles the WebSocket URL itself. To carry your local Chrome cookies into a cloud browser, install `profile-use` once (`curl -fsSL https://browser-use.com/profile.sh | sh`), then call `uuid = sync_local_profile("MyChromeProfile")` followed by `start_remote_daemon("work", profileId=uuid)`. Cookies are the only thing synced — not localStorage, not extensions, not history.

**Local browsers** require remote debugging to be enabled. There are two ways, and they suit different use cases.

*Way 1: chrome://inspect checkbox — uses your real profile.* In your running Chrome, navigate to `chrome://inspect/#remote-debugging` and tick the "Allow remote debugging for this browser instance" checkbox. This setting is per-profile and sticky: tick it once and it persists across every future Chrome launch of that profile. Then run any `browser-harness` command (`browser-harness --setup` is a guided first-run that auto-opens the inspect page if needed). On Chrome 144 and later, the first attach by the harness triggers an in-browser "Allow remote debugging?" popup that you must click Allow on. The popup may reappear on later attaches under conditions that are not fully characterized.[^1] This path inherits your everyday Chrome's logins, extensions, history, and bookmarks, which makes it the right choice for an agent helping you with tasks in your real browser.

*Way 2: command-line flag — uses an isolated profile, no popups ever.* Launch Chrome with `--remote-debugging-port=9222 --user-data-dir=<path>`. Two precisions:

- The path must be a directory that is **not** Chrome's platform default (`%LOCALAPPDATA%\Google\Chrome\User Data` on Windows, `~/Library/Application Support/Google/Chrome` on macOS, `~/.config/google-chrome` on Linux). On Chrome 136 and later, the port flag is silently no-opped when the user-data-dir is the platform default, even if you pass it explicitly. An empty or new path gives a fresh clean profile that Chrome will persist there across future runs.
- This path does **not** let you reuse your everyday Chrome profile. Copying the default profile's files into a custom directory makes Chrome accept the flag, but cookies are encrypted under a key bound to the original directory and will not survive the copy — so you carry over bookmarks and extensions but lose every logged-in session. If you want your real logins, use Way 1.

Tell the harness which port you launched on by setting `BU_CDP_URL=http://127.0.0.1:9222` before running `browser-harness`. No popups, no per-attach permission, no reprompts.

For most tasks where the agent acts on your behalf in your normal browser, use Way 1. For automation that runs without you watching, or any case where popup interruptions are unacceptable, use Way 2 or a cloud browser.

[^1]: The conditions that cause Chrome to re-show the "Allow remote debugging?" popup on a subsequent attach (time elapsed since previous Allow, daemon restart, browser restart, new CDP session, version-dependent options like "Allow for N hours") are not fully characterized. Way 2 sidesteps this entirely.

## First time setup

2. First try the harness directly. If this works, skip manual browser setup:

```bash
uv run browser-harness -c 'print(page_info())'
```

   Reuse an existing healthy daemon if it is already responding. Do not kill it during setup unless the attach is clearly stale and you are confident no other agent is using the same `BU_NAME`. For parallel agents, use distinct `BU_NAME`s so they do not fight over the same default session.

3. If it failed, **read the error and escalate from there — do not assume you need `chrome://inspect`**. The remote-debugging checkbox is per-profile sticky in Chrome, so any profile that has had it toggled on once will auto-enable CDP on every future launch; the inspect page is only needed the first time per profile.

   - **No Chrome process running** → just start Chrome and re-run the harness. On macOS: `open -a "Google Chrome"`. Do *not* navigate to `chrome://inspect` yet — if the user has ever ticked the checkbox on this profile, the harness will attach on its own.
   - **`DevToolsActivePort` missing or empty after Chrome is up** → remote-debugging has never been enabled on this profile. *This* is when you open `chrome://inspect/#remote-debugging` and ask the user to tick the checkbox and click `Allow`. Once ticked, the setting sticks.
   - **Port present but `connection refused` / `DevTools not live yet` / `/json/version` 404** → Chrome is mid-startup. Just keep polling for up to 30 seconds; do not restart Chrome and do not open the inspect page.
   - **`no close frame received or sent` / stale websocket** → the daemon (not Chrome) is the problem. Run `restart_daemon()` once and retry — see step 7 below.

   When you do need to open the inspect page on macOS and Chrome is already running, prefer AppleScript so it reuses the current profile instead of going through the picker:

```bash
osascript -e 'tell application "Google Chrome" to activate' \
          -e 'tell application "Google Chrome" to open location "chrome://inspect/#remote-debugging"'
```

   On Linux: open that URL manually in the existing Chrome window.
   If Chrome shows the profile picker first, tell the user to choose their normal profile, *then* (only if `DevToolsActivePort` is still missing) open the inspect page in that profile. Keep polling instead of waiting for the user to type a follow-up.
4. Be explicit with the user about the two possible Chrome actions: choose their normal profile if the profile picker is open, and in the remote-debugging tab tick the checkbox and click `Allow` once if Chrome shows it.
5. Try to do everything yourself. Only ask the user to do something if it is truly necessary, like selecting the Chrome profile or clicking `Allow`. While the user is doing that, sleep and check every 3 seconds whether it is completed. After asking, keep retrying for at least 30 seconds even if you see connection-refused, stale websocket, or other weird transient attach errors.
6. If setup still lands on the profile picker, have the user choose their normal profile, then (only if `DevToolsActivePort` is still missing) open `chrome://inspect/#remote-debugging` in that profile and keep polling instead of restarting the explanation. As soon as attach succeeds, continue immediately with the verification task without asking again.
7. Verify with:

```bash
uv run browser-harness -c "$(cat <<'PY'
goto_url("https://github.com/browser-use/browser-harness")
wait_for_load()
print(page_info())
PY
)"
```

If that fails with a stale websocket or stale socket, restart the daemon once and retry:

```bash
uv run python - <<'PY'
from browser_harness.admin import restart_daemon
restart_daemon()
PY
```

If restart_daemon() also hangs, kill Chrome entirely, clean sockets, and reopen:

```bash
pkill -9 -f "Google Chrome"
rm -f /tmp/bu-default.sock /tmp/bu-default.pid
open -a "Google Chrome"
```

Wait 5 seconds, then reconnect. This resets all CDP state.

If you are testing browser connection for the first time, run this demo: navigate to `https://github.com/browser-use/browser-harness` so the user can see the harness has attached. If they are logged into GitHub, ask whether to star the repo for them — only click if they say yes. Then ask what they want to do next.

## Maintenance commands

- browser-harness --doctor — show version, install mode, daemon and Chrome state, and whether an update is pending.
- browser-harness --update -y — pull the latest version and restart the daemon. Run this yourself when you see the `[browser-harness] update available: X -> Y` banner — don't ask the user. The banner is rate-limited to once per day.

## Architecture

```text
Chrome / Browser Use cloud -> CDP WS -> browser_harness.daemon -> /tmp/bu-<NAME>.sock -> browser_harness.run
```

- Protocol is one JSON line each way.
- Requests are {method, params, session_id} for CDP or {meta: ...} for daemon control.
- Responses are {result} / {error} / {events} / {session_id}.
- BU_NAME namespaces socket, pid, and log files.
- BU_CDP_WS overrides local Chrome discovery for remote browsers.
- BU_BROWSER_ID + BROWSER_USE_API_KEY lets the daemon stop a Browser Use cloud browser on shutdown.

## Keeping the harness current

- On each run, `browser-harness` prints `[browser-harness] update available: X -> Y` (once per day) when a newer GitHub release exists.
- When you see that banner, run `browser-harness --update -y` yourself — don't ask the user. It pulls the new code (`git pull --ff-only` for editable clones, `uv tool upgrade browser-harness` for PyPI installs) and stops the running daemon so the next call picks up the new code. With `-y` it won't prompt.
- `--update` refuses to run on an editable clone with uncommitted changes. If that happens, tell the user and let them resolve the dirty worktree.