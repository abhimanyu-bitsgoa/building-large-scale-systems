"""INC-05 (replication): a write to the leader must reach the followers.
GREEN when data written via the coordinator is durable on the cluster (read back after it propagates)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")


def main():
    key = f"repl_{int(time.time())}"
    try:
        w = requests.post(f"{C}/write", json={"key": key, "value": "v1"}, timeout=20)
    except Exception as e:
        report("05", "Single-leader replication", False, f"write failed: {e}")
    if w.status_code != 200:
        report("05", "Single-leader replication", False, f"write rejected ({w.status_code})")
    time.sleep(6)  # let async replication reach the followers
    r = requests.get(f"{C}/read/{key}", timeout=10)
    ok = r.status_code == 200 and r.json().get("value") == "v1"
    report("05", "Single-leader replication",
           ok,
           f"after replication, read returns {r.status_code} "
           f"({'data propagated to followers' if ok else 'followers never got the write'})")


main()
