import uvicorn
from fastapi import FastAPI, BackgroundTasks
import requests
import time
import argparse

app = FastAPI()

# In-memory store
data_store = {}
SECONDARIES = [] # List of ports
REPLICATION_DELAY = 2 # Seconds

def replicate_to_secondary(port, key, value):
    """Wait for artificial delay then send to secondary."""
    time.sleep(REPLICATION_DELAY)
    try:
        requests.post(f"http://localhost:{port}/replicate", json={"key": key, "value": value}, timeout=1)
        print(f"  [Primary] Replicated {key} to port {port}")
    except Exception as e:
        print(f"  [Primary] Failed to replicate to {port}: {e}")

@app.post("/write")
async def write_data(payload: dict, background_tasks: BackgroundTasks):
    key = payload["key"]
    value = payload["value"]
    
    # Update local store
    data_store[key] = value
    print(f"[Primary] Written {key}={value}. Triggering replication...")
    
    # Trigger replication in background
    for port in SECONDARIES:
        background_tasks.add_task(replicate_to_secondary, port, key, value)
        
    return {"status": "written", "node": "primary"}

@app.get("/data/{key}")
def get_data(key: str):
    return {"key": key, "value": data_store.get(key), "node": "primary"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=13000)
    parser.add_argument("--secondaries", type=str, default="13001,13002")
    parser.add_argument("--delay", type=int, default=5)
    args = parser.parse_args()
    
    SECONDARIES = [int(p) for p in args.secondaries.split(",")]
    REPLICATION_DELAY = args.delay
    
    print(f"Primary Node starting on port {args.port}...")
    print(f"Secondaries: {SECONDARIES} (Delay: {REPLICATION_DELAY}s)")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
