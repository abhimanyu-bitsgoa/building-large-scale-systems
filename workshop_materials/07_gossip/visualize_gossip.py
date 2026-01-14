import requests
import time
import os

NODES = [
    {"id": 1, "port": 7001},
    {"id": 2, "port": 7002},
    {"id": 3, "port": 7003},
    {"id": 4, "port": 7004},
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_states():
    clear_screen()
    print("        📢  GOSSIP PROTOCOL VISUALIZER  📢")
    print("=" * 45)
    print("Node ID | Port | State (NodeID: Version)")
    print("-" * 45)
    
    for node in NODES:
        try:
            resp = requests.get(f"http://localhost:{node['port']}/", timeout=0.5)
            data = resp.json()
            states = data.get("states", {})
            # Sort states for consistent display
            sorted_states = ", ".join([f"{k}:{v}" for k, v in sorted(states.items())])
            print(f" Node {node['id']} | {node['port']} | {sorted_states}")
        except:
            print(f" Node {node['id']} | {node['port']} | [OFFLINE]")

    print("-" * 45)
    print("\nHow to test:")
    print(f"1. Run: curl -X POST http://localhost:{NODES[0]['port']}/update")
    print("2. Watch the version propagate to all other nodes!\n")
    print("Press Ctrl+C to stop.")

if __name__ == "__main__":
    while True:
        draw_states()
        time.sleep(1)
