"""INC-06 (quorum): an immediate read after an UPDATE must return the NEW value, not the old one.
Demonstrates true staleness: all followers have an old copy; one async follower hasn't received
the latest write yet. With W+R<=N the read set may miss the updated copy entirely.
GREEN when W+R>N so the read set is guaranteed to overlap the latest write."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")
N = 4   # number of update-then-read trials


def main():
    stale = 0
    for i in range(N):
        key = f"cart_{int(time.time()*1000)}_{i}"

        # Step 1: write the OLD value and let it fully propagate to ALL followers
        # (including the slow async ones, whose lag is ~5s). Every follower gets "old"
        # so a miss on the next read is genuine staleness, not absence.
        w = requests.post(f"{C}/write", json={"key": key, "value": "old"}, timeout=20)
        if w.status_code != 200:
            report("06", "No stale reads (W+R>N)", False,
                   f"write rejected ({w.status_code}) — check the cluster is up")
        time.sleep(7)   # > async delay (5s) so every follower has "old"

        # Step 2: UPDATE to "fresh" but don't wait for async replication.
        w2 = requests.post(f"{C}/write", json={"key": key, "value": "fresh"}, timeout=20)
        if w2.status_code != 200:
            report("06", "No stale reads (W+R>N)", False,
                   f"update rejected ({w2.status_code}) — check the cluster is up")

        # Step 3: read IMMEDIATELY. With W+R<=N the read may land on the async follower
        # that still holds "old" — a genuinely stale value, not a missing one.
        r = requests.get(f"{C}/read/{key}", timeout=10)
        got = r.json().get("value") if r.status_code == 200 else None
        if got != "fresh":
            stale += 1

    ok = stale == 0
    report("06", "No stale reads (W+R>N)", ok,
           f"{stale}/{N} immediate reads returned an old value — "
           + ("the read set overlaps the write set (W+R>N): you always hit an up-to-date replica"
              if ok else
              "the async follower still held the previous value: raise R until W+R>N so the "
              "read set is forced to overlap the node that received the latest write"))


main()
