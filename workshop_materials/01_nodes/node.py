import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import argparse

app = FastAPI()

# Global variable to store node ID (will be set at startup)
NODE_ID = 0

# Store data in-memory
data_store = {}

class DataPayload(BaseModel):
    key: str
    value: str

@app.get("/")
def home():
    return {"message": "Node is running", "id": NODE_ID}

@app.get("/health")
def health():
    return {"status": "ok", "node_id": NODE_ID}

@app.post("/data")
def store_data(payload: DataPayload):
    """Store a key-value pair in this node's data store."""
    data_store[payload.key] = payload.value
    return {
        "status": "stored",
        "node_id": NODE_ID,
        "key": payload.key,
        "value": payload.value
    }

@app.get("/data/{key}")
def get_data(key: str):
    """Retrieve a value by key from this node's data store."""
    if key not in data_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found on Node {NODE_ID}")
    return {
        "node_id": NODE_ID,
        "key": key,
        "value": data_store[key]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--id", type=int, default=0)
    args = parser.parse_args()
    
    NODE_ID = args.id
    
    print(f"Starting Node {NODE_ID} on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
