"""
Replication Solution

📋 SOLUTION FILE - Students can copy this to see replication working.

Copy the replicate_to_followers() method below into your ReplicationMiddleware class
in middleware/replication.py to complete the exercise.
"""

import time
import requests


def replicate_to_followers_solution(self, key: str, value: str, version: int, data_store: dict):
    """
    Complete implementation of async replication to followers.
    
    Copy this method into your ReplicationMiddleware class.
    """
    for follower in self.followers:
        try:
            # Simulate network lag
            if self.replication_delay > 0:
                time.sleep(self.replication_delay)
            
            # Send replication request
            resp = requests.post(
                f"{follower}/replicate",
                json={"key": key, "value": value, "version": version},
                timeout=2
            )
            
            if resp.status_code == 200:
                self.replication_stats["replications_sent"] += 1
                print(f"[{self.node_id}] Replicated {key} to {follower}")
            else:
                self.replication_stats["replication_failures"] += 1
                
        except Exception as e:
            self.replication_stats["replication_failures"] += 1
            print(f"[{self.node_id}] Failed to replicate to {follower}: {e}")


# ═══════════════════════════════════════════════════════════════════
# QUICK COPY-PASTE VERSION
# ═══════════════════════════════════════════════════════════════════

"""
def replicate_to_followers(self, key: str, value: str, version: int, data_store: dict):
    for follower in self.followers:
        try:
            if self.replication_delay > 0:
                time.sleep(self.replication_delay)
            
            resp = requests.post(
                f"{follower}/replicate",
                json={"key": key, "value": value, "version": version},
                timeout=2
            )
            
            if resp.status_code == 200:
                self.replication_stats["replications_sent"] += 1
            else:
                self.replication_stats["replication_failures"] += 1
        except:
            self.replication_stats["replication_failures"] += 1
"""
