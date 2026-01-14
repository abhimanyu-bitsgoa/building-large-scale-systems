import uvicorn
from fastapi import FastAPI
import argparse

app = FastAPI()
data_store = {}
NODE_ID = 0

@app.post("/replicate")
def replicate(payload: dict):
    key = payload["key"]
    value = payload["value"]
    data_store[key] = value
    print(f"[Secondary {NODE_ID}] Replicated {key}={value}")
    return {"status": "ok"}

@app.get("/data/{key}")
def get_data(key: str):
    return {
        "key": key, 
        "value": data_store.get(key), 
        "node": f"secondary_{NODE_ID}"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--id", type=int, required=True)
    args = parser.parse_args()
    
    NODE_ID = args.id
    print(f"Secondary Node {NODE_ID} starting on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
