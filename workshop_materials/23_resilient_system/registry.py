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
        
        # If we spawned this process, kill it
        if node.get("process"):
            try:
                node["process"].terminate()
                print(f"🔫 Killed spawned node '{node_id}'")
            except:
                pass
        
        # Mark as dead regardless
        nodes[node_id]["status"] = "dead"
        print(f"💀 Node '{node_id}' marked as dead")
    
    return {"status": "killed", "node_id": node_id}

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

@app.post("/data")
def write_data(payload: DataPayload):
    """Write data with quorum (W=2)."""
    with lock:
        alive_nodes = [n for n in nodes.values() if n["status"] == "alive"]
    
    if len(alive_nodes) < 2:
        raise HTTPException(
            status_code=503,
            detail=f"Quorum not available. Need 2 nodes, have {len(alive_nodes)}"
        )
    
    # Write to all alive nodes, count successes
    successes = []
    failures = []
    
    for node in alive_nodes:
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
    
    if len(successes) >= 2:
        return {
            "status": "success",
            "quorum_met": True,
            "acks": len(successes),
            "nodes": successes,
            "key": payload.key
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Quorum not met",
                "acks": len(successes),
                "required": 2,
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
\033[1;33m
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                                                                           ║
    ║       🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓       ║
    ║       🎓                                                           🎓       ║
    ║       🎓   ██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗ █████╗ ████████╗███████╗██╗    ║
    ║       🎓  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║   ██║██╔══██╗╚══██╔══╝██╔════╝██║    ║
    ║       🎓  ██║  ███╗██████╔╝███████║██║  ██║██║   ██║███████║   ██║   █████╗  ██║    ║
    ║       🎓  ██║   ██║██╔══██╗██╔══██║██║  ██║██║   ██║██╔══██║   ██║   ██╔══╝  ╚═╝    ║
    ║       🎓  ╚██████╔╝██║  ██║██║  ██║██████╔╝╚██████╔╝██║  ██║   ██║   ███████╗██╗    ║
    ║       🎓   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝    ║
    ║       🎓                                                           🎓       ║
    ║       🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓🎓       ║
    ║                                                                           ║
    ╠═══════════════════════════════════════════════════════════════════════════╣
    ║                                                                           ║
    ║     \033[1;32m★ CONGRATULATIONS! YOU ARE NOW A DISTRIBUTED SYSTEMS ENGINEER! ★\033[1;33m     ║
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
    ║     \033[1;36m"In distributed systems, everything fails all the time.\033[1;33m             ║
    ║      \033[1;36mThe difference is whether you designed for it."\033[1;33m                    ║
    ║                                                                           ║
    ║                              \033[1;35m— Werner Vogels, AWS CTO\033[1;33m                       ║
    ║                                                                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
\033[0m

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
