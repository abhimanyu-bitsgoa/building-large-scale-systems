"""
Distributed KV Store Lab - Registry

Service discovery with heartbeats, automatic pruning, and catchup triggering.
Based on patterns from workshop_materials/11_membership/registry.py.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import time
import requests
import argparse
from typing import Dict
from datetime import datetime
import logging

# ========================
# Logging Configuration
# ========================

class EndpointFilter(logging.Filter):
    """Filter to suppress access logs for heartbeats."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "POST /heartbeat" not in msg

# Apply filter to uvicorn access logger
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# ========================
# Configuration
# ========================

HEARTBEAT_TIMEOUT = 5  # seconds before marking node as dead
COORDINATOR_URL = "http://localhost:7000"

# ========================
# Registry State
# ========================

# {node_id: {url, port, role, last_heartbeat, status}}
nodes: Dict[str, dict] = {}
lock = threading.Lock()

app = FastAPI(title="Distributed KV Store - Registry")

# ========================
# Pydantic Models
# ========================

class HeartbeatPayload(BaseModel):
    node_id: str
    port: int
    url: str
    role: str  # "leader" or "follower"

class DeregisterPayload(BaseModel):
    node_id: str

# ========================
# Background Tasks
# ========================

def prune_nodes():
    """Background task to detect dead nodes and trigger catchup for new ones."""
    while True:
        time.sleep(1)
        now = time.time()
        
        with lock:
            for node_id, node in list(nodes.items()):
                elapsed = now - node.get("last_heartbeat", 0)
                
                if node["status"] == "alive" and elapsed > HEARTBEAT_TIMEOUT:
                    print(f"💀 [Registry] Node '{node_id}' missed heartbeat ({elapsed:.1f}s)")
                    nodes[node_id]["status"] = "dead"
                    
                    # Notify coordinator about dead node
                    try:
                        requests.post(
                            f"{COORDINATOR_URL}/node-died",
                            json={"node_id": node_id},
                            timeout=2
                        )
                    except:
                        pass

def trigger_catchup(node_id: str, node_url: str):
    """Trigger catchup for a new follower node."""
    try:
        print(f"📥 [Registry] Triggering catchup for {node_id}")
        resp = requests.post(
            f"{COORDINATOR_URL}/catchup",
            json={"node_id": node_id, "url": node_url},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"✅ [Registry] Catchup triggered for {node_id}")
        else:
            print(f"⚠️ [Registry] Catchup failed for {node_id}: {resp.status_code}")
    except Exception as e:
        print(f"❌ [Registry] Catchup error for {node_id}: {e}")

# Start pruner thread
pruner_thread = threading.Thread(target=prune_nodes, daemon=True)
pruner_thread.start()

# ========================
# API Endpoints
# ========================

@app.get("/")
def root():
    """Registry status."""
    alive = sum(1 for n in nodes.values() if n.get("status") == "alive")
    return {
        "service": "Node Registry",
        "total_nodes": len(nodes),
        "alive_nodes": alive,
        "dead_nodes": len(nodes) - alive
    }

@app.post("/heartbeat")
def receive_heartbeat(payload: HeartbeatPayload):
    """Receive heartbeat from a node."""
    is_new_node = payload.node_id not in nodes
    
    with lock:
        if is_new_node:
            print(f"✅ [Registry] New node '{payload.node_id}' ({payload.role}) at {payload.url}")
        
        nodes[payload.node_id] = {
            "node_id": payload.node_id,
            "url": payload.url,
            "port": payload.port,
            "role": payload.role,
            "last_heartbeat": time.time(),
            "status": "alive"
        }
    
    # Trigger catchup for new followers
    if is_new_node and payload.role == "follower":
        threading.Thread(
            target=trigger_catchup,
            args=(payload.node_id, payload.url),
            daemon=True
        ).start()
    
    # Return list of alive nodes
    with lock:
        alive_nodes = [
            {"node_id": n["node_id"], "url": n["url"], "role": n["role"]}
            for n in nodes.values()
            if n["status"] == "alive"
        ]
    
    return {"status": "ok", "nodes": alive_nodes}

@app.post("/deregister")
def deregister(payload: DeregisterPayload):
    """Deregister a node."""
    with lock:
        if payload.node_id in nodes:
            print(f"👋 [Registry] Node '{payload.node_id}' deregistered")
            del nodes[payload.node_id]
    return {"status": "ok"}

@app.get("/nodes")
def list_nodes():
    """List all registered nodes."""
    with lock:
        return {
            "nodes": [
                {
                    "node_id": n["node_id"],
                    "url": n["url"],
                    "role": n["role"],
                    "status": n["status"],
                    "last_seen_seconds_ago": round(time.time() - n.get("last_heartbeat", time.time()), 1)
                }
                for n in nodes.values()
            ]
        }

@app.get("/alive")
def list_alive_nodes():
    """List only alive nodes."""
    with lock:
        return {
            "nodes": [
                {"node_id": n["node_id"], "url": n["url"], "role": n["role"]}
                for n in nodes.values()
                if n["status"] == "alive"
            ]
        }

# ========================
# Main Entry Point
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed KV Store - Registry")
    parser.add_argument("--port", type=int, default=9000,
                        help="Registry port")
    parser.add_argument("--coordinator", type=str, default="http://localhost:7000",
                        help="Coordinator URL for catchup notifications")
    
    args = parser.parse_args()
    
    COORDINATOR_URL = args.coordinator
    
    print(f"📋 Starting Registry on port {args.port}")
    print(f"   Coordinator: {args.coordinator}")
    print(f"   Heartbeat timeout: {HEARTBEAT_TIMEOUT}s")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)
