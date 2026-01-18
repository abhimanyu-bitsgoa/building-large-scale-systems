"""
Replication Middleware (Leader-Follower)

Implements single-leader replication where:
- Leader accepts writes and replicates to followers
- Followers accept replicated data and redirect writes to leader

Students implement the replication logic to understand async replication.
"""

import threading
import time
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse


class ReplicationMiddleware:
    """
    Leader-Follower Replication Middleware
    
    How it works:
    ┌─────────────────────────────────────────────────────────────┐
    │  LEADER MODE:                                               │
    │  1. Accept all writes                                       │
    │  2. Store locally                                           │
    │  3. Replicate asynchronously to all followers               │
    ├─────────────────────────────────────────────────────────────┤
    │  FOLLOWER MODE:                                             │
    │  1. Accept reads (may be stale)                             │
    │  2. Redirect writes to leader                               │
    │  3. Accept /replicate calls from leader                     │
    └─────────────────────────────────────────────────────────────┘
    
    Usage:
        # Start leader
        python node.py --port 5001 --id leader --role leader --followers 5002,5003
        
        # Start followers
        python node.py --port 5002 --id follower-1 --role follower --leader 5001
    """
    
    def __init__(
        self,
        app,
        node_id: str,
        node_port: int,
        role: str = "follower",
        leader_port: int = None,
        follower_ports: List[int] = None,
        replication_delay: float = 0.0
    ):
        """
        Initialize replication middleware.
        
        Args:
            app: FastAPI application
            node_id: This node's ID
            node_port: This node's port
            role: "leader" or "follower"
            leader_port: Port of leader (required for followers)
            follower_ports: List of follower ports (required for leader)
            replication_delay: Artificial delay to simulate network lag (seconds)
        """
        self.app = app
        self.node_id = node_id
        self.node_port = node_port
        self.role = role
        self.replication_delay = replication_delay
        
        # Leader configuration
        if role == "leader":
            self.followers = [f"http://localhost:{p}" for p in (follower_ports or [])]
            self.leader_address = f"http://localhost:{node_port}"
        else:
            self.followers = []
            self.leader_address = f"http://localhost:{leader_port}" if leader_port else None
        
        # Stats
        self.replication_stats = {
            "writes_received": 0,
            "replications_sent": 0,
            "replications_received": 0,
            "replication_failures": 0,
            "writes_redirected": 0
        }
        
        # Track replication lag per follower
        self.replication_lag: Dict[str, float] = {}
    
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self.role == "leader"
    
    def replicate_to_followers(self, key: str, value: str, version: int, data_store: dict):
        """
        📝 STUDENT EXERCISE: Implement async replication to followers
        
        This method is called after a write is accepted by the leader.
        You need to send the data to all followers.
        
        ════════════════════════════════════════════════════════════
        TODO: Implement the replication logic
        
        Steps:
        1. Loop through self.followers
        2. For each follower:
           a. Sleep for self.replication_delay (simulates network lag)
           b. POST to {follower}/replicate with JSON:
              {"key": key, "value": value, "version": version}
           c. If successful, increment self.replication_stats["replications_sent"]
           d. If failed, increment self.replication_stats["replication_failures"]
        
        Hints:
        - Use requests.post(url, json=data, timeout=2)
        - Wrap in try/except to handle failures gracefully
        - Use time.sleep() for the artificial delay
        ════════════════════════════════════════════════════════════
        """
        # ─────────────────────────────────────────────────────
        # YOUR CODE HERE
        # ─────────────────────────────────────────────────────
        raise NotImplementedError(
            "Implement the replication logic! "
            "See the docstring above for step-by-step instructions."
        )
    
    def receive_replication(self, key: str, value: str, version: int, data_store: dict) -> dict:
        """
        Receive replicated data from leader (called on followers).
        
        This is the complete implementation - students observe this.
        """
        data_store[key] = value
        self.replication_stats["replications_received"] += 1
        
        return {
            "status": "replicated",
            "node": self.node_id,
            "key": key,
            "version": version
        }
    
    def redirect_to_leader(self, key: str, value: str) -> dict:
        """
        Redirect a write request to the leader (called on followers).
        """
        if not self.leader_address:
            return {"error": "No leader configured"}
        
        try:
            resp = requests.post(
                f"{self.leader_address}/replicated-write",
                json={"key": key, "value": value},
                timeout=5
            )
            self.replication_stats["writes_redirected"] += 1
            result = resp.json()
            result["redirected_from"] = self.node_id
            return result
        except Exception as e:
            return {"error": str(e), "leader": self.leader_address}
    
    def get_status(self) -> dict:
        """Get replication status."""
        return {
            "node_id": self.node_id,
            "role": self.role,
            "leader_address": self.leader_address if self.role == "follower" else "self",
            "followers": self.followers if self.role == "leader" else [],
            "replication_delay_ms": self.replication_delay * 1000,
            "stats": self.replication_stats
        }
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - passthrough."""
        await self.app(scope, receive, send)


def add_replication_endpoints(app: FastAPI, middleware: ReplicationMiddleware, data_store: dict):
    """
    Add replication-aware endpoints.
    """
    
    @app.get("/replication-status")
    def replication_status():
        """Get replication configuration and stats."""
        return middleware.get_status()
    
    @app.post("/replicated-write")
    def replicated_write(payload: dict, background_tasks: BackgroundTasks):
        """
        Write endpoint that handles replication.
        
        Leaders: Store and replicate
        Followers: Redirect to leader
        """
        key = payload.get("key")
        value = payload.get("value")
        
        if not key or value is None:
            return {"error": "Missing key or value"}
        
        if middleware.is_leader():
            # Leader: Store locally and replicate
            version = data_store.get(f"_version:{key}", 0) + 1
            data_store[key] = value
            data_store[f"_version:{key}"] = version
            middleware.replication_stats["writes_received"] += 1
            
            # Async replication
            background_tasks.add_task(
                middleware.replicate_to_followers,
                key, value, version, data_store
            )
            
            return {
                "status": "written",
                "node": middleware.node_id,
                "role": "leader",
                "key": key,
                "version": version,
                "replicating_to": len(middleware.followers)
            }
        else:
            # Follower: Redirect to leader
            return middleware.redirect_to_leader(key, value)
    
    @app.post("/replicate")
    def receive_replicate(payload: dict):
        """
        Endpoint for receiving replicated data from leader.
        (Called by leader on followers)
        """
        key = payload.get("key")
        value = payload.get("value")
        version = payload.get("version", 1)
        
        return middleware.receive_replication(key, value, version, data_store)
    
    @app.get("/replicated-read/{key}")
    def replicated_read(key: str):
        """
        Read from this node (may be stale on followers).
        """
        value = data_store.get(key)
        version = data_store.get(f"_version:{key}", 0)
        
        return {
            "key": key,
            "value": value,
            "version": version,
            "node": middleware.node_id,
            "role": middleware.role,
            "may_be_stale": middleware.role == "follower"
        }
