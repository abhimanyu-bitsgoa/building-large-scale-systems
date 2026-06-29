# Remove emoji from terminal-facing code output (keep box-art + graduation easter egg)

**Date:** 2026-06-30
**Status:** accepted

## Context

Every lab process logs to its own tmux pane (`tools/tmux_lab.sh`). The `print()`/
`logger.log()` output was decorated with emoji (✅ ❌ 🚫 ⚠️ 🟢 🔴 🔄 🚀 👑 💀 ⏱️
📊 📋 📖 📝 📥 ⏳ 🌐 ➕ 🖥️ 🛡️ …). Two problems:

1. **Scrollback jumbling.** Emoji — and especially variation-selector sequences
   like `⏱️` (`U+23F1 U+FE0F`) — have an *ambiguous display width*. tmux computes
   each cell's width with its own `wcwidth` table; the outer terminal renders the
   glyph with its own rules. When the two disagree, tmux's cursor model drifts from
   what's on screen. While a pane only appends text the drift is hidden, but on
   **scroll** (copy-mode) tmux repaints from its grid and the accumulated
   misalignment shows up as overlapped/jumbled lines. Reported by the speaker while
   scrolling the stage-02 control pane.
2. **Aesthetics.** The speaker finds the emoji distracting / "AI-slop"-looking for a
   conference demo.

A prior attempt addressed (1) by *forcing* a UTF-8 locale so the glyphs render at
all (`tools/tmux_lab.sh` `export LANG/LC_ALL` + `tmux -u`). That makes them appear
but does not fix the width-disagreement on scroll. This decision reverses that
approach: remove the emoji rather than try to render them.

## Decision

Strip **true emoji** from all terminal-facing `.py`/`.sh` and replace them with ASCII:

- **Event-outcome glyphs → bracketed tags** (kept for at-a-glance scanning, which is
  the one thing the emoji did add to a live demo):
  `✅→[OK]  ❌→[ERR]  🚫→[RL]  ⚠️→[WARN]  🟢→[UP]  🔴→[DOWN]  💀→[DEAD]`
  `👑→[LEADER]  📋→[NODE]  📖→[READ]  ✍️→[WRITE]  🚀→[START]  🌐→[API]  ➕→[SPAWN]  🔄→[INFO]`
- **Decorative / process-step glyphs → dropped** (the message text already says what
  happened): `⏱️ 📊 📝 📥 ⏳ ⏭️ 🔢 🖥️ 🛡️ 👋 🛑` and the per-line stats prefixes.
- **Incident harness banner** (`incidents/_harness.py`):
  `✅ INCIDENT RESOLVED → [PASS] INCIDENT RESOLVED`, `❌ INCIDENT ACTIVE → [FAIL] …`.
- **`tools/status.py`** checklist: `✅/⬜ → [x]/[ ]`.

### Explicitly KEPT (not emoji, or intentional)

- **Box-drawing art** (`═ ║ █ ╔ ─ │ …`) — the coordinator/gateway dashboards and the
  ASCII banners. Single-width, render consistently, not the cause of the jumbling.
- **Prose/math punctuation** (`— → • … § ≠`).
- **The graduation easter egg** in `checkpoints/10-full-system/gateway.py`
  (`GRADUATION_ART` block + the `/graduate` print + the menu's "Celebrate 🎓" line).
  Intentional fun, printed once at the final stage — not slop. Speaker confirmed keep.

## Scope

Code & scripts only — markdown docs (`instructor/architecture.md`, `slide-deck.md`,
etc.) were **left untouched**: they don't render in the tmux panes (zero rendering
benefit) and stripping emoji there risks disturbing diagrams. 47 files changed
(`checkpoints/*`, `stages/*`, `incidents/_harness.py`, `tools/status.py`,
`tools/validate_ladder.sh`, plus the `tmux_lab.sh` rationale comment).

## How it was done

A one-shot transform (`strip_emoji.py`, kept in scratch, not committed) over
`git ls-files '*.py' '*.sh'` with **exact-string** replacements in three ordered
phases (special multi-line cases → quoted single-emoji tokens → bare in-string glyph
+ trailing space). The `GRADUATION_ART` triple-quoted block is pulled out behind a
placeholder before transforming and restored after; any line containing box-drawing
or the 🎓/★ glyphs is skipped. Exact-string matching (rather than a blanket
non-ASCII strip) is what protects the box-art and avoids orphaning the invisible
`U+FE0F` variation selectors.

## Alternatives considered

- **Leave emoji, rely on the forced UTF-8 locale** (status quo). Rejected: the locale
  makes glyphs *render* but does not fix the tmux/terminal width disagreement, so the
  scrollback jumbling persists; also doesn't address the aesthetic objection.
- **Blanket "strip all non-ASCII" regex.** Rejected: would destroy the box-drawing
  dashboards and the graduation banner, and would leave orphaned `U+FE0F` bytes.
- **Replace every emoji 1:1 with a unique word tag.** Rejected: the same glyph is
  reused in different semantic roles (`📋` = "node started" *and* the follower-role
  marker; `❌` = error *and* a yes/no value), so a blind map produces nonsense and
  redundancy (`[LEADER] Starting LEADER node`). Context-aware exact replacement used
  instead; the redundant `role_emoji` prefix in `node.py` was removed outright.
- **Also strip docs.** Rejected for now (see Scope) — can be a separate pass.

## Side effects / risks

- **Functionally inert.** All changes are inside `print()`/`logger.log()`/`echo`
  strings and HTML. Nothing branches on or parses emoji: the incident harness records
  a boolean and `validate_ladder.sh` checks exit codes, not output text. Verified all
  `.py` parse and `bash -n` on the changed script.
- **Tag-width alignment** is approximate (`[OK]` 4 chars vs `[ERR]` 5); acceptable for
  log lines, not tabular output.
- **Regression check:** `make validate` (the only automated check) — expected to stay
  green (18/18 cases). Run in the **background** inside the container; foreground runs
  time out and leave orphan clusters → spurious failures.
- A running client/process started before the edit keeps the old output until
  restarted (the lab reseeds `kvstore/` from the checkpoint on `make lab`, so a fresh
  run picks up the change automatically).
