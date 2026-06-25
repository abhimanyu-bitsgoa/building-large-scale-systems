#!/usr/bin/env bash
# ============================================================================
# tmux_lab.sh  <NN>   —   one-window "observe + play" dashboard for ANY stage.
#
# Lays EVERY process the stage runs in its OWN pane so you can WATCH each one
# react — the node(s) on stages 00-04, or registry / coordinator / gateway on
# 05-10. A "control" pane is pre-loaded with helpers so you drive the system BY
# HAND (write/read on 00-04; on 05-10 also kvkill / kvspawn to crash & revive
# nodes) instead of only running the incident checker. An "incident" pane has the
# graded check pre-typed. Mouse mode is on: click a pane to focus, scroll to read.
#
#   bash tools/tmux_lab.sh 03      # build the panes for stage 03 and attach
#   WORKERS=1 bash tools/tmux_lab.sh 01   # stage 01 with 1 worker (demo the choke)
#   bash tools/tmux_lab.sh down    # kill the session + all stage processes
#
# NON-DESTRUCTIVE on code stages (03/04/05/08): won't overwrite your solution.
# Other stages are seeded fresh from their checkpoint so the code is always correct.
# Load a code stage first with:  make gap STAGE=NN  (then implement the gap).
#
# Standalone & disposable: delete this one file to remove it (grep "tmux_lab").
#
# Note: the coordinator (05-10) spawns the leader (:7001) + followers (:7002-:7004)
# as CHILD processes, so their logs share the *coordinator* pane (one process owns
# one terminal). That pane is labelled to make this clear.
# ============================================================================
set -euo pipefail

SESSION="kvlab"
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # build-kvstore/ (where the Makefile lives)
KV="$HERE/kvstore"

# ---- teardown mode ---------------------------------------------------------
if [ "${1:-}" = "down" ]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  bash "$HERE/tools/down.sh" || true
  echo "Tore down tmux session '$SESSION' and all stage processes."
  exit 0
fi

STAGE="${1:-}"
case "$STAGE" in
  0[0-9]|10) : ;;
  *) echo "Usage: bash tools/tmux_lab.sh <NN>   (NN = 00..10)   |   bash tools/tmux_lab.sh down"; exit 1 ;;
esac
N=$((10#$STAGE))   # strip the leading zero so arithmetic doesn't read 08/09 as octal

command -v tmux >/dev/null 2>&1 || { echo "tmux not found (try: apt-get install -y tmux)"; exit 1; }

# ---- seed the working dir (code-stage-aware) -------------------------------
seed_from_checkpoint() {
  local cp; cp="$(ls -d "$HERE"/checkpoints/"$STAGE"-* 2>/dev/null | head -1)"
  [ -n "$cp" ] || { echo "No checkpoints/$STAGE-* found"; exit 1; }
  rm -rf "$KV" && cp -r "$cp" "$KV"
  echo "kvstore/ seeded from $(basename "$cp")"
}
CODE_STAGES=" 03 04 05 08 "
if [[ "$CODE_STAGES" == *" $STAGE "* ]]; then
  if [ ! -e "$KV" ] || [ -z "$(ls -A "$KV" 2>/dev/null)" ]; then
    seed_from_checkpoint
    echo "  (code stage — implement the gap, or 'make reset STAGE=$STAGE' for the solution)"
  else
    echo "kvstore/ left as-is (code stage — your work is preserved; 'make gap STAGE=$STAGE' to restart)"
  fi
else
  seed_from_checkpoint
fi

# Clear leftovers (ports + old session) before we start fresh.
bash "$HERE/tools/down.sh" >/dev/null 2>&1 || true
tmux kill-session -t "$SESSION" 2>/dev/null || true

# ---- which processes this stage runs, in dependency order ------------------
S_TITLE=(); S_CMD=(); TIER=cluster
case "$N" in
  0)
    TIER=node
    S_TITLE+=("node-1  :5001  (a KV store = a dict behind HTTP)")
    S_CMD+=("python node.py --port 5001 --id 1")
    ;;
  1)
    TIER=node; WK="${WORKERS:-4}"
    S_TITLE+=("node-1  :5001  (CPU load + $WK worker(s); the single-thread/GIL ceiling)")
    S_CMD+=("python node.py --port 5001 --id 1 --load-factor 30 --workers $WK")
    ;;
  2|3)
    TIER=node
    S_TITLE+=("node-1  :5001  (weak: 1 worker)");    S_CMD+=("python node.py --port 5001 --id 1 --load-factor 28 --workers 1")
    S_TITLE+=("node-2  :5002  (strong: 4 workers)"); S_CMD+=("python node.py --port 5002 --id 2 --load-factor 28 --workers 4")
    S_TITLE+=("node-3  :5003  (strong: 4 workers)"); S_CMD+=("python node.py --port 5003 --id 3 --load-factor 28 --workers 4")
    ;;
  4)
    TIER=node
    S_TITLE+=("node-1  :5001  (rate limited: 5 req / 10s)")
    S_CMD+=("python node.py --port 5001 --id 1 --load-factor 28 --rate-limit fixed_window --rate-limit-max 5 --rate-limit-window 10")
    ;;
  *)  # cluster tier (05-10)
    if [ "$N" -eq 5 ]; then WR=1; RR=1; else WR=2; RR=2; fi
    if [ "$N" -ge 8 ]; then
      if [ "$N" -ge 9 ]; then
        S_TITLE+=("registry  :9000  (discovery + heartbeats + AUTO-SPAWN)")
        S_CMD+=("python registry.py --port 9000 --auto-spawn --spawn-delay 5")
      else
        S_TITLE+=("registry  :9000  (discovery + heartbeats; no auto-spawn)")
        S_CMD+=("python registry.py --port 9000")
      fi
    fi
    COORD_CMD="python coordinator.py --followers 3 --write-quorum $WR --read-quorum $RR"
    [ "$N" -ge 8 ] && COORD_CMD="$COORD_CMD --registry http://localhost:9000"
    S_TITLE+=("coordinator  :7000  (quorum W=$WR,R=$RR; also shows leader :7001 + followers :7002-:7004)")
    S_CMD+=("$COORD_CMD")
    if [ "$N" -ge 10 ]; then
      S_TITLE+=("gateway  :8000  (edge: rate limit -> coordinator)")
      S_CMD+=("python gateway.py --port 8000 --coordinator http://localhost:7000 --rate-limit --rate-limit-max 10 --rate-limit-window 60")
    fi
    ;;
esac

# ---- URLs for the control pane helpers -------------------------------------
if [ "$TIER" = node ]; then
  NODE_URL="http://localhost:5001"
  if [ "$N" -eq 2 ] || [ "$N" -eq 3 ]; then
    NODES="http://localhost:5001,http://localhost:5002,http://localhost:5003"
  else
    NODES="$NODE_URL"
  fi
  CTRL_ENV="export TIER=node NODE_URL=$NODE_URL NODES=$NODES KVDIR='$KV'"
else
  if [ "$N" -ge 10 ]; then WR_URL="http://localhost:8000"; else WR_URL="http://localhost:7000"; fi
  CTRL_ENV="export TIER=cluster WR_URL=$WR_URL ADMIN_URL=http://localhost:7000"
fi

# ---- build the panes (stable pane IDs; re-tile so each split has room) ------
PANES=(); TITLES=()
add_pane() {  # add_pane <cwd> <title>
  local cwd=$1 title=$2
  if [ "${#PANES[@]}" -eq 0 ]; then
    tmux new-session -d -s "$SESSION" -n "lab$STAGE" -c "$cwd"
    PANES+=("$(tmux display-message -p -t "$SESSION:0" '#{pane_id}')")
  else
    PANES+=("$(tmux split-window -d -P -F '#{pane_id}' -t "${PANES[-1]}" -c "$cwd")")
    tmux select-layout -t "$SESSION:0" tiled >/dev/null
  fi
  TITLES+=("$title")
}

for i in "${!S_CMD[@]}"; do add_pane "$KV" "${S_TITLE[$i]}"; done
if [ "$TIER" = node ]; then
  add_pane "$HERE" "control  (drive it by hand: nwrite/nread/nhealth/nload)"
else
  add_pane "$HERE" "control  (drive it by hand: kvwrite/kvread/kvkill/kvspawn/kvstatus)"
fi
add_pane "$HERE" "incident  (press Enter to run the graded check; re-run any time)"
add_pane "$HERE" "scratch  (free shell)"

NSVC=${#S_CMD[@]}
P_CTRL="${PANES[$NSVC]}"
P_INC="${PANES[$((NSVC+1))]}"
P_SCR="${PANES[$((NSVC+2))]}"

# ---- mouse mode + per-pane border titles -----------------------------------
tmux set-option -g mouse on
tmux set-option -w -t "$SESSION:0" pane-border-status top
tmux set-option -w -t "$SESSION:0" pane-border-format " #[bold]#{pane_title}#[default] "
for i in "${!PANES[@]}"; do tmux select-pane -t "${PANES[$i]}" -T "${TITLES[$i]}"; done

# ---- start the services in dependency order (give each time to bind) --------
for i in "${!S_CMD[@]}"; do
  tmux send-keys -t "${PANES[$i]}" "${S_CMD[$i]}" C-m
  [ "$i" -lt "$((NSVC-1))" ] && sleep 3
done
sleep 2

# ---- pre-load the control + incident panes ---------------------------------
tmux send-keys -t "$P_CTRL" "$CTRL_ENV; source '$HERE/tools/kvplay.sh'; kvhelp" C-m
tmux send-keys -t "$P_INC" "make incident STAGE=$STAGE"   # no Enter — fire it when ready
tmux send-keys -t "$P_SCR" "# scratch shell — e.g.  make status" C-m
tmux select-pane -t "$P_CTRL"

echo
echo "Lab dashboard for stage $STAGE is up. Attaching…"
if [ "$TIER" = node ]; then
  echo "  • try:  nwrite cart shoes → nread cart"
  [ "$N" -eq 2 ] || [ "$N" -eq 3 ] && echo "  • compare routing:  nload adaptive 40 10   vs   nload round_robin 40 10"
else
  echo "  • try:  kvwrite cart shoes → kvstatus → kvkill 1 → kvstatus → kvspawn"
fi
echo "  • run the graded check: press Enter in the incident pane"
echo "  • click a pane to focus (mouse on); scroll with the wheel (q to exit scroll)"
echo "  • detach: Ctrl-b then d     • tear down: bash tools/tmux_lab.sh down"
echo

if [ -n "${TMUX:-}" ]; then
  tmux switch-client -t "$SESSION"
else
  tmux attach-session -t "$SESSION"
fi
