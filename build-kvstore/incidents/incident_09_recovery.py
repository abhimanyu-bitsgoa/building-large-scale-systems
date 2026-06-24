"""INC-09 (auto-recovery): a dead follower should be respawned and caught up.
GREEN when the cluster returns to full strength AND the revived node has the data."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")


def main():
    requests.post(f"{C}/write", json={"key": "rec", "value": "v1"}, timeout=20)
    st = requests.get(f"{C}/status", timeout=10).json()
    n = len(st["followers"])
    f1 = next((f for f in st["followers"] if f["node_id"] == "follower-1"), None)
    requests.post(f"{C}/kill/follower-1", timeout=10)
    time.sleep(18)  # heartbeat timeout + spawn delay + catchup
    st2 = requests.get(f"{C}/status", timeout=10).json()
    alive = sum(1 for f in st2["followers"] if f["status"] == "alive")
    has = False
    try:
        has = requests.get(f"{f1['url']}/data/rec", timeout=5).status_code == 200
    except Exception:
        pass
    report("09", "Auto-respawn + catchup",
           alive >= n and has,
           f"recovered to {alive}/{n} alive; revived follower has the data = {has} "
           f"(needs --auto-spawn and catchup on /spawn)")


main()
