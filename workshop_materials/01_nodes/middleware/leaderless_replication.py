"""
Leaderless Replication Middleware (Gossip Protocol)

Implements eventual consistency through gossip-based anti-entropy sync.
All nodes can accept writes, and they eventually converge through gossip.

This is an OBSERVATION module - students watch eventual consistency in action.
"""

import random
import threading
import time
import requests
from typing import List, Dict, Any
from fastapi import FastAPI


class LeaderlessReplicationMiddleware:
    """
    Leaderless Replication using Gossip Protocol
    
    How it works:
    ┌─────────────────────────────────────────────────────────────┐
    │  📡 Every node can accept reads AND writes                 │
    │  🔄 Background thread gossips with random peers            │
    │  📊 Uses version numbers for conflict resolution           │
    │  ⏰ Eventually, all nodes converge to same state           │
    │  ⚠️  Temporarily inconsistent (eventual consistency)       │
    └─────────────────────────────────────────────────────────────┘
    
    Demo to observe:
    1. Start 3 nodes with --leaderless
    2. Write to node 1: curl -X POST localhost:5001/leaderless-write -d '{"key":"x","value":"1"}'
    3. Immediately read from node 2: curl localhost:5002/leaderless-read/x
       → May return null (not yet synced)
    4. Wait 2-3 seconds
    5. Read again from node 2
       → Now returns "1" (gossip synced it)
    
    Usage:
        python node.py --port 5001 --id node-1 --leaderless --peers 5002,5003
    """
    
    def __init__(
        self,
        app,
        node_id: str,
        node_port: int,
        peers: List[int],
        gossip_interval: float = 2.0
    ):
        """
        Initialize leaderless replication middleware.
        
        Args:
            app: FastAPI application
            node_id: This node's ID
            node_port: This node's port
            peers: List of peer ports
            gossip_interval: Seconds between gossip rounds
        """
        self.app = app
        self.node_id = node_id
        self.node_port = node_port
        self.node_address = f"http://localhost:{node_port}"
        
        # Build peer list (excluding self)
        self.peers = [f"http://localhost:{p}" for p in peers if p != node_port]
        self.gossip_interval = gossip_interval
        
        # Data with versions for conflict resolution
        # Format: {key: {"value": ..., "version": ..., "origin": ...}}
        self.versioned_data: Dict[str, Dict[str, Any]] = {}
        
        # Gossip log for visualization
        self.gossip_log: List[Dict[str, Any]] = []
        self.max_log_size = 20
        
        # Stats
        self.stats = {
            "local_writes": 0,
            "gossip_sent": 0,
            "gossip_received": 0,
            "conflicts_resolved": 0
        }
        
        # State
        self.running = True
        
        # Start gossip thread
        self._start_gossip_thread()
    
    def _start_gossip_thread(self):
        """Start background gossip thread."""
        thread = threading.Thread(target=self._gossip_loop, daemon=True)
        thread.start()
        print(f"[{self.node_id}] Gossip thread started (interval: {self.gossip_interval}s)")
    
    def _gossip_loop(self):
        """Background thread that periodically syncs with random peers."""
        while self.running:
            time.sleep(self.gossip_interval)
            
            if not self.peers or not self.versioned_data:
                continue
            
            # Pick a random peer
            peer = random.choice(self.peers)
            
            try:
                # Send our complete state to the peer
                resp = requests.post(
                    f"{peer}/gossip-sync",
                    json={
                        "from_node": self.node_id,
                        "data": self.versioned_data
                    },
                    timeout=2
                )
                
                if resp.status_code == 200:
                    self.stats["gossip_sent"] += 1
                    
                    # Log gossip event
                    self._log_gossip("sent", peer, list(self.versioned_data.keys()))
                    
                    # Merge any newer data from peer's response
                    peer_data = resp.json().get("data", {})
                    self._merge_data(peer_data, f"gossip from {peer}")
                    
            except Exception as e:
                pass  # Peer might be down
    
    def _merge_data(self, incoming_data: Dict[str, Dict], source: str):
        """
        Merge incoming data using "Last Write Wins" (highest version).
        
        This is the core of eventual consistency - when two nodes
        have different values, the one with higher version wins.
        """
        for key, incoming in incoming_data.items():
            incoming_version = incoming.get("version", 0)
            
            if key not in self.versioned_data:
                # Key doesn't exist locally - accept it
                self.versioned_data[key] = incoming
                self.stats["gossip_received"] += 1
            else:
                local_version = self.versioned_data[key].get("version", 0)
                
                if incoming_version > local_version:
                    # Incoming is newer - accept it
                    self.versioned_data[key] = incoming
                    self.stats["gossip_received"] += 1
                    self.stats["conflicts_resolved"] += 1
                    print(f"[{self.node_id}] ← Merged {key} v{incoming_version} from {source}")
    
    def _log_gossip(self, action: str, peer: str, keys: List[str]):
        """Log a gossip event for visualization."""
        event = {
            "time": time.time(),
            "action": action,
            "peer": peer,
            "keys": keys[:5],  # Limit shown keys
            "key_count": len(keys)
        }
        self.gossip_log.append(event)
        if len(self.gossip_log) > self.max_log_size:
            self.gossip_log.pop(0)
    
    def local_write(self, key: str, value: str, data_store: dict) -> dict:
        """
        Write to this node (will eventually propagate via gossip).
        """
        # Increment version
        current = self.versioned_data.get(key, {})
        new_version = current.get("version", 0) + 1
        
        # Store with version info
        self.versioned_data[key] = {
            "value": value,
            "version": new_version,
            "origin": self.node_id,
            "timestamp": time.time()
        }
        
        # Also update main data store for compatibility
        data_store[key] = value
        
        self.stats["local_writes"] += 1
        
        return {
            "status": "written",
            "node": self.node_id,
            "key": key,
            "value": value,
            "version": new_version,
            "note": "Will propagate via gossip"
        }
    
    def local_read(self, key: str) -> dict:
        """
        Read from this node (may be stale!).
        """
        if key not in self.versioned_data:
            return {
                "key": key,
                "value": None,
                "version": 0,
                "node": self.node_id,
                "exists": False
            }
        
        entry = self.versioned_data[key]
        return {
            "key": key,
            "value": entry.get("value"),
            "version": entry.get("version"),
            "origin": entry.get("origin"),
            "node": self.node_id,
            "exists": True,
            "warning": "Value may be stale (eventual consistency)"
        }
    
    def receive_gossip(self, from_node: str, incoming_data: Dict) -> dict:
        """
        Receive gossip from a peer and merge.
        """
        self._merge_data(incoming_data, from_node)
        self._log_gossip("received", from_node, list(incoming_data.keys()))
        
        # Return our data so the sender can merge too (anti-entropy)
        return {
            "status": "merged",
            "node": self.node_id,
            "data": self.versioned_data
        }
    
    def get_state(self) -> dict:
        """Get current gossip state for visualization."""
        return {
            "node_id": self.node_id,
            "peers": self.peers,
            "gossip_interval_sec": self.gossip_interval,
            "data_keys": list(self.versioned_data.keys()),
            "data_count": len(self.versioned_data),
            "stats": self.stats,
            "recent_gossip": self.gossip_log[-5:]
        }
    
    def stop(self):
        """Stop the gossip thread."""
        self.running = False
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - passthrough."""
        await self.app(scope, receive, send)


def add_leaderless_endpoints(app: FastAPI, middleware: LeaderlessReplicationMiddleware, data_store: dict):
    """
    Add leaderless replication endpoints.
    """
    
    @app.get("/gossip-state")
    def gossip_state():
        """Get current gossip/replication state."""
        return middleware.get_state()
    
    @app.get("/gossip-data")
    def gossip_data():
        """Get all versioned data (for debugging)."""
        return {
            "node": middleware.node_id,
            "data": middleware.versioned_data
        }
    
    @app.post("/gossip-sync")
    def gossip_sync(payload: dict):
        """
        Internal endpoint for peer-to-peer gossip.
        """
        from_node = payload.get("from_node", "unknown")
        incoming_data = payload.get("data", {})
        return middleware.receive_gossip(from_node, incoming_data)
    
    @app.post("/leaderless-write")
    def leaderless_write(payload: dict):
        """
        Write to this node (eventually consistent).
        """
        key = payload.get("key")
        value = payload.get("value")
        
        if not key or value is None:
            return {"error": "Missing key or value"}
        
        return middleware.local_write(key, value, data_store)
    
    @app.get("/leaderless-read/{key}")
    def leaderless_read(key: str):
        """
        Read from this node (may be stale).
        """
        return middleware.local_read(key)
