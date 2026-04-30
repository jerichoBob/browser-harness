browser-harness is a thin layer that connects agents to browsers via an editable CDP harness.

# Code priorities
- Clarity
- Precision
- Low verbosity
- Versatility

# Overview
Core code lives in `src/browser_harness/`:
- `admin.py` — harness setup and daemon lifecycle (start, stop, attach, profile management)
- `daemon.py` — the long-lived middleman process between the browser and the agent
- `helpers.py` — CDP wrapper and core browser primitives auto-imported into `-c` scripts
- `run.py` — the `browser-harness` CLI

`SKILL.md` tells agents how to use the harness.
`install.md` tells agents how to install it, attach a browser, and troubleshoot.

An agent operating the harness only edits inside `agent-workspace/`, where it can add new helper functions and write or read skills.

# Contributing
Consider what is really needed. Prefer the smallest diff that fixes the bug.
