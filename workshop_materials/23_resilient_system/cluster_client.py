"""
Smart Cluster Client - Resilient client with automatic failover.

Features:
- Service discovery from registry
- Consistent hashing for routing
- Quorum writes (W=2)
- Automatic failover on node failure
- Retry with exponential backoff and jitter
"""

import requests
import time
import random
import hashlib
import argparse
from typing import List, Optional, Tuple

class ClusterClient:
    def __init__(self, registry_url: str = "http://localhost:5000"):
        self.registry_url = registry_url
        self.nodes = []
        self.last_refresh = 0
        self.refresh_interval = 5  # seconds
        
        # Circuit breaker state per node
        self.circuit_breakers = {}  # node_id -> {"failures": int, "last_failure": float, "state": str}
        self.failure_threshold = 3
        self.recovery_timeout = 10  # seconds
    
    def _refresh_nodes(self):
        """Refresh node list from registry."""
        try:
            resp = requests.get(f"{self.registry_url}/nodes", timeout=2)
            if resp.status_code == 200:
                all_nodes = resp.json().get("nodes", [])
                self.nodes = [n for n in all_nodes if n.get("status") == "alive"]
                self.last_refresh = time.time()
                return True
        except Exception as e:
            print(f"⚠️  Failed to refresh nodes: {e}")
        return False
    
    def _ensure_fresh_nodes(self):
        """Ensure we have a recent node list."""
        if time.time() - self.last_refresh > self.refresh_interval:
            self._refresh_nodes()
    
    def _get_circuit_state(self, node_id: str) -> str:
        """Get circuit breaker state for a node."""
        if node_id not in self.circuit_breakers:
            return "CLOSED"
        
        cb = self.circuit_breakers[node_id]
        
        if cb["state"] == "OPEN":
            # Check if we should try half-open
            if time.time() - cb["last_failure"] > self.recovery_timeout:
                cb["state"] = "HALF_OPEN"
                return "HALF_OPEN"
            return "OPEN"
        
        return cb["state"]
    
    def _record_success(self, node_id: str):
        """Record a successful request."""
        if node_id in self.circuit_breakers:
            self.circuit_breakers[node_id] = {
                "failures": 0,
                "last_failure": 0,
                "state": "CLOSED"
            }
    
    def _record_failure(self, node_id: str):
        """Record a failed request."""
        if node_id not in self.circuit_breakers:
            self.circuit_breakers[node_id] = {"failures": 0, "last_failure": 0, "state": "CLOSED"}
        
        cb = self.circuit_breakers[node_id]
        cb["failures"] += 1
        cb["last_failure"] = time.time()
        
        if cb["failures"] >= self.failure_threshold:
            cb["state"] = "OPEN"
            print(f"🔴 Circuit OPEN for {node_id} (too many failures)")
    
    def _get_hash(self, key: str) -> int:
        """Consistent hash for a key."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def _get_preferred_nodes(self, key: str, count: int = 3) -> List[dict]:
        """Get preferred nodes for a key using consistent hashing."""
        self._ensure_fresh_nodes()
        
        if not self.nodes:
            return []
        
        # Sort nodes by their hash distance from key
        key_hash = self._get_hash(key)
        sorted_nodes = sorted(
            self.nodes,
            key=lambda n: (self._get_hash(n["node_id"]) - key_hash) % (2**128)
        )
        
        return sorted_nodes[:count]
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        node_id: str,
        max_retries: int = 3,
        **kwargs
    ) -> Tuple[Optional[requests.Response], bool]:
        """Make a request with exponential backoff and jitter."""
        
        # Check circuit breaker
        state = self._get_circuit_state(node_id)
        if state == "OPEN":
            return None, False
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    resp = requests.get(url, timeout=2, **kwargs)
                else:
                    resp = requests.post(url, timeout=2, **kwargs)
                
                if resp.status_code < 500:
                    self._record_success(node_id)
                    return resp, True
                else:
                    self._record_failure(node_id)
                    
            except Exception as e:
                self._record_failure(node_id)
                
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0, base_delay)
                    delay = base_delay + jitter
                    print(f"   ⏳ Retry {attempt + 1}/{max_retries} in {delay:.2f}s...")
                    time.sleep(delay)
        
        return None, False
    
    def write(self, key: str, value: str, quorum: int = 2) -> bool:
        """Write data with quorum consistency."""
        print(f"\n📝 Writing {key}={value} (W={quorum})")
        
        preferred = self._get_preferred_nodes(key, count=quorum + 1)
        
        if len(preferred) < quorum:
            print(f"❌ Not enough nodes available ({len(preferred)} < {quorum})")
            return False
        
        successes = []
        failures = []
        
        for node in preferred:
            if len(successes) >= quorum:
                break
            
            node_id = node["node_id"]
            address = node["address"]
            
            print(f"   → Writing to {node_id}...", end=" ")
            
            resp, ok = self._request_with_retry(
                "POST",
                f"{address}/data",
                node_id,
                json={"key": key, "value": value, "is_replica": False}
            )
            
            if ok and resp and resp.status_code == 200:
                print(f"✅")
                successes.append(node_id)
            else:
                print(f"❌")
                failures.append(node_id)
        
        if len(successes) >= quorum:
            print(f"✅ Write successful! Quorum met: {len(successes)}/{quorum}")
            return True
        else:
            print(f"❌ Write failed. Only {len(successes)}/{quorum} acks")
            return False
    
    def read(self, key: str) -> Optional[str]:
        """Read data with automatic failover."""
        print(f"\n📖 Reading {key}")
        
        preferred = self._get_preferred_nodes(key)
        
        for node in preferred:
            node_id = node["node_id"]
            address = node["address"]
            
            state = self._get_circuit_state(node_id)
            if state == "OPEN":
                print(f"   → {node_id}: ⏭️  Skipped (circuit open)")
                continue
            
            print(f"   → Reading from {node_id}...", end=" ")
            
            resp, ok = self._request_with_retry(
                "GET",
                f"{address}/data/{key}",
                node_id,
                max_retries=1
            )
            
            if ok and resp:
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ (v{data.get('version', '?')})")
                    return data.get("value")
                elif resp.status_code == 404:
                    print(f"🔍 Not found")
                    continue
            else:
                print(f"❌ Failed")
        
        print(f"❌ Could not read {key}")
        return None
    
    def get_status(self):
        """Get cluster status."""
        try:
            resp = requests.get(f"{self.registry_url}/cluster-status", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

def interactive_mode(client: ClusterClient):
    """Run interactive client mode."""
    print("\n🎮 Interactive Mode")
    print("Commands: write <key> <value> | read <key> | status | quit")
    
    while True:
        try:
            cmd = input("\n> ").strip().split()
            
            if not cmd:
                continue
            
            if cmd[0] == "quit" or cmd[0] == "exit":
                break
            
            elif cmd[0] == "write" and len(cmd) >= 3:
                key = cmd[1]
                value = " ".join(cmd[2:])
                client.write(key, value)
            
            elif cmd[0] == "read" and len(cmd) >= 2:
                key = cmd[1]
                value = client.read(key)
                if value:
                    print(f"   Value: {value}")
            
            elif cmd[0] == "status":
                status = client.get_status()
                if status:
                    print(f"\n   Cluster: {status.get('health', 'unknown').upper()}")
                    print(f"   Nodes: {status.get('alive_count', 0)}/{status.get('total_nodes', 0)}")
                    for node in status.get("nodes", []):
                        emoji = "🟢" if node["status"] == "alive" else "🔴"
                        print(f"     {emoji} {node['node_id']} ({node['status']})")
                else:
                    print("   ❌ Cannot reach registry")
            
            else:
                print("   Unknown command. Try: write <key> <value> | read <key> | status | quit")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n👋 Goodbye!")

def demo_mode(client: ClusterClient):
    """Run a demo of client capabilities."""
    print("\n🚀 Running Demo Mode")
    print("=" * 50)
    
    # Write some test data
    test_data = [
        ("user:1", "Alice"),
        ("user:2", "Bob"),
        ("user:3", "Charlie"),
        ("config:theme", "dark"),
        ("session:xyz", "active"),
    ]
    
    print("\n📝 Phase 1: Writing test data...")
    for key, value in test_data:
        client.write(key, value)
        time.sleep(0.5)
    
    print("\n📖 Phase 2: Reading back data...")
    for key, _ in test_data:
        value = client.read(key)
        time.sleep(0.3)
    
    print("\n🔥 Phase 3: Chaos testing")
    print("Now try killing a node with:")
    print("  curl -X POST http://localhost:5000/kill/node-1")
    print("\nThen run reads again - they should failover automatically!")
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=str, default="http://localhost:5000")
    parser.add_argument("--mode", type=str, choices=["demo", "interactive"], default="interactive")
    args = parser.parse_args()
    
    client = ClusterClient(args.registry)
    
    print("🌐 Smart Cluster Client")
    print(f"   Registry: {args.registry}")
    
    # Check registry connection
    status = client.get_status()
    if status:
        print(f"   ✅ Connected to cluster: {status.get('alive_count', 0)} nodes alive")
    else:
        print("   ⚠️  Cannot reach registry. Make sure it's running!")
    
    if args.mode == "demo":
        demo_mode(client)
    else:
        interactive_mode(client)
