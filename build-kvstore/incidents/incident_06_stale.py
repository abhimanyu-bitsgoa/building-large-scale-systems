"""INC-06 (quorum): a read right after a write must not be stale.
GREEN when W+R>N so the read set overlaps the latest write."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")
N = 8


def main():
    stale = 0
    for i in range(N):
        key = f"cart_{int(time.time()*1000)}_{i}"
        w = requests.post(f"{C}/write", json={"key": key, "value": "fresh"}, timeout=20)
        if w.status_code != 200:
            report("06", "No stale reads (W+R>N)", False,
                   f"write rejected ({w.status_code}) — fix the write quorum first")
        r = requests.get(f"{C}/read/{key}", timeout=10)  # immediate
        if not (r.status_code == 200 and r.json().get("value") == "fresh"):
            stale += 1
    ok = stale == 0
    report("06", "No stale reads (W+R>N)", ok,
           f"{stale}/{N} immediate reads were stale — "
           + ("the read set overlaps the latest write (W+R>N)" if ok
              else "raise R until W+R>N so the read set overlaps the latest write"))


main()
