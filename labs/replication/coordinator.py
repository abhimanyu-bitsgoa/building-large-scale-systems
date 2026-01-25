"""
Replication Lab - Coordinator

Interactive coordinator for single-leader replication with HTTP API and TUI dashboard.

Features:
- Spawns and manages leader + follower nodes
- Write/Read with configurable quorum (W, R)
- Interactive commands to kill/spawn nodes
- Real-time TUI dashboard showing cluster state
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
# ANSI Color Codes
# ========================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

# ========================
# Configuration
# ========================

BASE_PORT = 6000
NODE_SCRIPT = os.path.join(os.path.dirname(__file__), "node.py")
HEARTBEAT_TIMEOUT = 5  # seconds

# Quorum settings
WRITE_QUORUM = 2  # W: Number of acks required for write
READ_QUORUM = 1   # R: Number of nodes to read from

# ========================
# Cluster State
# ========================

class ClusterState:
    """Manages the state of the replication cluster."""
    
    def __init__(self, write_quorum: int = 2, read_quorum: int = 1):
        self.leader: Optional[dict] = None
        self.followers: Dict[str, dict] = {}  # node_id -> {url, port, status, process}
        self.node_counter = 0
        self.write_quorum = write_quorum
        self.read_quorum = read_quorum
        self.lock = threading.Lock()
        
        # Data store (for quorum coordination)
        self.data_cache = {}  # key -> {value, version, acked_by}
    
    def get_all_nodes(self) -> List[dict]:
        """Get all nodes (leader + followers)."""
        nodes = []
        if self.leader:
            nodes.append(self.leader)
        nodes.extend(self.followers.values())
        return nodes
    
    def get_alive_nodes(self) -> List[dict]:
        """Get all alive nodes."""
        return [n for n in self.get_all_nodes() if n.get("status") == "alive"]
    
    def get_alive_followers(self) -> List[dict]:
        """Get alive followers."""
        return [f for f in self.followers.values() if f.get("status") == "alive"]
    
    def can_write(self) -> bool:
        """Check if we have enough nodes for write quorum."""
        # Need leader + W-1 followers
        alive_followers = len(self.get_alive_followers())
        return self.leader and self.leader.get("status") == "alive" and (alive_followers + 1) >= self.write_quorum
    
    def can_read(self) -> bool:
        """Check if we have enough nodes for read quorum."""
        return len(self.get_alive_nodes()) >= self.read_quorum

cluster = ClusterState()
app = FastAPI(title="Replication Lab - Coordinator")

# ========================
# Node Management
# ========================

def spawn_node(node_id: str, port: int, role: str, leader_url: str = None, 
               replication_delay: float = 1.0) -> subprocess.Popen:
    """Spawn a new node process."""
    cmd = [
        sys.executable, NODE_SCRIPT,
        "--port", str(port),
        "--id", node_id,
        "--role", role,
        "--replication-delay", str(replication_delay)
    ]
    if leader_url:
        cmd.extend(["--leader-url", leader_url])
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process

def register_follower_with_leader(follower_url: str):
    """Register a follower with the leader."""
    if cluster.leader:
        try:
            resp = requests.post(
                f"{cluster.leader['url']}/register-follower",
                json={"url": follower_url},
                timeout=5
            )
            return resp.status_code == 200
        except:
            return False
    return False

def check_node_health(url: str) -> bool:
    """Check if a node is healthy."""
    try:
        resp = requests.get(f"{url}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False

def health_check_loop():
    """Background thread to check node health."""
    while True:
        with cluster.lock:
            # Check leader
            if cluster.leader:
                if check_node_health(cluster.leader["url"]):
                    cluster.leader["status"] = "alive"
                else:
                    cluster.leader["status"] = "dead"
            
            # Check followers
            for node_id, follower in cluster.followers.items():
                if check_node_health(follower["url"]):
                    follower["status"] = "alive"
                else:
                    follower["status"] = "dead"
        
        time.sleep(2)

# ========================
# API Endpoints
# ========================

class WriteRequest(BaseModel):
    key: str
    value: str

@app.get("/")
def root():
    """Get cluster overview."""
    return {
        "service": "Replication Coordinator",
        "leader": cluster.leader["node_id"] if cluster.leader else None,
        "follower_count": len(cluster.followers),
        "write_quorum": cluster.write_quorum,
        "read_quorum": cluster.read_quorum,
        "can_write": cluster.can_write(),
        "can_read": cluster.can_read()
    }

@app.get("/status")
def get_status():
    """Get detailed cluster status."""
    alive_count = len(cluster.get_alive_nodes())
    total_count = len(cluster.get_all_nodes())
    
    return {
        "leader": {
            "node_id": cluster.leader["node_id"] if cluster.leader else None,
            "url": cluster.leader["url"] if cluster.leader else None,
            "status": cluster.leader["status"] if cluster.leader else None
        } if cluster.leader else None,
        "followers": [
            {
                "node_id": f["node_id"],
                "url": f["url"],
                "status": f["status"]
            }
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
    """
    Write data with quorum.
    Waits for W acks before returning success.
    """
    if not cluster.can_write():
        alive = len(cluster.get_alive_nodes())
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Write quorum not available",
                "alive_nodes": alive,
                "required": cluster.write_quorum,
                "message": f"Need {cluster.write_quorum} nodes, only {alive} alive"
            }
        )
    
    # Send write to leader
    try:
        print(f"[Coordinator] 📝 Writing {request.key}={request.value} to leader...")
        resp = requests.post(
            f"{cluster.leader['url']}/data",
            json={"key": request.key, "value": request.value},
            timeout=30  # Long timeout for replication delay
        )
        
        if resp.status_code == 200:
            result = resp.json()
            replication = result.get("replication", {})
            acks = replication.get("success", 0) + 1  # +1 for leader
            
            if acks >= cluster.write_quorum:
                print(f"[Coordinator] ✅ Write successful: {acks} acks (W={cluster.write_quorum})")
                return {
                    "status": "success",
                    "key": request.key,
                    "value": request.value,
                    "version": result.get("version"),
                    "acks": acks,
                    "quorum": cluster.write_quorum,
                    "replicated_to": replication.get("acks", [])
                }
            else:
                print(f"[Coordinator] ⚠️ Write quorum not met: {acks} < {cluster.write_quorum}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "Write quorum not met",
                        "acks": acks,
                        "required": cluster.write_quorum
                    }
                )
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Leader unreachable: {e}")

@app.get("/read/{key}")
def read_data(key: str):
    """
    Read data with quorum.
    Reads from R nodes and returns the latest version.
    """
    if not cluster.can_read():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Read quorum not available",
                "alive_nodes": len(cluster.get_alive_nodes()),
                "required": cluster.read_quorum
            }
        )
    
    # Read from alive nodes
    results = []
    for node in cluster.get_alive_nodes()[:cluster.read_quorum]:
        try:
            resp = requests.get(f"{node['url']}/data/{key}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results.append({
                    "node_id": node["node_id"],
                    "value": data.get("value"),
                    "version": data.get("version", 1)
                })
        except:
            pass
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    
    # Return the result with highest version (most recent)
    latest = max(results, key=lambda x: x["version"])
    
    return {
        "key": key,
        "value": latest["value"],
        "version": latest["version"],
        "served_by": latest["node_id"],
        "quorum_responses": len(results)
    }

@app.post("/spawn")
def spawn_follower():
    """Spawn a new follower node."""
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
            replication_delay=1.0
        )
        
        cluster.followers[node_id] = {
            "node_id": node_id,
            "url": url,
            "port": port,
            "status": "starting",
            "process": process
        }
        
        # Register with leader after a delay
        def register_delayed():
            time.sleep(2)  # Wait for node to start
            register_follower_with_leader(url)
        
        threading.Thread(target=register_delayed, daemon=True).start()
        
        print(f"[Coordinator] 🚀 Spawned follower: {node_id} on port {port}")
        
        return {
            "status": "spawned",
            "node_id": node_id,
            "url": url,
            "port": port
        }

@app.post("/kill/{node_id}")
def kill_node(node_id: str):
    """Kill a follower node."""
    with cluster.lock:
        if node_id not in cluster.followers:
            raise HTTPException(status_code=404, detail=f"Follower '{node_id}' not found")
        
        follower = cluster.followers[node_id]
        process = follower.get("process")
        
        if process:
            try:
                process.terminate()
                print(f"[Coordinator] 💀 Killed {node_id}")
            except:
                pass
        
        follower["status"] = "dead"
        
        return {
            "status": "killed",
            "node_id": node_id,
            "can_write": cluster.can_write(),
            "can_read": cluster.can_read()
        }

# ========================
# TUI Dashboard
# ========================

def clear_screen():
    """Clear terminal screen."""
    print("\033[H\033[J", end="")

def draw_dashboard():
    """Draw the TUI dashboard."""
    clear_screen()
    
    print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║           REPLICATION LAB - CLUSTER DASHBOARD                    ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()
    
    # Quorum status
    can_write = cluster.can_write()
    can_read = cluster.can_read()
    write_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_write else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    read_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_read else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    
    print(f"{Colors.BOLD}📊 QUORUM STATUS{Colors.RESET}")
    print(f"   Write Quorum (W={cluster.write_quorum}): {write_status}")
    print(f"   Read Quorum  (R={cluster.read_quorum}): {read_status}")
    print()
    
    # Leader
    print(f"{Colors.BOLD}👑 LEADER{Colors.RESET}")
    if cluster.leader:
        status_icon = "🟢" if cluster.leader["status"] == "alive" else "🔴"
        print(f"   {status_icon} {cluster.leader['node_id']} @ {cluster.leader['url']}")
    else:
        print(f"   {Colors.RED}No leader{Colors.RESET}")
    print()
    
    # Followers
    print(f"{Colors.BOLD}📋 FOLLOWERS ({len(cluster.followers)}){Colors.RESET}")
    if cluster.followers:
        for node_id, follower in cluster.followers.items():
            status_icon = "🟢" if follower["status"] == "alive" else "🔴"
            print(f"   {status_icon} {node_id} @ {follower['url']}")
    else:
        print(f"   {Colors.YELLOW}No followers registered{Colors.RESET}")
    print()
    
    # Commands
    print("-" * 60)
    print(f"{Colors.BOLD}API Endpoints:{Colors.RESET}")
    print(f"   POST http://localhost:{BASE_PORT}/write   - Write data")
    print(f"   GET  http://localhost:{BASE_PORT}/read/{{key}} - Read data")
    print(f"   POST http://localhost:{BASE_PORT}/spawn   - Add follower")
    print(f"   POST http://localhost:{BASE_PORT}/kill/{{id}} - Kill node")
    print(f"   GET  http://localhost:{BASE_PORT}/status  - Cluster status")
    print()
    print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}")

def dashboard_loop():
    """Background loop to refresh dashboard."""
    while True:
        draw_dashboard()
        time.sleep(1)

# ========================
# Main Entry Point
# ========================

def start_cluster(num_followers: int, write_quorum: int, read_quorum: int, 
                  replication_delay: float, run_dashboard: bool):
    """Start the replication cluster."""
    
    global cluster
    cluster = ClusterState(write_quorum=write_quorum, read_quorum=read_quorum)
    
    print(f"🚀 Starting Replication Cluster")
    print(f"   Write Quorum: W={write_quorum}")
    print(f"   Read Quorum:  R={read_quorum}")
    print(f"   Followers: {num_followers}")
    print()
    
    # Start leader
    leader_port = BASE_PORT + 1
    leader_url = f"http://localhost:{leader_port}"
    leader_process = spawn_node(
        node_id="leader",
        port=leader_port,
        role="leader",
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
    
    # Wait for leader to start
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
    
    # Wait for nodes to start
    time.sleep(2)
    
    # Register followers with leader
    for node_id, follower in cluster.followers.items():
        register_follower_with_leader(follower["url"])
    
    # Start health check thread
    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()
    
    # Start dashboard thread if requested
    if run_dashboard:
        dashboard_thread = threading.Thread(target=dashboard_loop, daemon=True)
        dashboard_thread.start()
    
    print()
    print(f"🌐 Coordinator API running on http://localhost:{BASE_PORT}")
    print()
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=BASE_PORT, log_level="warning")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replication Lab - Coordinator")
    parser.add_argument("--followers", type=int, default=2,
                        help="Number of follower nodes to start")
    parser.add_argument("--write-quorum", "-W", type=int, default=2,
                        help="Write quorum (acks required for write)")
    parser.add_argument("--read-quorum", "-R", type=int, default=1,
                        help="Read quorum (nodes to read from)")
    parser.add_argument("--replication-delay", type=float, default=1.0,
                        help="Replication delay in seconds (for visualization)")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Disable TUI dashboard")
    
    args = parser.parse_args()
    
    try:
        start_cluster(
            num_followers=args.followers,
            write_quorum=args.write_quorum,
            read_quorum=args.read_quorum,
            replication_delay=args.replication_delay,
            run_dashboard=not args.no_dashboard
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down cluster...")
        
        # Kill all spawned processes
        if cluster.leader and cluster.leader.get("process"):
            cluster.leader["process"].terminate()
        for follower in cluster.followers.values():
            if follower.get("process"):
                follower["process"].terminate()
        
        print("Goodbye!")
