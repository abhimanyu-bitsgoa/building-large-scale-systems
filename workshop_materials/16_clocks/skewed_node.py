import uvicorn
from fastapi import FastAPI
import time
import argparse

app = FastAPI()

# {key: {"value": str, "version_ts": float}}
data_store = {}
CLOCK_OFFSET = 0 # Seconds to add/subtract from real time

@app.post("/write/{key}")
def write(key: str, value: str):
    # This node's "local" time
    local_time = time.time() + CLOCK_OFFSET
    
    current = data_store.get(key)
    if current and current["version_ts"] > local_time:
        print(f"⚠️  REJECTED: Write for {key} is older ({local_time:.2f}) than current version ({current['version_ts']:.2f})")
        return {"status": "rejected", "reason": "stale_timestamp", "local_time": local_time}
    
    data_store[key] = {"value": value, "version_ts": local_time}
    print(f"✅ ACCEPTED: Written {key}={value} at local_time {local_time:.2f}")
    return {"status": "accepted", "saved_ts": local_time}

@app.get("/read/{key}")
def read(key: str):
    return data_store.get(key, {"error": "not found"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--offset", type=int, default=0, help="Clock offset in seconds")
    args = parser.parse_args()
    
    CLOCK_OFFSET = args.offset
    print(f"Storage Node starting on port {args.port} (Clock Offset: {CLOCK_OFFSET}s)")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
