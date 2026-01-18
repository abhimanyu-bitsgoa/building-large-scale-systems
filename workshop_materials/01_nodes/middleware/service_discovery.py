"""
Service Discovery Middleware

Implements automatic registration with a service registry,
background heartbeat emission, and peer discovery.

This is a complete implementation - students observe the behavior.
"""

import threading
import time
import requests
from typing import Optional, List, Dict, Any


class ServiceDiscoveryMiddleware:
    """
    ASGI Middleware that handles service registration and heartbeats.
    
    How it works:
    ┌─────────────────────────────────────────────────────────────┐
    │  📝 On startup: Register with the registry                 │
    │  💓 Background: Send heartbeats every N seconds            │
    │  🔍 On demand: Get list of peer nodes from registry        │
    │  👋 On shutdown: Deregister from registry                  │
    └─────────────────────────────────────────────────────────────┘
    
    Usage:
        from middleware import ServiceDiscoveryMiddleware
        sd = ServiceDiscoveryMiddleware(
            app,
            node_id="node-1",
            node_port=5001,
            registry_url="http://localhost:5000"
        )
    """
    
    def __init__(
        self,
        app,
        node_id: str,
        node_port: int,
        registry_url: str = "http://localhost:5000",
        heartbeat_interval: int = 2
    ):
        """
        Initialize service discovery middleware.
        
        Args:
            app: The ASGI application
            node_id: Unique identifier for this node
            node_port: Port this node is running on
            registry_url: URL of the service registry
            heartbeat_interval: Seconds between heartbeats
        """
        self.app = app
        self.node_id = node_id
        self.node_port = node_port
        self.node_address = f"http://localhost:{node_port}"
        self.registry_url = registry_url
        self.heartbeat_interval = heartbeat_interval
        
        # State
        self.running = True
        self.registered = False
        self.peers: List[Dict[str, Any]] = []
        self.last_heartbeat_time: Optional[float] = None
        self.heartbeat_failures = 0
        
        # Start background threads
        self._register()
        self._start_heartbeat_thread()
    
    def _register(self):
        """Register this node with the registry."""
        try:
            resp = requests.post(
                f"{self.registry_url}/register",
                json={
                    "id": self.node_id,
                    "port": self.node_port,
                    "address": self.node_address
                },
                timeout=2
            )
            if resp.status_code == 200:
                self.registered = True
                print(f"✅ [{self.node_id}] Registered with registry at {self.registry_url}")
            else:
                print(f"⚠️ [{self.node_id}] Registration failed: {resp.status_code}")
        except Exception as e:
            print(f"❌ [{self.node_id}] Could not connect to registry: {e}")
    
    def _heartbeat_loop(self):
        """Background thread that sends heartbeats."""
        while self.running:
            try:
                resp = requests.post(
                    f"{self.registry_url}/heartbeat/{self.node_id}",
                    timeout=2
                )
                if resp.status_code == 200:
                    self.last_heartbeat_time = time.time()
                    self.heartbeat_failures = 0
                    
                    # Try to get peer list from registry
                    try:
                        nodes_resp = requests.get(f"{self.registry_url}/nodes", timeout=2)
                        if nodes_resp.status_code == 200:
                            all_nodes = nodes_resp.json()
                            # Filter out self
                            self.peers = [
                                {"node_id": nid, **info}
                                for nid, info in all_nodes.items()
                                if nid != self.node_id
                            ]
                    except:
                        pass
                else:
                    self.heartbeat_failures += 1
            except Exception as e:
                self.heartbeat_failures += 1
                if self.heartbeat_failures > 3:
                    print(f"⚠️ [{self.node_id}] Heartbeat failed (attempt {self.heartbeat_failures})")
            
            time.sleep(self.heartbeat_interval)
    
    def _start_heartbeat_thread(self):
        """Start the background heartbeat thread."""
        thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        thread.start()
    
    def deregister(self):
        """Deregister from the registry (call on shutdown)."""
        self.running = False
        try:
            requests.post(
                f"{self.registry_url}/deregister",
                json={"node_id": self.node_id},
                timeout=2
            )
            print(f"👋 [{self.node_id}] Deregistered from registry")
        except:
            pass
    
    def get_peers(self) -> List[Dict[str, Any]]:
        """Get list of peer nodes (cached from last heartbeat)."""
        return self.peers
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service discovery status."""
        return {
            "node_id": self.node_id,
            "node_address": self.node_address,
            "registry_url": self.registry_url,
            "registered": self.registered,
            "peer_count": len(self.peers),
            "peers": [p.get("node_id") for p in self.peers],
            "last_heartbeat": self.last_heartbeat_time,
            "heartbeat_failures": self.heartbeat_failures
        }
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - passthrough (this middleware doesn't intercept requests)."""
        await self.app(scope, receive, send)


def add_discovery_endpoints(app, middleware: ServiceDiscoveryMiddleware):
    """
    Add service discovery endpoints for visualization.
    
    Endpoints:
    - GET /discovery-status: Current SD state
    - GET /peers: List of peer nodes
    """
    from fastapi import FastAPI
    
    @app.get("/discovery-status")
    def discovery_status():
        return middleware.get_status()
    
    @app.get("/peers")
    def list_peers():
        return {
            "node_id": middleware.node_id,
            "peers": middleware.get_peers(),
            "count": len(middleware.peers)
        }
