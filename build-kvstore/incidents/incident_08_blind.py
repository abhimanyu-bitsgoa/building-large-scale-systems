"""INC-08 (service discovery): the system must notice when a node dies.
GREEN when a killed follower is detected as dead within the heartbeat timeout."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

C = os.environ.get("COORDINATOR", "http://localhost:7000")
R = os.environ.get("REGISTRY", "http://localhost:9000")


def main():
    requests.post(f"{C}/kill/follower-1", timeout=10)
    time.sleep(10)  # longer than the heartbeat timeout
    nodes = requests.get(f"{R}/nodes", timeout=10).json().get("nodes", [])
    f1 = next((n for n in nodes if n["node_id"] == "follower-1"), None)
    status = f1["status"] if f1 else "unknown-to-registry"
    ok = status == "dead"
    report("08", "Death detection via heartbeats", ok,
           f"registry reports follower-1 = {status} — "
           + ("heartbeats let the registry detect the death" if ok
              else "want 'dead'; without heartbeats the registry never even sees the node"))


main()
