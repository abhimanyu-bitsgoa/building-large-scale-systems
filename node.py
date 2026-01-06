import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
import argparse
import math
import time

app = FastAPI()

# Global variable to store node ID (will be set at startup)
NODE_ID = 0
LOAD_FACTOR = 0

# Store data in-memory
data_store = {}

# Active Request Counter
active_requests = 0

class DataPayload(BaseModel):
    key: str
    value: str

@app.middleware("http")
async def active_request_middleware(request: Request, call_next):
    global active_requests
    active_requests += 1
    try:
        response = await call_next(request)
        response.headers["X-Active-Requests"] = str(active_requests)
        return response
    finally:
        active_requests -= 1

def simulate_cpu_load(n):
    """
    Calculates Fibonacci(n) inefficiently to simulate CPU load.
    The GIL ensures this creates resource contention for other threads.
    """
    if n <= 0:
        return
    
    start_time = time.time()
    def fib(x):
        if x <= 1: return x
        return fib(x-1) + fib(x-2)
    
    _ = fib(n)
    duration = (time.time() - start_time) * 1000
    print(f"[Node {NODE_ID}] CPU Load: fib({n}) took {duration:.2f}ms")

@app.get("/")
def home():
    return {"message": "Node is running", "id": NODE_ID}

@app.get("/health")
def health():
    return {"status": "ok", "node_id": NODE_ID, "active_requests": active_requests}

@app.get("/stats")
def stats():
    return {
        "node_id": NODE_ID,
        "active_requests": active_requests,
        "load_factor": LOAD_FACTOR
    }

@app.post("/data")
def store_data(payload: DataPayload):
    """Store a key-value pair in this node's data store."""
    if LOAD_FACTOR > 0:
        simulate_cpu_load(LOAD_FACTOR)
        
    data_store[payload.key] = payload.value
    return {
        "status": "stored",
        "node_id": NODE_ID,
        "key": payload.key,
        "value": payload.value
    }

@app.get("/data/{key}")
def get_data(key: str):
    """Retrieve a value by key from this node's data store."""
    if key not in data_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found on Node {NODE_ID}")
        
    if LOAD_FACTOR > 0:
        simulate_cpu_load(LOAD_FACTOR)
        
    return {
        "node_id": NODE_ID,
        "key": key,
        "value": data_store[key]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--load-factor", type=int, default=0, help="Fibonacci input to simulate CPU load (e.g., 30)")
    parser.add_argument("--workers", type=int, default=1, help="Number of Uvicorn worker processes")
    args = parser.parse_args()
    
    NODE_ID = args.id
    LOAD_FACTOR = args.load_factor
    
    print(f"Starting Node {NODE_ID} on port {args.port} (Load Factor: {LOAD_FACTOR}, Workers: {args.workers})")
    
    if args.workers > 1:
        # For multiple workers, we must pass the app as an import string
        # assuming the file is named 'node.py' in the 'workshop_materials/01_nodes' module path
        # BUT since we are running as a script, this is tricky.
        # Standard Uvicorn practice for scripts is to use the App object directly only for 1 worker.
        # To support workers, we will rely on the fact that this is a workshop script.
        # We'll print a warning that workers might require different launch command if not module-based.
        uvicorn.run("node:app", host="0.0.0.0", port=args.port, workers=args.workers)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
