"""Render the workshop ladder from progress.json."""
import json
import os

STAGES = [
    ("00", "single node"), ("01", "vertical scaling"), ("02", "horizontal scaling"),
    ("03", "load balancing"), ("04", "rate limiting"), ("05", "replication"),
    ("06", "quorum"), ("07", "fault tolerance"), ("08", "service discovery"),
    ("09", "auto-recovery"), ("10", "full system"),
]

fn = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progress.json")
progress = {}
if os.path.exists(fn):
    with open(fn) as f:
        progress = json.load(f)

print("\n  Build-a-KVStore — progress\n")
for sid, name in STAGES:
    mark = "✅" if progress.get(sid, {}).get("pass") else "⬜"
    print(f"   {mark}  {sid}  {name}")
done = sum(1 for s, _ in STAGES if progress.get(s, {}).get("pass"))
print(f"\n   {done}/{len(STAGES)} stages resolved\n")
