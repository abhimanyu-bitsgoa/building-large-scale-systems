"""
Distributed KV Store Lab - Coordinator

Enhanced coordinator with membership management and catchup integration.
Exposes APIs for turning nodes up/down and coordinating catchup.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import threading
import time
import os
import sys
import signal
import requests
from typing import Dict, List, Optional
import argparse

# ========================
# Configuration
# ========================

BASE_PORT = 7000
NODE_SCRIPT = os.path.join(os.path.dirname(__file__), "node.py")
REGISTRY_URL = "http://localhost:9000"
HEARTBEAT_TIMEOUT = 5

# Quorum settings
WRITE_QUORUM = 2
READ_QUORUM = 1

# ========================
# ANSI Colors
# ========================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"

# ========================
# Cluster State
# ========================

class ClusterState:
    def __init__(self, write_quorum: int = 2, read_quorum: int = 1):
        self.leader: Optional[dict] = None
        self.followers: Dict[str, dict] = {}
        self.node_counter = 0
        self.write_quorum = write_quorum
        self.read_quorum = read_quorum
        self.lock = threading.Lock()
    
    def get_all_nodes(self) -> List[dict]:
        nodes = []
        if self.leader:
            nodes.append(self.leader)
        nodes.extend(self.followers.values())
        return nodes
    
    def get_alive_nodes(self) -> List[dict]:
        return [n for n in self.get_all_nodes() if n.get("status") == "alive"]
    
    def get_alive_followers(self) -> List[dict]:
        return [f for f in self.followers.values() if f.get("status") == "alive"]
    
    def can_write(self) -> bool:
        alive_followers = len(self.get_alive_followers())
        return self.leader and self.leader.get("status") == "alive" and (alive_followers + 1) >= self.write_quorum
    
    def can_read(self) -> bool:
        return len(self.get_alive_nodes()) >= self.read_quorum

cluster = ClusterState()
app = FastAPI(title="Distributed KV Store - Coordinator")

# ========================
# Node Management
# ========================

def spawn_node(node_id: str, port: int, role: str, leader_url: str = None,
               registry_url: str = REGISTRY_URL, replication_delay: float = 1.0) -> subprocess.Popen:
    """Spawn a new node process."""
    cmd = [
        sys.executable, NODE_SCRIPT,
        "--port", str(port),
        "--id", node_id,
        "--role", role,
        "--registry", registry_url,
        "--replication-delay", str(replication_delay)
    ]
    if leader_url:
        cmd.extend(["--leader-url", leader_url])
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process

def check_node_health(url: str) -> bool:
    """Check if a node is healthy."""
    try:
        resp = requests.get(f"{url}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False

def health_check_loop():
    """Background health check."""
    while True:
        with cluster.lock:
            if cluster.leader:
                cluster.leader["status"] = "alive" if check_node_health(cluster.leader["url"]) else "dead"
            
            for node_id, follower in cluster.followers.items():
                follower["status"] = "alive" if check_node_health(follower["url"]) else "dead"
        
        time.sleep(2)

def send_catchup_to_follower(follower_url: str, leader_url: str) -> bool:
    """Send leader's data to a new follower."""
    try:
        # Get snapshot from leader
        resp = requests.get(f"{leader_url}/snapshot", timeout=5)
        if resp.status_code != 200:
            return False
        
        snapshot = resp.json()
        
        # Send to follower
        resp = requests.post(
            f"{follower_url}/catchup",
            json={"data": snapshot["data"], "versions": snapshot["versions"]},
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[Coordinator] ❌ Catchup failed: {e}")
        return False

# ========================
# API Models
# ========================

class WriteRequest(BaseModel):
    key: str
    value: str

class NodeRequest(BaseModel):
    node_id: str
    url: Optional[str] = None

# ========================
# API Endpoints
# ========================

@app.get("/")
def root():
    return {
        "service": "Distributed KV Store Coordinator",
        "leader": cluster.leader["node_id"] if cluster.leader else None,
        "follower_count": len(cluster.followers),
        "can_write": cluster.can_write(),
        "can_read": cluster.can_read()
    }

@app.get("/status")
def get_status():
    alive_count = len(cluster.get_alive_nodes())
    
    return {
        "leader": {
            "node_id": cluster.leader["node_id"] if cluster.leader else None,
            "url": cluster.leader["url"] if cluster.leader else None,
            "status": cluster.leader["status"] if cluster.leader else None
        } if cluster.leader else None,
        "followers": [
            {"node_id": f["node_id"], "url": f["url"], "status": f["status"]}
            for f in cluster.followers.values()
        ],
        "quorum": {
            "W": cluster.write_quorum,
            "R": cluster.read_quorum,
            "total_alive": alive_count,
            "can_write": cluster.can_write(),
            "can_read": cluster.can_read()
        }
    }

@app.post("/write")
def write_data(request: WriteRequest):
    """Write with quorum."""
    if not cluster.can_write():
        alive = len(cluster.get_alive_nodes())
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Write quorum not available",
                "alive_nodes": alive,
                "required": cluster.write_quorum
            }
        )
    
    try:
        resp = requests.post(
            f"{cluster.leader['url']}/data",
            json={"key": request.key, "value": request.value},
            timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            replication = result.get("replication", {})
            acks = replication.get("success", 0) + 1
            
            if acks >= cluster.write_quorum:
                return {
                    "status": "success",
                    "key": request.key,
                    "value": request.value,
                    "version": result.get("version"),
                    "acks": acks,
                    "quorum": cluster.write_quorum
                }
            else:
                raise HTTPException(status_code=503, detail={"error": "Write quorum not met", "acks": acks})
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Leader unreachable: {e}")

@app.get("/read/{key}")
def read_data(key: str):
    """Read with quorum."""
    if not cluster.can_read():
        raise HTTPException(status_code=503, detail="Read quorum not available")
    
    results = []
    for node in cluster.get_alive_nodes()[:cluster.read_quorum]:
        try:
            resp = requests.get(f"{node['url']}/data/{key}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results.append({"node_id": node["node_id"], "value": data.get("value"), "version": data.get("version", 1)})
        except:
            pass
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    
    latest = max(results, key=lambda x: x["version"])
    return {
        "key": key,
        "value": latest["value"],
        "version": latest["version"],
        "served_by": latest["node_id"]
    }

@app.post("/turnup")
def turnup_follower():
    """Start a new follower node."""
    with cluster.lock:
        cluster.node_counter += 1
        node_id = f"follower-{cluster.node_counter}"
        port = BASE_PORT + cluster.node_counter + 1
        url = f"http://localhost:{port}"
        
        process = spawn_node(
            node_id=node_id,
            port=port,
            role="follower",
            leader_url=cluster.leader["url"] if cluster.leader else None,
            registry_url=REGISTRY_URL
        )
        
        cluster.followers[node_id] = {
            "node_id": node_id,
            "url": url,
            "port": port,
            "status": "starting",
            "process": process
        }
        
        # Register with leader
        if cluster.leader:
            threading.Thread(
                target=lambda: time.sleep(2) or requests.post(
                    f"{cluster.leader['url']}/register-follower",
                    json={"url": url},
                    timeout=5
                ),
                daemon=True
            ).start()
        
        print(f"[Coordinator] 🚀 Spawned {node_id} on port {port}")
        
        return {"status": "spawned", "node_id": node_id, "url": url}

@app.post("/turndown/{node_id}")
def turndown_follower(node_id: str):
    """Stop a follower node."""
    with cluster.lock:
        if node_id not in cluster.followers:
            raise HTTPException(status_code=404, detail=f"Follower '{node_id}' not found")
        
        follower = cluster.followers[node_id]
        if follower.get("process"):
            follower["process"].terminate()
        
        follower["status"] = "dead"
        print(f"[Coordinator] 💀 Stopped {node_id}")
        
        return {
            "status": "stopped",
            "node_id": node_id,
            "can_write": cluster.can_write()
        }

@app.post("/catchup")
def trigger_catchup(request: NodeRequest):
    """Trigger catchup for a follower (called by registry)."""
    if not cluster.leader:
        raise HTTPException(status_code=503, detail="No leader available")
    
    node_url = request.url
    if not node_url and request.node_id in cluster.followers:
        node_url = cluster.followers[request.node_id]["url"]
    
    if not node_url:
        raise HTTPException(status_code=404, detail=f"Node '{request.node_id}' not found")
    
    success = send_catchup_to_follower(node_url, cluster.leader["url"])
    
    if success:
        print(f"[Coordinator] ✅ Catchup completed for {request.node_id}")
        return {"status": "caught_up", "node_id": request.node_id}
    else:
        raise HTTPException(status_code=500, detail="Catchup failed")

@app.post("/node-died")
def handle_node_died(request: NodeRequest):
    """Handle notification that a node died (from registry)."""
    with cluster.lock:
        if request.node_id in cluster.followers:
            cluster.followers[request.node_id]["status"] = "dead"
            print(f"[Coordinator] 💀 Node {request.node_id} died")
    
    return {"status": "acknowledged"}

# ========================
# TUI Dashboard
# ========================

def clear_screen():
    print("\033[H\033[J", end="")

def draw_dashboard():
    clear_screen()
    
    print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║        DISTRIBUTED KV STORE - CLUSTER DASHBOARD                  ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()
    
    can_write = cluster.can_write()
    can_read = cluster.can_read()
    write_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_write else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    read_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_read else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    
    print(f"{Colors.BOLD}📊 QUORUM (W={cluster.write_quorum}, R={cluster.read_quorum}){Colors.RESET}")
    print(f"   Write: {write_status}  |  Read: {read_status}")
    print()
    
    print(f"{Colors.BOLD}👑 LEADER{Colors.RESET}")
    if cluster.leader:
        icon = "🟢" if cluster.leader["status"] == "alive" else "🔴"
        print(f"   {icon} {cluster.leader['node_id']} @ {cluster.leader['url']}")
    else:
        print(f"   {Colors.RED}No leader{Colors.RESET}")
    print()
    
    print(f"{Colors.BOLD}📋 FOLLOWERS ({len(cluster.followers)}){Colors.RESET}")
    for f in cluster.followers.values():
        icon = "🟢" if f["status"] == "alive" else "🔴"
        print(f"   {icon} {f['node_id']} @ {f['url']}")
    print()
    
    print("-" * 60)
    print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}")

def dashboard_loop():
    while True:
        draw_dashboard()
        time.sleep(1)

# ========================
# Main Entry Point
# ========================

def start_cluster(num_followers: int, write_quorum: int, read_quorum: int,
                  registry_url: str, replication_delay: float, run_dashboard: bool):
    global cluster, REGISTRY_URL
    
    REGISTRY_URL = registry_url
    cluster = ClusterState(write_quorum=write_quorum, read_quorum=read_quorum)
    
    print(f"🚀 Starting Distributed KV Store Cluster")
    print(f"   Registry: {registry_url}")
    print(f"   Quorum: W={write_quorum}, R={read_quorum}")
    print()
    
    # Start leader
    leader_port = BASE_PORT + 1
    leader_url = f"http://localhost:{leader_port}"
    leader_process = spawn_node(
        node_id="leader",
        port=leader_port,
        role="leader",
        registry_url=registry_url,
        replication_delay=replication_delay
    )
    
    cluster.leader = {
        "node_id": "leader",
        "url": leader_url,
        "port": leader_port,
        "status": "starting",
        "process": leader_process
    }
    print(f"👑 Started leader on port {leader_port}")
    
    time.sleep(1)
    
    # Start followers
    for i in range(num_followers):
        cluster.node_counter = i
        port = BASE_PORT + 2 + i
        node_id = f"follower-{i+1}"
        url = f"http://localhost:{port}"
        
        process = spawn_node(
            node_id=node_id,
            port=port,
            role="follower",
            leader_url=leader_url,
            registry_url=registry_url,
            replication_delay=replication_delay
        )
        
        cluster.followers[node_id] = {
            "node_id": node_id,
            "url": url,
            "port": port,
            "status": "starting",
            "process": process
        }
        print(f"📋 Started {node_id} on port {port}")
    
    time.sleep(2)
    
    # Register followers with leader
    for f in cluster.followers.values():
        try:
            requests.post(f"{leader_url}/register-follower", json={"url": f["url"]}, timeout=5)
        except:
            pass
    
    # Start background threads
    threading.Thread(target=health_check_loop, daemon=True).start()
    
    if run_dashboard:
        threading.Thread(target=dashboard_loop, daemon=True).start()
    
    print(f"\n🌐 Coordinator running on http://localhost:{BASE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=BASE_PORT, log_level="warning")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed KV Store - Coordinator")
    parser.add_argument("--followers", type=int, default=2)
    parser.add_argument("--write-quorum", "-W", type=int, default=2)
    parser.add_argument("--read-quorum", "-R", type=int, default=1)
    parser.add_argument("--registry", type=str, default="http://localhost:9000")
    parser.add_argument("--replication-delay", type=float, default=1.0)
    parser.add_argument("--no-dashboard", action="store_true")
    
    args = parser.parse_args()
    
    try:
        start_cluster(
            num_followers=args.followers,
            write_quorum=args.write_quorum,
            read_quorum=args.read_quorum,
            registry_url=args.registry,
            replication_delay=args.replication_delay,
            run_dashboard=not args.no_dashboard
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        if cluster.leader and cluster.leader.get("process"):
            cluster.leader["process"].terminate()
        for f in cluster.followers.values():
            if f.get("process"):
                f["process"].terminate()
