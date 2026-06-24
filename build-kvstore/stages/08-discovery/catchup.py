"""
Distributed KV Store Lab - Catchup Module

Handles synchronization of new follower nodes with the leader's data.
Called by the registry when a new follower joins the cluster.
"""

import requests
from typing import Optional

def perform_catchup(follower_url: str, leader_url: str, timeout: int = 10) -> bool:
    """
    Perform catchup for a new follower node.
    
    1. Gets full data snapshot from leader
    2. Sends snapshot to new follower
    
    Args:
        follower_url: URL of the new follower node
        leader_url: URL of the leader node
        timeout: Request timeout in seconds
    
    Returns:
        True if catchup successful, False otherwise
    """
    try:
        print(f"[Catchup] Getting snapshot from leader: {leader_url}")
        
        # Get snapshot from leader
        resp = requests.get(f"{leader_url}/snapshot", timeout=timeout)
        if resp.status_code != 200:
            print(f"[Catchup] Failed to get snapshot: {resp.status_code}")
            return False
        
        snapshot = resp.json()
        data = snapshot.get("data", {})
        versions = snapshot.get("versions", {})
        
        print(f"[Catchup] Got {len(data)} keys from leader")
        
        # Send to follower
        print(f"[Catchup] Sending snapshot to follower: {follower_url}")
        resp = requests.post(
            f"{follower_url}/catchup",
            json={"data": data, "versions": versions},
            timeout=timeout
        )
        
        if resp.status_code == 200:
            print(f"[Catchup] ✅ Follower caught up successfully")
            return True
        else:
            print(f"[Catchup] ❌ Failed to send to follower: {resp.status_code}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"[Catchup] ❌ Error: {e}")
        return False

def get_leader_snapshot(leader_url: str, timeout: int = 5) -> Optional[dict]:
    """
    Get the current data snapshot from the leader.
    
    Args:
        leader_url: URL of the leader node
        timeout: Request timeout
    
    Returns:
        Dict with 'data' and 'versions', or None if failed
    """
    try:
        resp = requests.get(f"{leader_url}/snapshot", timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def send_snapshot_to_follower(follower_url: str, data: dict, versions: dict,
                               timeout: int = 10) -> bool:
    """
    Send a data snapshot to a follower node.
    
    Args:
        follower_url: URL of the follower
        data: The key-value data
        versions: The version numbers
        timeout: Request timeout
    
    Returns:
        True if successful
    """
    try:
        resp = requests.post(
            f"{follower_url}/catchup",
            json={"data": data, "versions": versions},
            timeout=timeout
        )
        return resp.status_code == 200
    except:
        return False

# For command-line usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trigger catchup for a follower")
    parser.add_argument("--follower", type=str, required=True, help="Follower URL")
    parser.add_argument("--leader", type=str, required=True, help="Leader URL")
    
    args = parser.parse_args()
    
    success = perform_catchup(args.follower, args.leader)
    exit(0 if success else 1)
