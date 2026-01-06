import uvicorn
from fastapi import FastAPI, HTTPException
import time
import argparse

app = FastAPI()

# {resource_name: {"owner": str, "expires": float}}
locks = {}

@app.post("/acquire/{resource}")
def acquire_lock(resource: str, owner: str, ttl: int = 5):
    now = time.time()
    
    # Check if lock exists and is still valid
    if resource in locks:
        lock = locks[resource]
        if now < lock["expires"]:
            if lock["owner"] == owner:
                # Extend lock (Renew)
                locks[resource]["expires"] = now + ttl
                return {"status": "renewed", "expires_in": ttl}
            else:
                return {"status": "denied", "reason": "locked_by_other", "owner": lock["owner"]}
    
    # Grant new lock
    locks[resource] = {"owner": owner, "expires": now + ttl}
    print(f"🔒 Lock GRANTED on '{resource}' to '{owner}'")
    return {"status": "granted", "expires_in": ttl}

@app.post("/release/{resource}")
def release_lock(resource: str, owner: str):
    if resource in locks:
        if locks[resource]["owner"] == owner:
            del locks[resource]
            print(f"🔓 Lock RELEASED on '{resource}' by '{owner}'")
            return {"status": "released"}
    return {"status": "not_held"}

@app.get("/status")
def get_status():
    return locks

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=14000)
    args = parser.parse_args()
    
    print(f"Lock Server starting on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
