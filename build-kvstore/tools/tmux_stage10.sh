#!/usr/bin/env bash
# ============================================================================
# tmux_stage10.sh  —  OPTIONAL stage-10 "see every component" dashboard.
#
# This is NOT part of the core workshop and is intentionally standalone: it does
# not modify or depend on the Makefile, up.sh or any other file. It just lays the
# full KV-store system out one component per tmux pane so you can watch the
# registry, coordinator, gateway and a client side by side.
#
#   bash tools/tmux_stage10.sh         # seed stage 10, build the panes, attach
#   bash tools/tmux_stage10.sh down    # kill the tmux session + all processes
#
# To remove this feature entirely, delete THIS ONE FILE (grep "tmux_stage10").
#
# Pane layout (tiled — identity shown in each pane's border title):
#   ┌──────────────┬──────────────┬──────────────┐
#   │ registry     │ coordinator  │ gateway       │   the three services
#   ├──────────────┴──────┬───────┴──────────────┤
#   │ client (interactive)│ scratch (free shell) │
#   └─────────────────────┴──────────────────────┘
#
# Note: the coordinator spawns the leader + 3 followers as child processes, so
# their logs appear inside the *coordinator* pane. Don't run assessment.py at the
# same time — it spins up its own separate cluster on the same ports.
# ============================================================================
set -euo pipefail

SESSION="kvstore10"
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # build-kvstore/
KV="$HERE/kvstore"

# ---- teardown mode ---------------------------------------------------------
if [ "${1:-}" = "down" ]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  bash "$HERE/tools/down.sh" || true
  echo "Tore down tmux session '$SESSION' and all stage processes."
  exit 0
fi

# ---- preconditions ---------------------------------------------------------
command -v tmux >/dev/null 2>&1 || { echo "tmux not found (try: apt-get install -y tmux)"; exit 1; }

# Seed the working dir with the full-system code. The capstone is config-only
# (you tune student_config.json, you don't edit code), so re-seeding is safe.
CP="$(ls -d "$HERE"/checkpoints/10-* 2>/dev/null | head -1)"
[ -n "$CP" ] || { echo "No checkpoints/10-* found"; exit 1; }
rm -rf "$KV" && cp -r "$CP" "$KV"
echo "kvstore/ seeded from $(basename "$CP")"

# Clear anything left over from a previous run (ports + old session).
bash "$HERE/tools/down.sh" >/dev/null 2>&1 || true
tmux kill-session -t "$SESSION" 2>/dev/null || true

# ---- build the panes (use stable pane IDs, never positional indexes) --------
# Re-tile after every split so each pane always has room to split again — this
# avoids tmux's "no space for new pane" on smaller terminals.
tmux new-session -d -s "$SESSION" -n stage10 -c "$KV"
P_REG="$(tmux display-message -p -t "$SESSION:0" '#{pane_id}')"
P_COORD="$(tmux  split-window -d -P -F '#{pane_id}' -t "$P_REG"    -c "$KV")"; tmux select-layout -t "$SESSION:0" tiled
P_GW="$(tmux     split-window -d -P -F '#{pane_id}' -t "$P_COORD"  -c "$KV")"; tmux select-layout -t "$SESSION:0" tiled
P_CLIENT="$(tmux split-window -d -P -F '#{pane_id}' -t "$P_GW"     -c "$KV")"; tmux select-layout -t "$SESSION:0" tiled
P_SCRATCH="$(tmux split-window -d -P -F '#{pane_id}' -t "$P_CLIENT" -c "$KV")"; tmux select-layout -t "$SESSION:0" tiled

# ---- mouse mode: click a pane to focus it, scroll to view history ----------
# Far friendlier than the Ctrl-b prefix for anyone new to tmux. (On macOS, hold
# Option/Alt while dragging if you want to select text for copy.)
tmux set-option -g mouse on

# ---- label each pane in its border ----------------------------------------
tmux set-option -w -t "$SESSION:0" pane-border-status top
tmux set-option -w -t "$SESSION:0" pane-border-format " #[bold]#{pane_title}#[default] "
tmux select-pane -t "$P_REG"     -T "registry  :9000  (discovery + heartbeats + auto-spawn)"
tmux select-pane -t "$P_COORD"   -T "coordinator  :7000  (quorum; spawns leader :7001 + followers :7002-:7004)"
tmux select-pane -t "$P_GW"      -T "gateway  :8000  (edge: rate limit -> coordinator)"
tmux select-pane -t "$P_CLIENT"  -T "client  (interactive -> gateway :8000)"
tmux select-pane -t "$P_SCRATCH" -T "scratch  (free shell: curl / make status / etc.)"

# ---- start the services in dependency order --------------------------------
# registry first, then coordinator (needs the registry), then gateway (needs the
# coordinator). The sleeps give each service a moment to bind before the next.
tmux send-keys -t "$P_REG" \
  'python registry.py --port 9000 --auto-spawn --spawn-delay 5' C-m
sleep 2
tmux send-keys -t "$P_COORD" \
  'python coordinator.py --followers 3 --write-quorum 2 --read-quorum 2 --registry http://localhost:9000' C-m
sleep 4
tmux send-keys -t "$P_GW" \
  'python gateway.py --port 8000 --coordinator http://localhost:7000 --rate-limit --rate-limit-max 10 --rate-limit-window 60' C-m

# ---- pre-load (but don't run) the client; pre-seed the scratch hint --------
# The client command is pre-typed (no Enter) so you launch it with one keypress
# once the gateway is up.
tmux send-keys -t "$P_CLIENT" 'python client.py'
tmux send-keys -t "$P_SCRATCH" \
  '# scratch shell — e.g.: curl -s localhost:7000/status | python -m json.tool   |   make status' C-m

tmux select-pane -t "$P_CLIENT"

echo
echo "Dashboard '$SESSION' is up. Attaching…"
echo "  • switch panes:  CLICK a pane (mouse mode is on)  — or  Ctrl-b then arrow"
echo "  • scroll a pane: mouse wheel  (press q to exit scroll)"
echo "  • detach:        Ctrl-b then d   (Ctrl-b = press & release, THEN the next key)"
echo "  • select text:   hold Option/Alt while dragging (macOS)"
echo "  • tear it down:  bash tools/tmux_stage10.sh down"
echo

# Attach (or switch, if you're already inside tmux).
if [ -n "${TMUX:-}" ]; then
  tmux switch-client -t "$SESSION"
else
  tmux attach-session -t "$SESSION"
fi
