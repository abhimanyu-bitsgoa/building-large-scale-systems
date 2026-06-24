"""INC-02 (horizontal scaling): one node can't serve everything and is a single point of failure.
GREEN when load is spread across multiple reachable nodes (>=90% served)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from _harness import report

NODES = os.environ.get("NODES", "http://localhost:5001,http://localhost:5002,http://localhost:5003").split(",")
TOTAL = 30


def main():
    ok = 0
    for i in range(TOTAL):
        node = NODES[i % len(NODES)]
        try:
            if requests.post(f"{node}/data", json={"key": f"k{i}", "value": "v"}, timeout=10).status_code == 200:
                ok += 1
        except Exception:
            pass
    rate = ok / TOTAL
    passed = rate >= 0.9
    report("02", "Horizontal scaling across nodes", passed,
           f"{ok}/{TOTAL} requests served across {len(NODES)} nodes ({rate*100:.0f}%) — "
           + ("load is spread across the cluster" if passed
              else "most failed: a single node leaves the other addresses unreachable"))


main()
