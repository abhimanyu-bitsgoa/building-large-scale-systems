"""
Replication Lab - Node Server

A node that can operate as either a leader or follower in single-leader replication.
Core architecture is consistent with Lab 1 (Scalability) for student familiarity.

Features:
- Leader mode: Accepts writes, replicates to followers
- Follower mode: Accepts replications from leader
- Configurable replication delay for visualization
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import argparse
import os
import time
import requests
import threading
from typing import List, Optional
import logging

# ========================
# Logging Configuration
# ========================

class EndpointFilter(logging.Filter):
    """Filter to suppress access logs for internal endpoints."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(endpoint in msg for endpoint in ["GET /stats", "GET /health", "GET / "])

# Apply filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# ========================
# Global Configuration
# ========================

NODE_ID = os.environ.get("NODE_ID", "node-1")
NODE_PORT = int(os.environ.get("NODE_PORT", 5001))
NODE_ROLE = os.environ.get("NODE_ROLE", "follower")  # "leader" or "follower"
LEADER_URL = os.environ.get("LEADER_URL", None)
REPLICATION_DELAY = float(os.environ.get("REPLICATION_DELAY", 1.0))

# In-memory data store
data_store = {}
data_versions = {}  # Track versions for conflict resolution

# Metrics
active_requests = 0
total_writes = 0
total_reads = 0
replications_sent = 0
replications_received = 0

# Followers list (only used by leader)
followers: List[str] = []

# ========================
# Pydantic Models
# ========================

class DataPayload(BaseModel):
    key: str
    value: str

class ReplicatePayload(BaseModel):
    key: str
    value: str
    version: int
    source: str  # Source node ID

class AckPayload(BaseModel):
    status: str
    node_id: str
    key: str
    version: int

# ========================
# FastAPI App
# ========================

app = FastAPI(title=f"Replication Lab - {NODE_ID}")

# ========================
# Middleware
# ========================

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Track active requests."""
    global active_requests
    active_requests += 1
    try:
        response = await call_next(request)
        response.headers["X-Node-ID"] = NODE_ID
        response.headers["X-Node-Role"] = NODE_ROLE
        return response
    finally:
        active_requests -= 1

# ========================
# Replication Functions
# ========================

def replicate_to_follower(follower_url: str, key: str, value: str, version: int) -> bool:
    """
    Replicate a write to a follower node.
    Includes configurable delay for visualization.
    """
    global replications_sent
    
    # Artificial delay so students can observe replication
    if REPLICATION_DELAY > 0:
        print(f"[{NODE_ID}] ⏳ Replicating {key} to {follower_url} (delay: {REPLICATION_DELAY}s)...")
        time.sleep(REPLICATION_DELAY)
    
    try:
        resp = requests.post(
            f"{follower_url}/replicate",
            json={"key": key, "value": value, "version": version, "source": NODE_ID},
            timeout=5
        )
        
        if resp.status_code == 200:
            replications_sent += 1
            print(f"[{NODE_ID}] ✅ Replicated {key}={value} (v{version}) to {follower_url}")
            return True
        else:
            print(f"[{NODE_ID}] ❌ Replication to {follower_url} failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[{NODE_ID}] ❌ Replication to {follower_url} failed: {e}")
        return False

def replicate_to_all_followers(key: str, value: str, version: int) -> dict:
    """
    Replicate to all registered followers.
    Returns dict with success/failure counts.
    """
    if not followers:
        return {"success": 0, "failed": 0, "total": 0}
    
    results = {"success": 0, "failed": 0, "total": len(followers), "acks": []}
    
    for follower_url in followers:
        success = replicate_to_follower(follower_url, key, value, version)
        if success:
            results["success"] += 1
            results["acks"].append(follower_url)
        else:
            results["failed"] += 1
    
    return results

# ========================
# API Endpoints
# ========================

@app.get("/")
def home():
    """Root endpoint showing node info."""
    return {
        "node_id": NODE_ID,
        "role": NODE_ROLE,
        "status": "running",
        "port": NODE_PORT
    }

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "node_id": NODE_ID,
        "role": NODE_ROLE,
        "followers": len(followers) if NODE_ROLE == "leader" else None,
        "leader_url": LEADER_URL if NODE_ROLE == "follower" else None
    }

@app.get("/stats")
def stats():
    """Detailed node statistics."""
    return {
        "node_id": NODE_ID,
        "role": NODE_ROLE,
        "active_requests": active_requests,
        "total_writes": total_writes,
        "total_reads": total_reads,
        "replications_sent": replications_sent,
        "replications_received": replications_received,
        "data_count": len(data_store),
        "followers": followers if NODE_ROLE == "leader" else None
    }

@app.post("/data")
def store_data(payload: DataPayload):
    """
    Store a key-value pair.
    - Leader: Stores locally and replicates to followers
    - Follower: Rejects writes (must go through leader)
    """
    global total_writes
    
    if NODE_ROLE == "follower":
        raise HTTPException(
            status_code=403,
            detail=f"Node {NODE_ID} is a follower. Writes must go to leader."
        )
    
    # Leader processing
    current_version = data_versions.get(payload.key, 0)
    new_version = current_version + 1
    
    # Store locally
    data_store[payload.key] = payload.value
    data_versions[payload.key] = new_version
    total_writes += 1
    
    print(f"[{NODE_ID}] 📝 Written {payload.key}={payload.value} (v{new_version})")
    
    # Replicate to followers (synchronous for quorum demonstration)
    replication_result = replicate_to_all_followers(payload.key, payload.value, new_version)
    
    return {
        "status": "stored",
        "node_id": NODE_ID,
        "key": payload.key,
        "value": payload.value,
        "version": new_version,
        "replication": replication_result
    }

@app.get("/data/{key}")
def get_data(key: str):
    """Retrieve a value by key."""
    global total_reads
    
    if key not in data_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found on {NODE_ID}")
    
    total_reads += 1
    return {
        "node_id": NODE_ID,
        "role": NODE_ROLE,
        "key": key,
        "value": data_store[key],
        "version": data_versions.get(key, 1)
    }

@app.get("/data")
def list_data():
    """List all stored data."""
    return {
        "node_id": NODE_ID,
        "role": NODE_ROLE,
        "data": {k: {"value": v, "version": data_versions.get(k, 1)} for k, v in data_store.items()},
        "count": len(data_store)
    }

@app.post("/replicate")
def receive_replication(payload: ReplicatePayload):
    """
    Receive replicated data from leader.
    Only accepts if this node is a follower.
    """
    global replications_received
    
    if NODE_ROLE == "leader":
        raise HTTPException(
            status_code=403,
            detail=f"Node {NODE_ID} is the leader. Cannot receive replications."
        )
    
    current_version = data_versions.get(payload.key, 0)
    
    # Only accept if incoming version is newer
    if payload.version > current_version:
        data_store[payload.key] = payload.value
        data_versions[payload.key] = payload.version
        replications_received += 1
        
        print(f"[{NODE_ID}] 📥 Received replication: {payload.key}={payload.value} (v{payload.version}) from {payload.source}")
        
        return {
            "status": "accepted",
            "node_id": NODE_ID,
            "key": payload.key,
            "version": payload.version
        }
    else:
        print(f"[{NODE_ID}] ⏭️ Skipped stale replication: {payload.key} v{payload.version} (current: v{current_version})")
        return {
            "status": "rejected",
            "reason": "stale_version",
            "node_id": NODE_ID,
            "current_version": current_version
        }

# ========================
# Leader-only endpoints
# ========================

@app.post("/register-follower")
def register_follower(payload: dict):
    """Register a follower node (leader only)."""
    if NODE_ROLE != "leader":
        raise HTTPException(status_code=403, detail="Only leader can register followers")
    
    follower_url = payload.get("url")
    if follower_url and follower_url not in followers:
        followers.append(follower_url)
        print(f"[{NODE_ID}] ✅ Registered follower: {follower_url}")
        return {"status": "registered", "followers": followers}
    
    return {"status": "already_registered", "followers": followers}

@app.get("/followers")
def list_followers():
    """List registered followers (leader only)."""
    if NODE_ROLE != "leader":
        raise HTTPException(status_code=403, detail="Only leader has followers")
    
    return {"leader": NODE_ID, "followers": followers}

# ========================
# Main Entry Point
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replication Lab - Node Server")
    parser.add_argument("--port", type=int, default=5001, help="Port to run the server on")
    parser.add_argument("--id", type=str, default="node-1", help="Node ID")
    parser.add_argument("--role", type=str, default="follower", choices=["leader", "follower"],
                        help="Node role (leader or follower)")
    parser.add_argument("--leader-url", type=str, default=None,
                        help="Leader URL (for followers to know where to redirect)")
    parser.add_argument("--replication-delay", type=float, default=1.0,
                        help="Delay in seconds for replication (for visualization)")
    
    args = parser.parse_args()
    
    # Set globals
    NODE_ID = args.id
    NODE_PORT = args.port
    NODE_ROLE = args.role
    LEADER_URL = args.leader_url
    REPLICATION_DELAY = args.replication_delay
    
    # Set environment variables
    os.environ["NODE_ID"] = args.id
    os.environ["NODE_PORT"] = str(args.port)
    os.environ["NODE_ROLE"] = args.role
    os.environ["REPLICATION_DELAY"] = str(args.replication_delay)
    if args.leader_url:
        os.environ["LEADER_URL"] = args.leader_url
    
    role_emoji = "👑" if NODE_ROLE == "leader" else "📋"
    print(f"{role_emoji} Starting {NODE_ROLE.upper()} node '{NODE_ID}' on port {NODE_PORT}")
    print(f"   Replication delay: {REPLICATION_DELAY}s")
    if NODE_ROLE == "follower" and LEADER_URL:
        print(f"   Leader: {LEADER_URL}")
    
    uvicorn.run(app, host="0.0.0.0", port=NODE_PORT)
