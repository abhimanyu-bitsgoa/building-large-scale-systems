import requests
import time
import os

NODES = [
    {"id": 1, "port": 8001},
    {"id": 2, "port": 8002},
    {"id": 3, "port": 8003},
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_election():
    clear_screen()
    print("        👑  LEADER ELECTION (BULLY)  👑")
    print("=" * 45)
    print("Node ID | Port | Status | Leader")
    print("-" * 45)
    
    for node in NODES:
        try:
            resp = requests.get(f"http://localhost:{node['port']}/", timeout=0.5)
            data = resp.json()
            is_leader = data.get("is_leader", False)
            leader_id = data.get("leader_id")
            
            status = "LEADER 👑" if is_leader else "FOLLOWER"
            election = " (✍️ Election!)" if data.get("election_in_progress") else ""
            
            print(f" Node {node['id']} | {node['port']} | {status}{election} | {leader_id}")
        except:
            print(f" Node {node['id']} | {node['port']} | [OFFLINE] | -")

    print("-" * 45)
    print("\nHow to test:")
    print("1. Find the current LEADER (usually Node 3).")
    print("2. Kill that node's process (Ctrl+C).")
    print("3. Watch Node 1 & 2 detect the failure and fight to be leader!")
    print("4. Restart Node 3 and watch it 'bully' its way back to the top.")
    print("\nPress Ctrl+C to stop.")

if __name__ == "__main__":
    while True:
        draw_election()
        time.sleep(1)
