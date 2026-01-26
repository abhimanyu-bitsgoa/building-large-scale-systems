"""
Replication Lab - Coordinator

Interactive coordinator for single-leader replication with HTTP API and TUI dashboard.

Features:
- Spawns and manages leader + follower nodes
- Write/Read with configurable quorum (W, R)
- W = number of followers that must ack synchronously (leader not counted)
- R = number of followers for read quorum (uses largest port nodes)
- Interactive commands to kill/spawn nodes
- Real-time TUI dashboard showing cluster state and data propagation
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
from typing import Dict, List, Optional, Tuple
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    DIM = "\033[2m"

# ========================
# Configuration
# ========================

BASE_PORT = 6000
NODE_SCRIPT = os.path.join(os.path.dirname(__file__), "node.py")
HEARTBEAT_TIMEOUT = 5  # seconds

# Replication delays
SYNC_REPLICATION_DELAY = 0.5   # Fast for sync nodes
ASYNC_REPLICATION_DELAY = 5.0  # Slow for async nodes (visible lag)

# Dashboard lock to prevent concurrent output
dashboard_lock = threading.Lock()

# ========================
# Cluster State
# ========================

class ClusterState:
    """Manages the state of the replication cluster."""
    
    def __init__(self, write_quorum: int = 2, read_quorum: int = 1):
        self.leader: Optional[dict] = None
        self.followers: Dict[str, dict] = {}  # node_id -> {url, port, status, process, is_sync}
        self.node_counter = 0
        self.write_quorum = write_quorum  # W: number of followers that must ack
        self.read_quorum = read_quorum    # R: number of followers to read from
        self.lock = threading.Lock()
        
        # Cache of node data for dashboard
        self.node_data_cache: Dict[str, Dict] = {}  # node_id -> {key: {value, version}}
    
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
    
    def get_sync_followers(self) -> List[dict]:
        """Get alive sync followers (first W smallest ports)."""
        alive = self.get_alive_followers()
        # Sort by port, take first W
        sorted_by_port = sorted(alive, key=lambda x: x["port"])
        return sorted_by_port[:self.write_quorum]
    
    def get_async_followers(self) -> List[dict]:
        """Get alive async followers (not in sync set)."""
        sync_ids = {f["node_id"] for f in self.get_sync_followers()}
        return [f for f in self.get_alive_followers() if f["node_id"] not in sync_ids]
    
    def get_read_followers(self) -> List[dict]:
        """Get followers for read quorum (largest R ports that are alive)."""
        alive = self.get_alive_followers()
        # Sort by port descending, take first R
        sorted_by_port = sorted(alive, key=lambda x: x["port"], reverse=True)
        return sorted_by_port[:self.read_quorum]
    
    def can_write(self) -> bool:
        """Check if we have enough followers for write quorum."""
        # Need leader alive + W followers
        alive_followers = len(self.get_alive_followers())
        return (self.leader and 
                self.leader.get("status") == "alive" and 
                alive_followers >= self.write_quorum)
    
    def can_read(self) -> bool:
        """Check if we have enough nodes for read quorum."""
        return len(self.get_alive_followers()) >= self.read_quorum
    
    def get_dead_followers(self) -> List[dict]:
        """Get dead followers that can be respawned."""
        return [f for f in self.followers.values() if f.get("status") == "dead"]

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

def fetch_node_data(node: dict) -> Tuple[str, Dict]:
    """Fetch all data from a node."""
    try:
        resp = requests.get(f"{node['url']}/data", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            return node["node_id"], data.get("data", {})
    except:
        pass
    return node["node_id"], {}

def health_check_loop():
    """Background thread to check node health and fetch data."""
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
        
        # Fetch data from all alive nodes for dashboard
        alive_nodes = cluster.get_alive_nodes()
        for node in alive_nodes:
            node_id, data = fetch_node_data(node)
            cluster.node_data_cache[node_id] = data
        
        time.sleep(1)

# ========================
# API Endpoints
# ========================

class WriteRequest(BaseModel):
    key: str
    value: str

@app.get("/")
def root():
    """Get cluster overview."""
    sync_followers = cluster.get_sync_followers()
    async_followers = cluster.get_async_followers()
    read_followers = cluster.get_read_followers()
    
    return {
        "service": "Replication Coordinator",
        "leader": cluster.leader["node_id"] if cluster.leader else None,
        "follower_count": len(cluster.followers),
        "write_quorum": cluster.write_quorum,
        "read_quorum": cluster.read_quorum,
        "sync_followers": [f["node_id"] for f in sync_followers],
        "async_followers": [f["node_id"] for f in async_followers],
        "read_followers": [f["node_id"] for f in read_followers],
        "can_write": cluster.can_write(),
        "can_read": cluster.can_read()
    }

@app.get("/status")
def get_status():
    """Get detailed cluster status."""
    alive_count = len(cluster.get_alive_nodes())
    total_count = len(cluster.get_all_nodes())
    sync_followers = cluster.get_sync_followers()
    async_followers = cluster.get_async_followers()
    read_followers = cluster.get_read_followers()
    
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
                "port": f["port"],
                "status": f["status"],
                "is_sync": f["node_id"] in [s["node_id"] for s in sync_followers],
                "is_read": f["node_id"] in [r["node_id"] for r in read_followers]
            }
            for f in cluster.followers.values()
        ],
        "quorum": {
            "W": cluster.write_quorum,
            "R": cluster.read_quorum,
            "total_alive": alive_count,
            "can_write": cluster.can_write(),
            "can_read": cluster.can_read()
        },
        "sync_followers": [f["node_id"] for f in sync_followers],
        "async_followers": [f["node_id"] for f in async_followers],
        "read_followers": [f["node_id"] for f in read_followers]
    }

@app.get("/data-table")
def get_data_table():
    """Get data from all nodes for visualization."""
    return {
        "nodes": list(cluster.node_data_cache.keys()),
        "data": cluster.node_data_cache
    }

@app.post("/write")
def write_data(request: WriteRequest):
    """
    Write data with quorum.
    Waits for W follower acks before returning success.
    Leader always writes, plus W followers must ack synchronously.
    Remaining followers receive async replication.
    """
    if not cluster.can_write():
        alive = len(cluster.get_alive_followers())
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Write quorum not available",
                "alive_followers": alive,
                "required": cluster.write_quorum,
                "message": f"Need {cluster.write_quorum} followers, only {alive} alive"
            }
        )
    
    sync_followers = cluster.get_sync_followers()
    async_followers = cluster.get_async_followers()
    
    sync_urls = [f["url"] for f in sync_followers]
    async_urls = [f["url"] for f in async_followers]
    
    # Send write to leader with sync/async follower lists
    try:
        resp = requests.post(
            f"{cluster.leader['url']}/data",
            json={
                "key": request.key, 
                "value": request.value,
                "sync_followers": sync_urls,
                "async_followers": async_urls
            },
            timeout=60  # Long timeout for replication
        )
        
        if resp.status_code == 200:
            result = resp.json()
            replication = result.get("replication", {})
            sync_acks = replication.get("sync_acks", 0)
            
            if sync_acks >= cluster.write_quorum:
                return {
                    "status": "success",
                    "key": request.key,
                    "value": request.value,
                    "version": result.get("version"),
                    "sync_acks": sync_acks,
                    "quorum": cluster.write_quorum,
                    "sync_replicated_to": replication.get("sync_acked_by", []),
                    "async_queued": replication.get("async_queued", 0)
                }
            else:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "Write quorum not met",
                        "sync_acks": sync_acks,
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
    Queries ALL nodes, waits for R quorum responses, returns latest version.
    Uses largest R port followers for quorum check.
    """
    if not cluster.can_read():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Read quorum not available",
                "alive_followers": len(cluster.get_alive_followers()),
                "required": cluster.read_quorum
            }
        )
    
    read_followers = cluster.get_read_followers()
    read_follower_ids = {f["node_id"] for f in read_followers}
    
    # Query ALL alive nodes (leader + all followers)
    all_nodes = cluster.get_alive_nodes()
    results = []
    all_responses = []
    
    # Use thread pool to query all nodes in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for node in all_nodes:
            future = executor.submit(
                lambda n: requests.get(f"{n['url']}/data/{key}", timeout=5),
                node
            )
            futures[future] = node
        
        for future in as_completed(futures):
            node = futures[future]
            try:
                resp = future.result()
                if resp.status_code == 200:
                    data = resp.json()
                    response_data = {
                        "node_id": node["node_id"],
                        "value": data.get("value"),
                        "version": data.get("version", 0),
                        "is_quorum_node": node["node_id"] in read_follower_ids or node["node_id"] == "leader"
                    }
                    all_responses.append(response_data)
                    
                    # Only count follower responses for quorum
                    if node["node_id"] in read_follower_ids:
                        results.append(response_data)
                elif resp.status_code == 404:
                    all_responses.append({
                        "node_id": node["node_id"],
                        "value": None,
                        "version": 0,
                        "is_quorum_node": node["node_id"] in read_follower_ids,
                        "error": "not_found"
                    })
            except Exception as e:
                all_responses.append({
                    "node_id": node["node_id"],
                    "error": str(e)
                })
    
    # Check if we have R quorum responses
    if len(results) < cluster.read_quorum:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Read quorum not met",
                "responses": len(results),
                "required": cluster.read_quorum,
                "all_responses": all_responses
            }
        )
    
    # Return the result with highest version (most recent)
    latest = max(results, key=lambda x: x["version"])
    
    return {
        "key": key,
        "value": latest["value"],
        "version": latest["version"],
        "served_by": latest["node_id"],
        "quorum_responses": len(results),
        "required_quorum": cluster.read_quorum,
        "all_node_responses": all_responses
    }

@app.post("/spawn")
def spawn_follower():
    """Spawn a new follower node. Prioritizes respawning dead followers."""
    with cluster.lock:
        # Check for dead followers to respawn first
        dead_followers = cluster.get_dead_followers()
        
        if dead_followers:
            # Respawn the first dead follower
            dead = dead_followers[0]
            node_id = dead["node_id"]
            port = dead["port"]
            url = dead["url"]
            
            # Kill old process if still around
            if dead.get("process"):
                try:
                    dead["process"].terminate()
                except:
                    pass
            
            # Spawn new process
            process = spawn_node(
                node_id=node_id,
                port=port,
                role="follower",
                leader_url=cluster.leader["url"] if cluster.leader else None,
                replication_delay=SYNC_REPLICATION_DELAY  # Will be determined by leader
            )
            
            # Update follower state
            cluster.followers[node_id] = {
                "node_id": node_id,
                "url": url,
                "port": port,
                "status": "starting",
                "process": process
            }
            
            # Register with leader after delay
            def register_delayed():
                time.sleep(2)
                register_follower_with_leader(url)
            
            threading.Thread(target=register_delayed, daemon=True).start()
            
            return {
                "status": "respawned",
                "node_id": node_id,
                "url": url,
                "port": port,
                "was_dead": True
            }
        
        # No dead followers - spawn a new one
        cluster.node_counter += 1
        node_id = f"follower-{cluster.node_counter}"
        port = BASE_PORT + cluster.node_counter + 1
        url = f"http://localhost:{port}"
        
        process = spawn_node(
            node_id=node_id,
            port=port,
            role="follower",
            leader_url=cluster.leader["url"] if cluster.leader else None,
            replication_delay=SYNC_REPLICATION_DELAY
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
        
        return {
            "status": "spawned",
            "node_id": node_id,
            "url": url,
            "port": port,
            "was_dead": False
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
    """Clear terminal screen properly."""
    # Move cursor to home position and clear entire screen
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def draw_dashboard():
    """Draw the TUI dashboard with data table."""
    clear_screen()
    
    print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║           REPLICATION LAB - CLUSTER DASHBOARD                                ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()
    
    sync_followers = cluster.get_sync_followers()
    async_followers = cluster.get_async_followers()
    read_followers = cluster.get_read_followers()
    sync_ids = {f["node_id"] for f in sync_followers}
    read_ids = {f["node_id"] for f in read_followers}
    
    # Quorum status
    can_write = cluster.can_write()
    can_read = cluster.can_read()
    write_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_write else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    read_status = f"{Colors.GREEN}✅ OK{Colors.RESET}" if can_read else f"{Colors.RED}❌ UNAVAILABLE{Colors.RESET}"
    
    print(f"{Colors.BOLD}📊 QUORUM STATUS{Colors.RESET}")
    print(f"   Write Quorum (W={cluster.write_quorum} followers): {write_status}")
    print(f"   Read Quorum  (R={cluster.read_quorum} followers): {read_status}")
    print()
    
    # Leader
    print(f"{Colors.BOLD}👑 LEADER{Colors.RESET}")
    if cluster.leader:
        status_icon = "🟢" if cluster.leader["status"] == "alive" else "🔴"
        print(f"   {status_icon} {cluster.leader['node_id']} @ {cluster.leader['url']}")
    else:
        print(f"   {Colors.RED}No leader{Colors.RESET}")
    print()
    
    # Followers with sync/async/read indicators
    print(f"{Colors.BOLD}📋 FOLLOWERS ({len(cluster.followers)}){Colors.RESET}")
    if cluster.followers:
        sorted_followers = sorted(cluster.followers.values(), key=lambda x: x["port"])
        for follower in sorted_followers:
            node_id = follower["node_id"]
            status_icon = "🟢" if follower["status"] == "alive" else "🔴"
            
            tags = []
            if node_id in sync_ids:
                tags.append(f"{Colors.GREEN}SYNC{Colors.RESET}")
            else:
                tags.append(f"{Colors.YELLOW}ASYNC{Colors.RESET}")
            if node_id in read_ids:
                tags.append(f"{Colors.BLUE}READ{Colors.RESET}")
            
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            print(f"   {status_icon} {node_id} @ {follower['url']} (port {follower['port']}){tag_str}")
    else:
        print(f"   {Colors.YELLOW}No followers registered{Colors.RESET}")
    print()
    
    # Data table
    print(f"{Colors.BOLD}📊 DATA TABLE (Real-time){Colors.RESET}")
    
    # Get all keys across all nodes
    all_keys = set()
    for node_data in cluster.node_data_cache.values():
        all_keys.update(node_data.keys())
    
    if all_keys:
        # Get node order: leader first, then followers by port
        node_order = []
        if cluster.leader and cluster.leader["node_id"] in cluster.node_data_cache:
            node_order.append(cluster.leader["node_id"])
        for f in sorted(cluster.followers.values(), key=lambda x: x["port"]):
            if f["node_id"] in cluster.node_data_cache:
                node_order.append(f["node_id"])
        
        # Header
        header = f"   {'Key':<12}"
        for node_id in node_order:
            short_id = node_id[:10]
            header += f" | {short_id:<12}"
        print(header)
        print("   " + "-" * (len(header) - 3))
        
        # Data rows
        for key in sorted(all_keys):
            row = f"   {key:<12}"
            for node_id in node_order:
                node_data = cluster.node_data_cache.get(node_id, {})
                if key in node_data:
                    val = node_data[key]
                    if isinstance(val, dict):
                        display = f"{val.get('value', '?')[:6]}(v{val.get('version', '?')})"
                    else:
                        display = str(val)[:10]
                else:
                    display = f"{Colors.DIM}---{Colors.RESET}"
                row += f" | {display:<12}"
            print(row)
    else:
        print(f"   {Colors.DIM}No data yet{Colors.RESET}")
    print()
    
    # Commands
    print("-" * 70)
    print(f"{Colors.BOLD}API Endpoints:{Colors.RESET}")
    print(f"   POST http://localhost:{BASE_PORT}/write   - Write data (waits for W follower acks)")
    print(f"   GET  http://localhost:{BASE_PORT}/read/{{key}} - Read data (queries R followers)")
    print(f"   POST http://localhost:{BASE_PORT}/spawn   - Add follower (respawns dead first)")
    print(f"   POST http://localhost:{BASE_PORT}/kill/{{id}} - Kill node")
    print(f"   GET  http://localhost:{BASE_PORT}/status  - Cluster status")
    print()
    print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.RESET}")
    sys.stdout.flush()  # Ensure all output is written

def dashboard_loop():
    """Background loop to refresh dashboard."""
    while True:
        with dashboard_lock:
            draw_dashboard()
        time.sleep(1)

# ========================
# Main Entry Point
# ========================

def start_cluster(num_followers: int, write_quorum: int, read_quorum: int, run_dashboard: bool):
    """Start the replication cluster."""
    
    global cluster
    cluster = ClusterState(write_quorum=write_quorum, read_quorum=read_quorum)
    
    print(f"🚀 Starting Replication Cluster")
    print(f"   Write Quorum: W={write_quorum} (followers must ack)")
    print(f"   Read Quorum:  R={read_quorum} (followers to query)")
    print(f"   Followers: {num_followers}")
    print(f"   Sync delay: {SYNC_REPLICATION_DELAY}s, Async delay: {ASYNC_REPLICATION_DELAY}s")
    print()
    
    # Start leader
    leader_port = BASE_PORT + 1
    leader_url = f"http://localhost:{leader_port}"
    leader_process = spawn_node(
        node_id="leader",
        port=leader_port,
        role="leader",
        replication_delay=SYNC_REPLICATION_DELAY  # Base delay, actual will be per-follower
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
            replication_delay=SYNC_REPLICATION_DELAY
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
    parser.add_argument("--followers", type=int, default=3,
                        help="Number of follower nodes to start")
    parser.add_argument("--write-quorum", "-W", type=int, default=2,
                        help="Write quorum (number of follower acks required)")
    parser.add_argument("--read-quorum", "-R", type=int, default=2,
                        help="Read quorum (number of followers to read from)")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Disable TUI dashboard")
    
    args = parser.parse_args()
    
    try:
        start_cluster(
            num_followers=args.followers,
            write_quorum=args.write_quorum,
            read_quorum=args.read_quorum,
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
