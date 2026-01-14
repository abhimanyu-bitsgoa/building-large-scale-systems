import uvicorn
from fastapi import FastAPI
import time
import threading
import argparse

app = FastAPI()

# {node_id: {"port": int, "last_seen": float}}
nodes = {}

EXPIRY_SECONDS = 5

def prune_nodes():
    """Background task to remove nodes that haven't sent heartbeats."""
    while True:
        time.sleep(1)
        now = time.time()
        expired = [nid for nid, info in nodes.items() if now - info["last_seen"] > EXPIRY_SECONDS]
        for nid in expired:
            print(f"💀 Node {nid} expired (No heartbeat)")
            del nodes[nid]

@app.post("/register")
def register(payload: dict):
    node_id = payload["id"]
    port = payload["port"]
    nodes[node_id] = {"port": port, "last_seen": time.time()}
    print(f"✅ Node {node_id} registered on port {port}")
    return {"status": "registered"}

@app.post("/heartbeat/{node_id}")
def heartbeat(node_id: str):
    if node_id in nodes:
        nodes[node_id]["last_seen"] = time.time()
        return {"status": "ok"}
    else:
        return {"status": "not_found"}, 404

@app.get("/nodes")
def list_nodes():
    return nodes

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    
    # Start pruner
    threading.Thread(target=prune_nodes, daemon=True).start()
    
    print(f"Registry starting on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
