"""
Distributed KV Store Lab - Catchup

The catchup procedure for a new or respawned follower, in its clearest form: pull the leader's full
data snapshot, then push it to the follower so it rejoins with all the data.

In the running system the coordinator performs catchup directly (see
`coordinator.send_catchup_to_follower`, which adds retries for a follower whose API isn't ready yet).
This module is the standalone, readable reference for what "catchup" means.
"""

import requests


def perform_catchup(follower_url: str, leader_url: str, timeout: int = 10) -> bool:
    """Catch a follower up from the leader: GET the leader's snapshot, then POST it to the follower."""
    try:
        print(f"[Catchup] Getting snapshot from leader: {leader_url}")
        resp = requests.get(f"{leader_url}/snapshot", timeout=timeout)
        if resp.status_code != 200:
            print(f"[Catchup] Failed to get snapshot: {resp.status_code}")
            return False

        snapshot = resp.json()
        data = snapshot.get("data", {})
        versions = snapshot.get("versions", {})
        print(f"[Catchup] Got {len(data)} keys from leader")

        print(f"[Catchup] Sending snapshot to follower: {follower_url}")
        resp = requests.post(
            f"{follower_url}/catchup",
            json={"data": data, "versions": versions},
            timeout=timeout,
        )
        if resp.status_code == 200:
            print(f"[Catchup] ✅ Follower caught up successfully")
            return True
        print(f"[Catchup] ❌ Failed to send to follower: {resp.status_code}")
        return False

    except requests.exceptions.RequestException as e:
        print(f"[Catchup] ❌ Error: {e}")
        return False
