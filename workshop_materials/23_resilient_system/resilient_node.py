"""
Resilient Node - A self-healing distributed node.

Features:
- Heartbeat emission to registry
- Data replication to peers
- Consistent hashing for key distribution
- Graceful shutdown
"""

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import argparse
import requests
import threading
import time
import hashlib
import signal
import sys
import os

app = FastAPI()

# Node configuration
NODE_ID = ""
NODE_PORT = 5001
REGISTRY_URL = "http://localhost:5000"
HEARTBEAT_INTERVAL = 2  # seconds
GOSSIP_INTERVAL = 3     # seconds between gossip rounds
REPLICATION_FACTOR = 2  # Replicate to N-1 peers

# State
data_store = {}
data_versions = {}  # Track versions for conflict resolution
peers = []  # List of peer node URLs
running = True

# Gossip event log (for visualization)
gossip_events = []  # List of {"time": ..., "key": ..., "from": ..., "to": ..., "action": ...}
MAX_GOSSIP_EVENTS = 20

class DataPayload(BaseModel):
    key: str
    value: str
    version: int = 1
    is_replica: bool = False

class ReplicatePayload(BaseModel):
    key: str
    value: str
    version: int
    source_node: str

# ========================
# Heartbeat Thread
# ========================

def heartbeat_loop():
    """Send heartbeats to registry every HEARTBEAT_INTERVAL seconds."""
    global peers, running
    while running:
        try:
            resp = requests.post(
                f"{REGISTRY_URL}/heartbeat",
                json={"node_id": NODE_ID, "port": NODE_PORT, "address": f"http://localhost:{NODE_PORT}"},
                timeout=2
            )
            if resp.status_code == 200:
                # Update peer list from registry
                data = resp.json()
                peers = [p for p in data.get("nodes", []) if p["node_id"] != NODE_ID]
        except Exception as e:
            print(f"[{NODE_ID}] Heartbeat failed: {e}")
        
        time.sleep(HEARTBEAT_INTERVAL)

import random

def gossip_loop():
    """Gossip protocol: periodically sync data with random peers."""
    global running, gossip_events
    while running:
        time.sleep(GOSSIP_INTERVAL)
        
        if not peers or not data_store:
            continue
        
        # Pick a random peer to gossip with
        peer = random.choice(peers)
        
        # Send our data summary to peer (anti-entropy)
        for key, value in list(data_store.items()):
            version = data_versions.get(key, 1)
            try:
                resp = requests.post(
                    f"{peer['address']}/gossip",
                    json={"key": key, "value": value, "version": version, "source_node": NODE_ID},
                    timeout=1
                )
                if resp.status_code == 200:
                    result = resp.json()
                    action = result.get("action", "unknown")
                    
                    # Log gossip event
                    event = {
                        "time": time.time(),
                        "key": key,
                        "from": NODE_ID,
                        "to": peer["node_id"],
                        "action": action,
                        "version": version
                    }
                    gossip_events.append(event)
                    if len(gossip_events) > MAX_GOSSIP_EVENTS:
                        gossip_events.pop(0)
                    
                    if action == "accepted":
                        print(f"[{NODE_ID}] Gossip: {peer['node_id']} accepted {key} (v{version})")
            except:
                pass  # Peer might be down

# ========================
# Consistent Hashing
# ========================

def get_hash(key: str) -> int:
    """Generate a consistent hash for a key."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16)

def get_responsible_nodes(key: str, all_nodes: list, count: int = 2) -> list:
    """Get the nodes responsible for storing this key using consistent hashing."""
    if not all_nodes:
        return []
    
    # Sort nodes by their hash position
    node_hashes = [(get_hash(n["node_id"]), n) for n in all_nodes]
    node_hashes.sort(key=lambda x: x[0])
    
    key_hash = get_hash(key)
    
    # Find the first node with hash >= key_hash (wrap around if needed)
    responsible = []
    start_idx = 0
    for i, (h, node) in enumerate(node_hashes):
        if h >= key_hash:
            start_idx = i
            break
    
    # Collect 'count' nodes starting from start_idx
    for i in range(count):
        idx = (start_idx + i) % len(node_hashes)
        responsible.append(node_hashes[idx][1])
    
    return responsible

# ========================
# Replication
# ========================

def replicate_to_peers(key: str, value: str, version: int):
    """Replicate data to peer nodes asynchronously."""
    all_nodes = [{"node_id": NODE_ID, "address": f"http://localhost:{NODE_PORT}"}] + \
                [{"node_id": p["node_id"], "address": p["address"]} for p in peers]
    
    responsible = get_responsible_nodes(key, all_nodes, REPLICATION_FACTOR + 1)
    
    for node in responsible:
        if node["node_id"] == NODE_ID:
            continue  # Skip self
        try:
            requests.post(
                f"{node['address']}/replicate",
                json={"key": key, "value": value, "version": version, "source_node": NODE_ID},
                timeout=1
            )
            print(f"[{NODE_ID}] Replicated {key} to {node['node_id']}")
        except Exception as e:
            print(f"[{NODE_ID}] Failed to replicate to {node['node_id']}: {e}")

# ========================
# API Endpoints
# ========================

@app.get("/")
def root():
    return {"node_id": NODE_ID, "status": "running", "data_count": len(data_store)}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "node_id": NODE_ID,
        "port": NODE_PORT,
        "peer_count": len(peers),
        "data_count": len(data_store)
    }

@app.post("/data")
def store_data(payload: DataPayload, background_tasks: BackgroundTasks):
    """Store data locally and replicate to peers."""
    current_version = data_versions.get(payload.key, 0)
    new_version = current_version + 1
    
    data_store[payload.key] = payload.value
    data_versions[payload.key] = new_version
    
    print(f"[{NODE_ID}] Stored {payload.key}={payload.value} (v{new_version})")
    
    # Trigger replication in background
    if not payload.is_replica:
        background_tasks.add_task(replicate_to_peers, payload.key, payload.value, new_version)
    
    return {
        "status": "stored",
        "node_id": NODE_ID,
        "key": payload.key,
        "version": new_version
    }

@app.get("/data/{key}")
def get_data(key: str):
    """Retrieve data by key."""
    if key not in data_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found on {NODE_ID}")
    
    return {
        "node_id": NODE_ID,
        "key": key,
        "value": data_store[key],
        "version": data_versions.get(key, 1)
    }

@app.post("/replicate")
def receive_replica(payload: ReplicatePayload):
    """Receive replicated data from another node."""
    current_version = data_versions.get(payload.key, 0)
    
    # Only accept if incoming version is newer
    if payload.version > current_version:
        data_store[payload.key] = payload.value
        data_versions[payload.key] = payload.version
        print(f"[{NODE_ID}] Received replica {payload.key}={payload.value} (v{payload.version}) from {payload.source_node}")
        return {"status": "accepted", "version": payload.version}
    else:
        return {"status": "rejected", "reason": "stale_version", "current_version": current_version}

class GossipPayload(BaseModel):
    key: str
    value: str
    version: int
    source_node: str

@app.post("/gossip")
def receive_gossip(payload: GossipPayload):
    """Receive gossip from another node (anti-entropy sync)."""
    global gossip_events
    current_version = data_versions.get(payload.key, 0)
    
    if payload.version > current_version:
        # Accept newer data
        data_store[payload.key] = payload.value
        data_versions[payload.key] = payload.version
        print(f"[{NODE_ID}] 📨 Gossip received: {payload.key} (v{payload.version}) from {payload.source_node}")
        
        return {"action": "accepted", "version": payload.version}
    elif payload.version == current_version:
        return {"action": "already_synced", "version": current_version}
    else:
        return {"action": "have_newer", "my_version": current_version}

@app.get("/gossip-events")
def get_gossip_events():
    """Get recent gossip events for visualization."""
    return {
        "node_id": NODE_ID,
        "events": gossip_events[-10:],  # Last 10 events
        "total_events": len(gossip_events)
    }

@app.get("/keys")
def list_keys():
    """List all keys stored on this node."""
    return {
        "node_id": NODE_ID,
        "keys": list(data_store.keys()),
        "count": len(data_store)
    }

@app.get("/stats")
def stats():
    """Get detailed node statistics."""
    return {
        "node_id": NODE_ID,
        "port": NODE_PORT,
        "peer_count": len(peers),
        "peers": [p["node_id"] for p in peers],
        "data_count": len(data_store),
        "keys": list(data_store.keys())[:10],  # First 10 keys
        "replication_factor": REPLICATION_FACTOR
    }

# ========================
# Graceful Shutdown
# ========================

def graceful_shutdown(signum, frame):
    """Handle graceful shutdown."""
    global running
    print(f"\n[{NODE_ID}] Shutting down gracefully...")
    running = False
    
    # Deregister from registry
    try:
        requests.post(f"{REGISTRY_URL}/deregister", json={"node_id": NODE_ID}, timeout=2)
        print(f"[{NODE_ID}] Deregistered from registry")
    except:
        pass
    
    sys.exit(0)

# ========================
# Main
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--id", type=str, default="node-1")
    parser.add_argument("--registry", type=str, default="http://localhost:5000")
    args = parser.parse_args()
    
    NODE_ID = args.id
    NODE_PORT = args.port
    REGISTRY_URL = args.registry
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    print(f"🚀 Starting Resilient Node '{NODE_ID}' on port {NODE_PORT}")
    print(f"   Registry: {REGISTRY_URL}")
    print(f"   Replication Factor: {REPLICATION_FACTOR}")
    print(f"   Gossip Interval: {GOSSIP_INTERVAL}s")
    
    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    
    # Start gossip thread (anti-entropy sync)
    gossip_thread = threading.Thread(target=gossip_loop, daemon=True)
    gossip_thread.start()
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=NODE_PORT, log_level="warning")

