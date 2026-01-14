"""
Load Test Script - Bombard the cluster with requests and observe distribution.

This script sends many requests to the registry and shows which node handled each one,
demonstrating how consistent hashing distributes load.
"""

import requests
import time
import random
import string
from collections import defaultdict
import hashlib

def generate_random_key():
    """Generate a random key."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def get_hash_position(key: str) -> int:
    """Get consistent hash position (0-99 for display)."""
    hash_val = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return hash_val % 100

def main():
    registry_url = "http://localhost:5000"
    num_requests = 50
    
    print("🔥 LOAD TEST: Consistent Hashing Distribution Demo")
    print("=" * 60)
    print()
    
    # Check cluster health
    try:
        resp = requests.get(f"{registry_url}/cluster-status", timeout=2)
        if resp.status_code != 200:
            print("❌ Cannot reach registry. Make sure it's running!")
            return
        status = resp.json()
        alive_nodes = status.get("alive_count", 0)
        print(f"✅ Cluster: {alive_nodes} nodes alive")
        print()
    except Exception as e:
        print(f"❌ Cannot reach registry: {e}")
        return
    
    # Track which node handles which keys
    node_counts = defaultdict(int)
    node_keys = defaultdict(list)
    
    print(f"📝 Sending {num_requests} write requests...")
    print()
    
    successes = 0
    failures = 0
    
    for i in range(num_requests):
        key = f"test:{generate_random_key()}"
        value = f"value_{i}"
        
        try:
            resp = requests.post(
                f"{registry_url}/data",
                json={"key": key, "value": value},
                timeout=2
            )
            if resp.status_code == 200:
                data = resp.json()
                nodes_written = data.get("nodes", [])
                for node in nodes_written:
                    node_counts[node] += 1
                    node_keys[node].append(key)
                successes += 1
                
                # Show progress every 10 requests
                if (i + 1) % 10 == 0:
                    print(f"  [{i+1}/{num_requests}] Written to: {nodes_written}")
            else:
                failures += 1
        except Exception as e:
            failures += 1
    
    print()
    print("=" * 60)
    print("📊 DISTRIBUTION RESULTS")
    print("=" * 60)
    print()
    
    # Show distribution
    total_writes = sum(node_counts.values())
    print(f"Total writes: {successes} success, {failures} failed")
    print()
    
    print("Node               Writes   Percentage   Bar")
    print("-" * 60)
    
    for node, count in sorted(node_counts.items()):
        percentage = (count / total_writes * 100) if total_writes > 0 else 0
        bar_length = int(percentage / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"{node:15}   {count:4}     {percentage:5.1f}%     {bar[:30]}")
    
    print()
    print("-" * 60)
    print()
    
    # Show sample keys per node
    print("📦 Sample Keys per Node:")
    for node, keys in sorted(node_keys.items()):
        sample = keys[:3]
        print(f"  {node}: {', '.join(sample)}{'...' if len(keys) > 3 else ''} ({len(keys)} total)")
    
    print()
    print("=" * 60)
    print()
    
    # Explain the distribution
    if len(node_counts) > 1:
        min_count = min(node_counts.values())
        max_count = max(node_counts.values())
        ratio = max_count / min_count if min_count > 0 else 0
        
        if ratio < 1.5:
            print("✅ Distribution is EVEN! Consistent hashing is working well.")
        elif ratio < 2.0:
            print("⚠️  Distribution is SLIGHTLY UNEVEN. This is normal with few nodes.")
        else:
            print("❌ Distribution is UNEVEN. Consider adding virtual nodes.")
    
    print()
    print("💡 TIP: Try killing a node and run this again to see keys redistribute!")
    print("   curl -X POST http://localhost:5000/kill/node-1")
    print()

if __name__ == "__main__":
    main()
