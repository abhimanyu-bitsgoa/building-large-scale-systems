#!/usr/bin/env bash
# Stop every workshop process started by up.sh.
for p in gateway.py coordinator.py registry.py node.py; do
  pkill -f "$p" 2>/dev/null
done
# Also kill orphaned uvicorn worker processes (started with --workers): their command
# line is just "python", so matching by script name misses them — kill them by workshop port.
for port in 5001 5002 5003 5004 5005 7000 7001 7002 7003 7004 7005 7006 8000 9000; do
  for pid in $(ss -ltnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u); do
    kill -9 "$pid" 2>/dev/null
  done
done
echo "Stopped workshop processes."
