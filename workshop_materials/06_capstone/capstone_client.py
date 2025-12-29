import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import time
import requests
from typing import List
from collections import defaultdict

# Import your sharding library
from workshop_materials.sharding.sharding_lib import ConsistentHashingStrategy

class ResilientClient:
    def __init__(self, nodes: List[str]):
        self.all_nodes = nodes
        self.alive_nodes = set(nodes)  # Track which nodes are alive
        self.hashing_strategy = ConsistentHashingStrategy(nodes)
    
    def _mark_node_down(self, node_url: str):
        """Mark a node as down after connection failure."""
        if node_url in self.alive_nodes:
            self.alive_nodes.remove(node_url)
            print(f"⚠️ Marked {node_url} as DOWN. Alive: {len(self.alive_nodes)}/{len(self.all_nodes)}")
    
    def _try_node_recovery(self):
        """Periodically check if dead nodes are back online."""
        for node in self.all_nodes:
            if node not in self.alive_nodes:
                try:
                    resp = requests.get(f"{node}/health", timeout=1)
                    if resp.status_code == 200:
                        self.alive_nodes.add(node)
                        print(f"✅ Node {node} recovered!")
                except:
                    pass
    
    def write_quorum(self, key: str, value: str, w: int = 2) -> bool:
        """
        Write data to a quorum of nodes.
        
        TODO: Implement the following logic:
        1. Use ConsistentHashing to find the primary node for this key
        2. Pick W nodes (primary + replicas)
        3. Send POST /data to all W nodes
        4. Return True if at least W nodes ACK
        """
        # HINT: You can use self.hashing_strategy.get_node(key, list(self.alive_nodes))
        # to get the primary node.
        
        raise NotImplementedError("TODO: Implement write_quorum")
    
    def read_quorum(self, key: str, r: int = 2) -> str:
        """
        Read data from a quorum of nodes.
        
        TODO: Implement the following logic:
        1. Use ConsistentHashing to find the primary node
        2. Query R nodes for the key
        3. Return the value if at least R nodes respond
        4. (Bonus) Implement Read Repair if versions differ
        """
        raise NotImplementedError("TODO: Implement read_quorum")

if __name__ == "__main__":
    NODES = [
        "http://localhost:5001",
        "http://localhost:5002",
        "http://localhost:5003"
    ]
    
    client = ResilientClient(NODES)
    
    print("🚀 Starting Resilient Client...")
    print("Make sure 3 nodes are running and the Chaos script is active!")
    
    iteration = 0
    while True:
        try:
            iteration += 1
            key = f"test_key_{iteration % 10}"
            value = f"value_{iteration}"
            
            # Try recovery every 10 iterations
            if iteration % 10 == 0:
                client._try_node_recovery()
            
            # Attempt write
            client.write_quorum(key, value, w=2)
            print(f"✅ Write Success (Iteration {iteration}): {key} = {value}")
            
            time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n👋 Client stopped.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(1)
