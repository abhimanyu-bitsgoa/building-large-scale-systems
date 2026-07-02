# `make verify` attendee preflight + Linux bind-mount chmod fix

**Date:** 2026-07-02
**Scope:** `build-kvstore/` + root `README.md` / `WORKSHOP-WALKTHROUGH.md`. Status: accepted.

## Context

EuroPython workshop, 40–60 attendees on mixed Windows/macOS/Linux laptops. The author wanted
one command attendees can run to prove their whole setup works before the session. A
cross-OS portability audit of `build-kvstore/` was done alongside; two real gaps were found
and fixed here.

## Decision 1 — container-first preflight: `make verify`

**What:** new attendee verb `make verify` → `tools/verify_setup.sh`, run INSIDE the container.
Checks, in order: (1) actually inside the container (`/.dockerenv` / `/workspace`), (2) python +
`import fastapi, uvicorn, requests, httpx`, (3) `curl`/`make`/`tmux` present, (4) tmux can create
a *detached* session (proves `make lab` will work without trapping the attendee in tmux),
(5) the real smoke test — boots the stage-01 node **directly from `checkpoints/01-*`**, polls
`/health`, does an HTTP write + read round-trip, then cleans up via `tools/down.sh`. Ends in a
box-drawing `SETUP VERIFIED` banner (which doubles as the UTF-8 rendering check) or per-check
`[FAIL]` lines each carrying a one-line fix. ~15s, idempotent, ASCII tags only (no emoji — house
rule).

**Why container-first instead of native `verify.sh`/`verify.ps1` wrappers:** the alternative
(host-side scripts that auto-start Docker Desktop, then exec in) was considered and rejected.
Getting a shell via `docker-compose exec workshop bash` already proves Docker is installed,
running, built, and mounted — so per-OS wrapper scripts add maintenance (PowerShell execution
policy, daemon autostart per OS) for almost no signal. One bash script in a fixed Ubuntu image
= zero cross-platform surface. The trade-off accepted: the script cannot start Docker itself;
the README covers that with one line per platform.

**Non-destructive by design:** the smoke test runs the node from `checkpoints/01-*`, never
seeding `kvstore/`, so an attendee mid-exercise can run it without losing work. It *does* call
`down.sh` (stops running workshop processes) — documented in the script header.

## Decision 2 — `chmod -R a+rw kvstore` after every seed (the Linux fix)

The container runs as root, so `make start`/`todo`/`checkpoint` and `tmux_lab.sh`'s
`seed_from_checkpoint` created root-owned files on the bind mount. On **Linux hosts** that
means an attendee's host editor (VS Code) gets *permission denied* saving the exercise file —
mid-workshop, at the worst moment. macOS/Windows are immune (Docker Desktop maps ownership).
Fix: chain `chmod -R a+rw kvstore` after each `cp -r` (4 sites: 3 Makefile targets +
`tmux_lab.sh`). Harmless on Docker Desktop platforms.

## Decision 3 — platform notes + doc reconciliation

- Root `README.md`: "Verify Setup" now points at `make verify` (was: run a `labs/scalability`
  node by hand); added **Platform notes** (Windows: use PowerShell/Windows Terminal, not Git
  Bash — MinTTY breaks `exec` with "the input device is not a TTY"; `docker compose` vs
  `docker-compose`; Linux daemon start) and a "run this the day before, not on conference
  wifi" callout.
- `WORKSHOP-WALKTHROUGH.md`: still said `make gap`/`make reset` — the 2026-07-02 verb rename
  ([2026-07-02_rename-gap-todo-reset-checkpoint.md](2026-07-02_rename-gap-todo-reset-checkpoint.md))
  only swept `build-kvstore/`, so this root doc referenced dead targets. Renamed here, and
  `make verify` added to its setup + cheat sheet.
- `LAB-MANUAL.md` setup + cheat sheet, `instructor/HANDOFF.md` + `SPEC.md` verb lists updated.

## Audit results recorded (checked, NOT bugs)

For future reference, these cross-OS concerns were explicitly verified fine: `.gitattributes`
forces LF and overrides attendee `core.autocrlf` (the CRLF issue is fixed at the root); no
symlinks; no case-colliding paths; nodes are in-memory (no bind-mount data files); no host
ports; `venv/`/`__pycache__` untracked; CRLF saved by a Windows editor into the one `.py`
attendees edit is harmless (Python tolerates it). Remaining known risk: `incident_01`/`incident_03`
timing thresholds on very slow laptops — already mitigated (env-var budget, best-of-3) and
documented as "re-run it".

## Side effects / risks

- `make verify` kills running workshop processes (via `down.sh`) — same behavior as `make down`,
  stated in the script header.
- `chmod a+rw` makes seeded files world-writable inside the repo checkout; irrelevant for a
  disposable, gitignored working dir.
- **Known residual staleness (out of scope here):** `WORKSHOP-WALKTHROUGH.md` still describes
  the pre-2026-06-30 ladder (stages 00–10, `STAGE=00`, separate horizontal-scaling stage,
  "18/18 cases"). Flagged for a separate pass; do not treat its stage numbering as current.

## Verification

Ran in the live container: `make verify` → 9/9 `[OK]` + banner, exit 0; host run → graceful
`[FAIL]` + exit 1; port 5001 confirmed free afterwards. `make -n start|todo|checkpoint` show
the chmod chained correctly; `bash -n` clean on both scripts.
