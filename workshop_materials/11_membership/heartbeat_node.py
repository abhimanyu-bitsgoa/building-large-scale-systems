import uvicorn
from fastapi import FastAPI
import argparse
import time
import requests
import threading

app = FastAPI()

NODE_ID = ""
PORT = 0
REGISTRY_URL = ""

def send_heartbeats():
    """Background task to send heartbeats to the registry."""
    while True:
        try:
            requests.post(f"{REGISTRY_URL}/heartbeat/{NODE_ID}")
        except:
            print("Failed to send heartbeat")
        time.sleep(2)

@app.get("/")
def home():
    return {"id": NODE_ID, "status": "running"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--id", type=str, required=True)
    parser.add_argument("--registry", type=str, default="http://localhost:5000")
    args = parser.parse_args()
    
    NODE_ID = args.id
    PORT = args.port
    REGISTRY_URL = args.registry
    
    print(f"Node {NODE_ID} starting...")

    # 1. Register
    try:
        requests.post(f"{REGISTRY_URL}/register", json={"id": NODE_ID, "port": PORT})
    except:
        print("Could not connect to Registry!")

    # 2. Start heartbeat thread
    threading.Thread(target=send_heartbeats, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=PORT)
