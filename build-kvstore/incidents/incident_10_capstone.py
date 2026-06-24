"""INC-10 (capstone): run the full assessment against your deployed system + config.
GREEN when the score meets the bar. (assessment.py spins up its own cluster.)"""
import os
import re
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KVSTORE = os.environ.get("KVSTORE_DIR", os.path.join(ROOT, "kvstore"))
CONFIG = os.environ.get("CONFIG", "student_config.json")
BAR = int(os.environ.get("BAR", "80"))


def main():
    try:
        out = subprocess.run(["python", "assessment.py", "--config", CONFIG],
                             cwd=KVSTORE, capture_output=True, text=True, timeout=300).stdout
    except Exception as e:
        report("10", "Capstone assessment", False, f"could not run assessment.py: {e}")
    m = re.search(r"TOTAL SCORE:\s*([\d.]+)/", out)
    score = float(m.group(1)) if m else 0.0
    ok = score >= BAR
    report("10", "Capstone assessment", ok,
           f"assessment score = {score:.0f}/100 (bar {BAR}) — "
           + ("your config resolves the incidents" if ok
              else "edit student_config.json to resolve the incidents"))


main()
