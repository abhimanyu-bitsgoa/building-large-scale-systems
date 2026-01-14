import uvicorn
from fastapi import FastAPI, BackgroundTasks
import argparse
import time
import requests
import threading

app = FastAPI()

# Configuration
NODE_ID = 0
PORT = 0
NODES = {} # {id: port}

LEADER_ID = None
ELECTION_IN_PROGRESS = False

def check_leader():
    """Periodically check if leader is alive."""
    global LEADER_ID, ELECTION_IN_PROGRESS
    while True:
        time.sleep(3)
        if LEADER_ID is None or LEADER_ID == NODE_ID:
            continue
            
        leader_port = NODES.get(LEADER_ID)
        try:
            resp = requests.get(f"http://localhost:{leader_port}/health", timeout=1)
            if resp.status_code != 200:
                raise Exception("Leader unhealthy")
        except:
            print(f"[Node {NODE_ID}] Leader {LEADER_ID} is DOWN. Starting election...")
            threading.Thread(target=start_election).start()

def start_election():
    global ELECTION_IN_PROGRESS, LEADER_ID
    if ELECTION_IN_PROGRESS:
        return
        
    ELECTION_IN_PROGRESS = True
    print(f"[Node {NODE_ID}] Initiating Election...")
    
    higher_nodes = {id: port for id, port in NODES.items() if id > NODE_ID}
    
    any_higher_responded = False
    for id, port in higher_nodes.items():
        try:
            resp = requests.post(f"http://localhost:{port}/election", json={"from": NODE_ID}, timeout=1)
            if resp.status_code == 200:
                any_higher_responded = True
        except:
            pass
            
    if not any_higher_responded:
        # I am the leader!
        become_leader()
    else:
        # Wait for a coordinator message
        time.sleep(5)
        if ELECTION_IN_PROGRESS:
            print(f"[Node {NODE_ID}] Election timed out. Restarting...")
            ELECTION_IN_PROGRESS = False
            start_election()

    ELECTION_IN_PROGRESS = False

def become_leader():
    global LEADER_ID
    LEADER_ID = NODE_ID
    print(f"[Node {NODE_ID}] I am the LEADER 👑")
    
    for id, port in NODES.items():
        if id == NODE_ID: continue
        try:
            requests.post(f"http://localhost:{port}/coordinator", json={"leader": NODE_ID}, timeout=1)
        except:
            pass

@app.get("/health")
def health():
    return {"status": "ok", "id": NODE_ID, "is_leader": LEADER_ID == NODE_ID}

@app.post("/election")
def handle_election(payload: dict):
    print(f"[Node {NODE_ID}] Received Election from Node {payload['from']}")
    # Start our own election because we have a higher ID
    threading.Thread(target=start_election).start()
    return {"status": "alive"}

@app.post("/coordinator")
def handle_coordinator(payload: dict):
    global LEADER_ID, ELECTION_IN_PROGRESS
    LEADER_ID = payload['leader']
    ELECTION_IN_PROGRESS = False
    print(f"[Node {NODE_ID}] New Leader: {LEADER_ID}")
    return {"status": "acknowledged"}

@app.get("/")
def get_info():
    return {
        "node_id": NODE_ID,
        "leader_id": LEADER_ID,
        "is_leader": LEADER_ID == NODE_ID,
        "election_in_progress": ELECTION_IN_PROGRESS
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--nodes", type=str, required=True, help="id:port,id:port")
    args = parser.parse_args()
    
    NODE_ID = args.id
    PORT = args.port
    for pair in args.nodes.split(","):
        nid, nport = pair.split(":")
        NODES[int(nid)] = int(nport)
    
    print(f"Starting Bully Node {NODE_ID} on port {PORT}")
    
    # Start leader checker thread
    threading.Thread(target=check_leader, daemon=True).start()
    
    # Initially start an election to find a leader
    threading.Thread(target=start_election).start()
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)
