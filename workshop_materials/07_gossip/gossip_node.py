import uvicorn
from fastapi import FastAPI, BackgroundTasks
import argparse
import random
import time
import requests
import threading

app = FastAPI()

# Configuration
NODE_ID = 0
PORT = 0
NEIGHBORS = [] # List of ports for other nodes

# State dictionary: {node_id: version}
# We gossip the version of the data each node has.
node_states = {}

def gossip_task():
    """Background thread to gossip with neighbors."""
    while True:
        time.sleep(2)  # Gossip every 2 seconds
        if not NEIGHBORS:
            continue
            
        target_port = random.choice(NEIGHBORS)
        try:
            # Send current knowledge to a random neighbor
            response = requests.post(
                f"http://localhost:{target_port}/gossip",
                json=node_states,
                timeout=1
            )
            if response.status_code == 200:
                # Optional: The neighbor could return its state too (anti-entropy)
                # But for simplicity, we just push.
                pass
        except Exception as e:
            # print(f"[Node {NODE_ID}] Failed to gossip to {target_port}")
            pass

@app.get("/")
def get_state():
    return {"node_id": NODE_ID, "states": node_states}

@app.post("/update")
def update_self():
    """Manually increment this node's version to trigger gossip."""
    current_version = node_states.get(str(NODE_ID), 0)
    node_states[str(NODE_ID)] = current_version + 1
    return {"status": "updated", "new_version": node_states[str(NODE_ID)]}

@app.post("/gossip")
def receive_gossip(received_states: dict):
    """Receive gossip from a peer and merge it."""
    global node_states
    
    changed = False
    for node_id, version in received_states.items():
        # Merge if the received version is newer
        if node_id not in node_states or version > node_states[node_id]:
            node_states[node_id] = version
            changed = True
            
    if changed:
        print(f"[Node {NODE_ID}] Updated state: {node_states}")
    
    return {"status": "merged", "current_state": node_states}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--neighbors", type=str, default="", help="Comma-separated ports")
    args = parser.parse_args()
    
    NODE_ID = args.id
    PORT = args.port
    if args.neighbors:
        NEIGHBORS = [int(p) for p in args.neighbors.split(",")]
        
    # Initialize self state
    node_states[str(NODE_ID)] = 0
    
    print(f"Starting Gossip Node {NODE_ID} on port {PORT}")
    print(f"Neighbors: {NEIGHBORS}")
    
    # Start gossip thread
    threading.Thread(target=gossip_task, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)
