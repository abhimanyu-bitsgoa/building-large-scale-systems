"""
Replication Lab - Coordinator

Coordinator for single-leader replication with HTTP API and event-based logging.

Features:
- Spawns and manages leader + follower nodes
- Write/Read with configurable quorum (W, R)
- W = number of followers that must ack synchronously (leader not counted)
- R = number of followers for read quorum (uses largest port nodes)
- Interactive commands to kill/spawn nodes
- Event-based console logging showing cluster state and data propagation
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import threading
import time
import os
import sys
import requests
from typing import Dict, List, Optional, Tuple
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ========================
# Event Logger
# ========================

class EventLogger:
    """Simple event logger with timestamps for cross-platform compatibility."""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def log(self, icon: str, message: str, details: List[str] = None, indent: int = 0):
        """Log an event with optional details."""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = "    " * indent
            print(f"[{timestamp}] {prefix}{icon} {message}")
            if details:
                for detail in details:
                    print(f"           {prefix}   {detail}")
            sys.stdout.flush()
    
    def log_separator(self):
        """Print a visual separator."""
        with self.lock:
            print("-" * 70)
            sys.stdout.flush()

logger = EventLogger()

# ========================
# Configuration
# ========================

BASE_PORT = 6000
NODE_SCRIPT = os.path.join(os.path.dirname(__file__), "node.py")
HEARTBEAT_TIMEOUT = 5  # seconds

# Replication delays
SYNC_REPLICATION_DELAY = 0.5   # Fast for sync nodes
ASYNC_REPLICATION_DELAY = 5.0  # Slow for async nodes (visible lag)

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
        
        # Track previous status for change detection
        self.previous_status: Dict[str, str] = {}
    
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
    """Background thread to check node health and log status changes."""
    while True:
        with cluster.lock:
            # Check leader
            if cluster.leader:
                node_id = cluster.leader["node_id"]
                old_status = cluster.previous_status.get(node_id)
                new_status = "alive" if check_node_health(cluster.leader["url"]) else "dead"
                cluster.leader["status"] = new_status
                
                if old_status and old_status != new_status:
                    if new_status == "dead":
                        logger.log("🔴", f"LEADER DOWN: {node_id} is no longer responding")
                    else:
                        logger.log("🟢", f"LEADER RECOVERED: {node_id} is back online")
                cluster.previous_status[node_id] = new_status
            
            # Check followers
            for node_id, follower in cluster.followers.items():
                old_status = cluster.previous_status.get(node_id)
                new_status = "alive" if check_node_health(follower["url"]) else "dead"
                follower["status"] = new_status
                
                if old_status and old_status != new_status:
                    sync_followers = cluster.get_sync_followers()
                    sync_ids = {f["node_id"] for f in sync_followers}
                    role_tag = "SYNC" if node_id in sync_ids else "ASYNC"
                    
                    if new_status == "dead":
                        logger.log("🔴", f"NODE DOWN: {node_id} [{role_tag}]")
                        # Log quorum impact
                        if not cluster.can_write():
                            logger.log("⚠️", f"WRITE QUORUM LOST: Only {len(cluster.get_alive_followers())} followers alive, need {cluster.write_quorum}")
                    else:
                        logger.log("🟢", f"NODE RECOVERED: {node_id} [{role_tag}]")
                
                cluster.previous_status[node_id] = new_status
        
        # Fetch data from all alive nodes (for status endpoint)
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
    logger.log_separator()
    logger.log("✍️", f"WRITE REQUEST: key=\"{request.key}\" value=\"{request.value}\"")
    
    if not cluster.can_write():
        alive = len(cluster.get_alive_followers())
        logger.log("❌", f"WRITE REJECTED: Quorum unavailable ({alive}/{cluster.write_quorum} followers)")
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
    
    logger.log("→", f"Sending to leader ({cluster.leader['node_id']})")
    logger.log("→", f"Sync followers: {[f['node_id'] for f in sync_followers]}")
    if async_followers:
        logger.log("→", f"Async followers: {[f['node_id'] for f in async_followers]}")
    
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
            sync_acked_by = replication.get("sync_acked_by", [])
            
            # Log leader write
            logger.log("✅", f"Leader: written (v{result.get('version')})")
            
            # Log sync acks
            for node_url in sync_acked_by:
                # Find node_id from URL
                node_id = "unknown"
                for f in sync_followers:
                    if f["url"] == node_url:
                        node_id = f["node_id"]
                        break
                logger.log("✅", f"{node_id}: sync ack received")
            
            if sync_acks >= cluster.write_quorum:
                logger.log("✅", f"QUORUM MET: {sync_acks}/{cluster.write_quorum} sync acks")
                
                if async_followers:
                    logger.log("🔄", f"Async replication queued for {len(async_followers)} followers")
                    
                    # Start a background thread to log when async replication is expected to complete
                    def log_async_completion(follower_ids: List[str]):
                        # Wait for delay + small buffer for network/processing
                        time.sleep(ASYNC_REPLICATION_DELAY + 0.5)
                        logger.log("✅", f"ASYNC REPLICATION COMPLETE: Replicated to {follower_ids}")
                    
                    async_ids = [f["node_id"] for f in async_followers]
                    threading.Thread(target=log_async_completion, args=(async_ids,), daemon=True).start()
                
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
                logger.log("❌", f"QUORUM FAILED: Only {sync_acks}/{cluster.write_quorum} acks")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "Write quorum not met",
                        "sync_acks": sync_acks,
                        "required": cluster.write_quorum
                    }
                )
        else:
            logger.log("❌", f"Leader error: {resp.status_code}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    
    except requests.exceptions.RequestException as e:
        logger.log("❌", f"Leader unreachable: {e}")
        raise HTTPException(status_code=503, detail=f"Leader unreachable: {e}")

@app.get("/read/{key}")
def read_data(key: str):
    """
    Read data with quorum.
    Queries ALL nodes, waits for R quorum responses, returns latest version.
    Uses largest R port followers for quorum check.
    """
    logger.log_separator()
    logger.log("📖", f"READ REQUEST: key=\"{key}\"")
    
    if not cluster.can_read():
        logger.log("❌", f"READ REJECTED: Quorum unavailable")
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
    
    logger.log("→", f"Querying all nodes (quorum nodes: {list(read_follower_ids)})")
    
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
                    
                    # Log response
                    quorum_marker = "[QUORUM]" if response_data["is_quorum_node"] else ""
                    logger.log("←", f"{node['node_id']}: v{data.get('version', 0)} \"{data.get('value', 'null')}\" {quorum_marker}")
                    
                    # Only count follower responses for quorum
                    if node["node_id"] in read_follower_ids:
                        results.append(response_data)
                elif resp.status_code == 404:
                    logger.log("←", f"{node['node_id']}: NOT FOUND")
                    all_responses.append({
                        "node_id": node["node_id"],
                        "value": None,
                        "version": 0,
                        "is_quorum_node": node["node_id"] in read_follower_ids,
                        "error": "not_found"
                    })
            except Exception as e:
                logger.log("←", f"{node['node_id']}: ERROR ({str(e)[:30]})")
                all_responses.append({
                    "node_id": node["node_id"],
                    "error": str(e)
                })
    
    # Check if we have R quorum responses
    if len(results) < cluster.read_quorum:
        logger.log("❌", f"QUORUM FAILED: Only {len(results)}/{cluster.read_quorum} responses")
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
    
    logger.log("✅", f"RESULT: v{latest['version']} \"{latest['value']}\" (from {latest['node_id']})")
    
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
    logger.log_separator()
    
    with cluster.lock:
        # Check for dead followers to respawn first
        dead_followers = cluster.get_dead_followers()
        
        if dead_followers:
            # Respawn the first dead follower
            dead = dead_followers[0]
            node_id = dead["node_id"]
            port = dead["port"]
            url = dead["url"]
            
            logger.log("🔄", f"RESPAWNING: {node_id} (was dead)")
            
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
                if register_follower_with_leader(url):
                    logger.log("✅", f"REGISTERED: {node_id} with leader")
                else:
                    logger.log("⚠️", f"REGISTRATION FAILED: {node_id}")
            
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
        
        logger.log("➕", f"SPAWNING NEW: {node_id} on port {port}")
        
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
            if register_follower_with_leader(url):
                logger.log("✅", f"REGISTERED: {node_id} with leader")
            else:
                logger.log("⚠️", f"REGISTRATION FAILED: {node_id}")
        
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
    logger.log_separator()
    
    with cluster.lock:
        if node_id not in cluster.followers:
            logger.log("❌", f"KILL FAILED: {node_id} not found")
            raise HTTPException(status_code=404, detail=f"Follower '{node_id}' not found")
        
        follower = cluster.followers[node_id]
        process = follower.get("process")
        
        # Determine role
        sync_ids = {f["node_id"] for f in cluster.get_sync_followers()}
        role_tag = "SYNC" if node_id in sync_ids else "ASYNC"
        
        logger.log("💀", f"KILLING: {node_id} [{role_tag}]")
        
        if process:
            try:
                process.terminate()
            except:
                pass
        
        follower["status"] = "dead"
        cluster.previous_status[node_id] = "dead"
        
        # Log quorum impact
        can_write = cluster.can_write()
        can_read = cluster.can_read()
        
        if not can_write:
            logger.log("⚠️", f"WRITE QUORUM LOST: Only {len(cluster.get_alive_followers())} followers alive, need {cluster.write_quorum}")
        if not can_read:
            logger.log("⚠️", f"READ QUORUM LOST: Only {len(cluster.get_alive_followers())} followers alive, need {cluster.read_quorum}")
        
        return {
            "status": "killed",
            "node_id": node_id,
            "can_write": can_write,
            "can_read": can_read
        }

# ========================
# Main Entry Point
# ========================

def print_banner():
    """Print startup banner."""
    print()
    print("=" * 70)
    print("          REPLICATION LAB - CLUSTER COORDINATOR")
    print("=" * 70)
    print()

def start_cluster(num_followers: int, write_quorum: int, read_quorum: int):
    """Start the replication cluster."""
    
    global cluster
    cluster = ClusterState(write_quorum=write_quorum, read_quorum=read_quorum)
    
    print_banner()
    
    logger.log("🚀", "STARTING CLUSTER", [
        f"Write Quorum: W={write_quorum} (followers must ack)",
        f"Read Quorum: R={read_quorum} (followers to query)",
        f"Followers: {num_followers}",
        f"Sync delay: {SYNC_REPLICATION_DELAY}s, Async delay: {ASYNC_REPLICATION_DELAY}s"
    ])
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
    logger.log("👑", f"Leader started on port {leader_port}")
    
    # Wait for leader to start
    time.sleep(1)
    
    # Start followers
    for i in range(num_followers):
        cluster.node_counter = i + 1
        port = BASE_PORT + 2 + i
        node_id = f"follower-{i+1}"
        url = f"http://localhost:{port}"
        
        # Determine if sync or async based on position
        is_sync = i < write_quorum
        role_tag = "SYNC" if is_sync else "ASYNC"
        
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
        logger.log("📋", f"{node_id} started on port {port} [{role_tag}]")
    
    # Wait for nodes to start
    time.sleep(2)
    
    # Register followers with leader
    for node_id, follower in cluster.followers.items():
        register_follower_with_leader(follower["url"])
    
    # Initialize previous status for all nodes
    cluster.previous_status["leader"] = "alive"
    for node_id in cluster.followers:
        cluster.previous_status[node_id] = "alive"
    
    # Start health check thread
    health_thread = threading.Thread(target=health_check_loop, daemon=True)
    health_thread.start()
    
    print()
    logger.log_separator()
    logger.log("🌐", f"Coordinator API running on http://localhost:{BASE_PORT}")
    print()
    print("API Endpoints:")
    print(f"  POST http://localhost:{BASE_PORT}/write        - Write data (waits for W acks)")
    print(f"  GET  http://localhost:{BASE_PORT}/read/{{key}}    - Read data (queries R followers)")
    print(f"  POST http://localhost:{BASE_PORT}/spawn        - Add follower")
    print(f"  POST http://localhost:{BASE_PORT}/kill/{{id}}     - Kill node")
    print(f"  GET  http://localhost:{BASE_PORT}/status       - Cluster status")
    print()
    logger.log_separator()
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
    
    args = parser.parse_args()
    
    try:
        start_cluster(
            num_followers=args.followers,
            write_quorum=args.write_quorum,
            read_quorum=args.read_quorum
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
