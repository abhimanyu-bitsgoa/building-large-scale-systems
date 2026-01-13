"""
Registry - Central service discovery and cluster management.

Features:
- Heartbeat reception with timeout detection
- Node list management
- Scale-up: spawn new nodes dynamically
- Kill: terminate nodes for chaos testing
- Graduation easter egg
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import subprocess
import threading
import time
import os
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime

app = FastAPI()

# Configuration
HEARTBEAT_TIMEOUT = 5  # seconds before marking node as dead
NODE_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "resilient_node.py")

# State
nodes: Dict[str, dict] = {}  # node_id -> {address, port, last_heartbeat, status, process}
node_counter = 0  # For generating new node IDs
data_store = {}  # For quorum writes via registry
lock = threading.Lock()

class HeartbeatPayload(BaseModel):
    node_id: str
    port: int
    address: str

class DeregisterPayload(BaseModel):
    node_id: str

class DataPayload(BaseModel):
    key: str
    value: str

# ========================
# Heartbeat Management
# ========================

def check_heartbeats():
    """Background thread to check for expired heartbeats."""
    while True:
        current_time = time.time()
        with lock:
            for node_id, node in list(nodes.items()):
                if node.get("status") == "alive":
                    elapsed = current_time - node.get("last_heartbeat", 0)
                    if elapsed > HEARTBEAT_TIMEOUT:
                        print(f"💀 Node '{node_id}' missed heartbeat ({elapsed:.1f}s)")
                        nodes[node_id]["status"] = "dead"
        time.sleep(1)

# Start heartbeat checker
heartbeat_checker = threading.Thread(target=check_heartbeats, daemon=True)
heartbeat_checker.start()

# ========================
# API Endpoints
# ========================

@app.get("/")
def root():
    alive = sum(1 for n in nodes.values() if n.get("status") == "alive")
    return {
        "service": "Cluster Registry",
        "total_nodes": len(nodes),
        "alive_nodes": alive,
        "dead_nodes": len(nodes) - alive
    }

@app.post("/heartbeat")
def receive_heartbeat(payload: HeartbeatPayload):
    """Receive heartbeat from a node."""
    with lock:
        if payload.node_id not in nodes:
            print(f"✅ Node '{payload.node_id}' registered at {payload.address}")
        
        nodes[payload.node_id] = {
            "node_id": payload.node_id,
            "address": payload.address,
            "port": payload.port,
            "last_heartbeat": time.time(),
            "status": "alive",
            "process": nodes.get(payload.node_id, {}).get("process")
        }
        
        # Return list of all alive nodes
        alive_nodes = [
            {"node_id": n["node_id"], "address": n["address"], "port": n["port"]}
            for n in nodes.values()
            if n.get("status") == "alive"
        ]
    
    return {"status": "ok", "nodes": alive_nodes}

@app.post("/deregister")
def deregister(payload: DeregisterPayload):
    """Deregister a node."""
    with lock:
        if payload.node_id in nodes:
            print(f"👋 Node '{payload.node_id}' deregistered")
            del nodes[payload.node_id]
    return {"status": "ok"}

@app.get("/nodes")
def get_nodes():
    """Get all registered nodes."""
    with lock:
        return {
            "nodes": [
                {
                    "node_id": n["node_id"],
                    "address": n["address"],
                    "port": n["port"],
                    "status": n["status"],
                    "last_seen": time.time() - n.get("last_heartbeat", time.time())
                }
                for n in nodes.values()
            ]
        }

@app.get("/cluster-status")
def cluster_status():
    """Get comprehensive cluster status."""
    with lock:
        alive_nodes = [n for n in nodes.values() if n["status"] == "alive"]
        dead_nodes = [n for n in nodes.values() if n["status"] == "dead"]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(nodes),
            "alive_count": len(alive_nodes),
            "dead_count": len(dead_nodes),
            "nodes": [
                {
                    "node_id": n["node_id"],
                    "address": n["address"],
                    "status": n["status"],
                    "last_seen_seconds_ago": round(time.time() - n.get("last_heartbeat", time.time()), 1)
                }
                for n in nodes.values()
            ],
            "health": "healthy" if len(alive_nodes) >= 2 else "degraded" if len(alive_nodes) >= 1 else "critical"
        }

# ========================
# Chaos Engineering
# ========================

@app.post("/kill/{node_id}")
def kill_node(node_id: str):
    """Kill a node for chaos testing."""
    with lock:
        if node_id not in nodes:
            raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
        
        node = nodes[node_id]
        was_terminated = False
        
        # If we spawned this process, kill it
        if node.get("process"):
            try:
                node["process"].terminate()
                was_terminated = True
                print(f"🔫 Terminated spawned node '{node_id}'")
            except:
                pass
        
        # Mark as dead regardless
        nodes[node_id]["status"] = "dead"
        print(f"💀 Node '{node_id}' marked as dead")
    
    if was_terminated:
        return {
            "status": "killed",
            "node_id": node_id,
            "process_terminated": True,
            "message": f"Node '{node_id}' was terminated and marked as dead"
        }
    else:
        return {
            "status": "marked_dead",
            "node_id": node_id,
            "process_terminated": False,
            "message": f"Node '{node_id}' marked as dead. To fully terminate, press Ctrl+C in its terminal.",
            "tip": "Nodes started with scale-up are fully killable. Manually-started nodes need Ctrl+C."
        }

@app.post("/scale-up")
def scale_up():
    """Spawn a new node dynamically."""
    global node_counter
    
    with lock:
        node_counter += 1
        new_id = f"node-{node_counter + 3}"  # Start after node-1, node-2, node-3
        new_port = 5000 + node_counter + 3
        
        # Spawn new node process
        try:
            process = subprocess.Popen(
                [sys.executable, NODE_SCRIPT_PATH, "--port", str(new_port), "--id", new_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Pre-register (will be confirmed by heartbeat)
            nodes[new_id] = {
                "node_id": new_id,
                "address": f"http://localhost:{new_port}",
                "port": new_port,
                "last_heartbeat": time.time(),
                "status": "starting",
                "process": process
            }
            
            print(f"🚀 Spawned new node '{new_id}' on port {new_port}")
            
            return {
                "status": "spawned",
                "node_id": new_id,
                "port": new_port,
                "message": "Node will appear in cluster status within 2-3 seconds"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to spawn node: {e}")

# ========================
# Data Operations (Quorum)
# ========================

import requests as http_client
import hashlib

# Configuration
REPLICATION_FACTOR = 3  # Each key lives on N nodes

def get_hash(key: str) -> int:
    """Get consistent hash for a key (0-999)."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % 1000

def get_replicas_for_key(key: str, alive_nodes: list) -> list:
    """Get the N nodes responsible for this key using consistent hashing."""
    if not alive_nodes:
        return []
    
    # Sort nodes by their hash position
    node_hashes = [(get_hash(n["node_id"]), n) for n in alive_nodes]
    node_hashes.sort(key=lambda x: x[0])
    
    key_hash = get_hash(key)
    
    # Find first node with hash >= key_hash (or wrap around)
    start_idx = 0
    for i, (h, node) in enumerate(node_hashes):
        if h >= key_hash:
            start_idx = i
            break
    
    # Collect REPLICATION_FACTOR nodes starting from start_idx
    n_replicas = min(REPLICATION_FACTOR, len(node_hashes))
    replicas = []
    for i in range(n_replicas):
        idx = (start_idx + i) % len(node_hashes)
        replicas.append(node_hashes[idx][1])
    
    return replicas

@app.post("/data")
def write_data(payload: DataPayload):
    """Write data with dynamic quorum using consistent hashing."""
    with lock:
        alive_nodes = [n for n in nodes.values() if n["status"] == "alive"]
    
    if len(alive_nodes) < 1:
        raise HTTPException(
            status_code=503,
            detail="No nodes available"
        )
    
    # Get replicas for this key using consistent hashing
    replicas = get_replicas_for_key(payload.key, alive_nodes)
    n = len(replicas)  # Actual replication count (might be < REPLICATION_FACTOR)
    w = (n // 2) + 1   # Write quorum = majority
    
    # Write to replica nodes only (not all nodes!)
    successes = []
    failures = []
    
    for node in replicas:
        try:
            resp = http_client.post(
                f"{node['address']}/data",
                json={"key": payload.key, "value": payload.value, "is_replica": False},
                timeout=2
            )
            if resp.status_code == 200:
                successes.append(node["node_id"])
            else:
                failures.append({"node_id": node["node_id"], "error": resp.text})
        except Exception as e:
            failures.append({"node_id": node["node_id"], "error": str(e)})
    
    if len(successes) >= w:
        return {
            "status": "success",
            "quorum_met": True,
            "key": payload.key,
            "N": n,
            "W": w,
            "acks": len(successes),
            "replica_nodes": [r["node_id"] for r in replicas],
            "written_to": successes,
            "message": f"Written to {len(successes)}/{n} replicas (W={w} required). Gossip will propagate to others."
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Quorum not met",
                "N": n,
                "W": w,
                "acks": len(successes),
                "required": w,
                "failures": failures
            }
        )

@app.get("/data/{key}")
def read_data(key: str):
    """Read data from cluster with failover."""
    with lock:
        alive_nodes = [n for n in nodes.values() if n["status"] == "alive"]
    
    if not alive_nodes:
        raise HTTPException(status_code=503, detail="No nodes available")
    
    # Try each node until we get a response
    for node in alive_nodes:
        try:
            resp = http_client.get(f"{node['address']}/data/{key}", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                data["served_by"] = node["node_id"]
                return data
        except:
            continue
    
    raise HTTPException(status_code=404, detail=f"Key '{key}' not found in cluster")

# ========================
# Easter Egg: Graduation
# ========================

GRADUATION_ART = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║       🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓       ║
║                                                                           ║
║      ██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗ █████╗ ████████╗███████╗   ║
║     ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██╔════╝   ║
║     ██║  ███╗██████╔╝███████║██║  ██║██║   ██║███████║   ██║   █████╗     ║
║     ██║   ██║██╔══██╗██╔══██║██║  ██║██║   ██║██╔══██║   ██║   ██╔══╝     ║
║     ╚██████╔╝██║  ██║██║  ██║██████╔╝╚██████╔╝██║  ██║   ██║   ███████╗   ║
║      ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝   ║
║                                                                           ║
║       🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓       ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║     ★ CONGRATULATIONS! YOU ARE NOW A DISTRIBUTED SYSTEMS ENGINEER! ★     ║
║                                                                           ║
║     You have mastered:                                                    ║
║                                                                           ║
║       ✅ Service Discovery & Heartbeats                                   ║
║       ✅ Consistent Hashing & Data Partitioning                           ║
║       ✅ Quorum Reads & Writes                                            ║
║       ✅ Replication & Fault Tolerance                                    ║
║       ✅ Chaos Engineering & Recovery                                     ║
║       ✅ Circuit Breakers & Graceful Degradation                          ║
║                                                                           ║
║     "In distributed systems, everything fails all the time.               ║
║      The difference is whether you designed for it."                      ║
║                                                                           ║
║                              — Werner Vogels, AWS CTO                     ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

    🚀 Now go build systems that survive chaos! 🚀

"""

@app.get("/graduate", response_class=PlainTextResponse)
def graduate():
    """Easter egg: graduation celebration!"""
    return GRADUATION_ART

# ========================
# Main
# ========================

if __name__ == "__main__":
    print("🏛️  Starting Cluster Registry on port 5000")
    print("   Heartbeat timeout: 5 seconds")
    print("   API Endpoints:")
    print("     GET  /nodes         - List all nodes")
    print("     GET  /cluster-status - Detailed cluster health")
    print("     POST /scale-up      - Spawn a new node")
    print("     POST /kill/{id}     - Kill a node (chaos)")
    print("     POST /data          - Write with quorum")
    print("     GET  /data/{key}    - Read with failover")
    print("     GET  /graduate      - 🎓 Easter egg!")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="warning")
