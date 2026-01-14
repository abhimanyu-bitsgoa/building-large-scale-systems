import uvicorn
from fastapi import FastAPI, HTTPException, Request
import asyncio
import argparse
import time

app = FastAPI()

# Buffer configuration
buffer = []
BUFFER_LIMIT = 50
BACKPRESSURE_ENABLED = False

# Stats
processed_count = 0
dropped_count = 0

@app.post("/push")
async def push_data(request: Request):
    global dropped_count
    data = await request.json()
    
    if len(buffer) >= BUFFER_LIMIT:
        if BACKPRESSURE_ENABLED:
            # Tell the producer to slow down (429 Too Many Requests)
            raise HTTPException(status_code=429, detail="Backpressure: Buffer Full")
        else:
            # No backpressure: Just drop the data (OOM simulation or silent loss)
            dropped_count += 1
            return {"status": "dropped", "reason": "buffer_full"}
            
    buffer.append(data)
    return {"status": "accepted", "buffer_size": len(buffer)}

@app.get("/stats")
def get_stats():
    return {
        "buffer_size": len(buffer),
        "buffer_limit": BUFFER_LIMIT,
        "processed": processed_count,
        "dropped": dropped_count,
        "backpressure_enabled": BACKPRESSURE_ENABLED
    }

async def consumer_loop():
    """Simulates a slow worker processing items from the buffer."""
    global processed_count
    while True:
        if buffer:
            _ = buffer.pop(0)
            processed_count += 1
            # Simulate slow processing (e.g., DB write)
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--backpressure", action="store_true")
    args = parser.parse_args()
    
    BACKPRESSURE_ENABLED = args.backpressure
    print(f"Starting Consumer on port {args.port} (Backpressure: {BACKPRESSURE_ENABLED})")
    
    # Start worker loop
    asyncio.get_event_loop().create_task(consumer_loop())
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)
