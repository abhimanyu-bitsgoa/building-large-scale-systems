"""INC-07 (fault tolerance / CAP): the cluster must survive floor(N/2) node failures.
GREEN when writes still succeed after killing the tolerable number of followers."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")


def main():
    st = requests.get(f"{C}/status", timeout=10).json()
    n = len(st["followers"])
    to_kill = n // 2
    for i in range(1, to_kill + 1):
        requests.post(f"{C}/kill/follower-{i}", timeout=10)
    time.sleep(8)
    w = requests.post(f"{C}/write", json={"key": "after_failure", "value": "ok"}, timeout=20)
    report("07", f"Survive floor(N/2)={to_kill} failures",
           w.status_code == 200,
           f"after killing {to_kill}/{n} followers, write returned {w.status_code} "
           f"(503 means the write quorum is too tight — lower W)")


main()
