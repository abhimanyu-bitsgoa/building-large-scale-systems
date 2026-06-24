"""INC-03 (load balancing): round-robin ignores node capacity and tanks on a slow node.
GREEN when the adaptive strategy you implemented routes around it (adaptive p95 < round-robin p95)."""
import os
import re
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KVSTORE = os.environ.get("KVSTORE_DIR", os.path.join(ROOT, "kvstore"))


def p95_for(strategy):
    try:
        out = subprocess.run(
            ["python", "client.py", "--strategy", strategy, "--concurrent", "4", "--requests", "24"],
            cwd=KVSTORE, capture_output=True, text=True, timeout=180).stdout
    except Exception:
        return None
    m = re.search(r"Global P95 Latency:\s*([\d.]+)ms", out)
    return float(m.group(1)) if m else None


def main():
    rr = p95_for("round_robin")
    ad = p95_for("adaptive")
    if rr is None or ad is None:
        report("03", "Adaptive load balancing", False,
               "could not measure both strategies via client.py — is AdaptiveStrategy implemented?")
    report("03", "Adaptive load balancing",
           ad < rr,
           f"round-robin p95={rr:.0f}ms vs adaptive p95={ad:.0f}ms (adaptive should avoid the slow node)")


main()
