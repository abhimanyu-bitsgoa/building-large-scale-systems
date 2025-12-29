import uvicorn
from fastapi import FastAPI
import argparse

app = FastAPI()

# Store data in-memory
data_store = {}

@app.get("/")
def home():
    return {"message": "Node is running", "id": NODE_ID}

@app.get("/health")
def health():
    return {"status": "ok", "node_id": NODE_ID}

# TODO: Add a POST /data endpoint to store key-value pairs
# @app.post("/data") ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--id", type=int, default=0)
    args = parser.parse_args()
    
    NODE_ID = args.id
    
    print(f"Starting Node {NODE_ID} on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
