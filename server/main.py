from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import time

app = FastAPI()

def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

@app.get("/")
async def root():
    n = 10
    result = fib(n)
    print(f"Fib({n}) = {result}")
    return "Hello, World!"

class EchoPayload(BaseModel):
    message: str

@app.post("/echo")
async def echo(payload: EchoPayload):
    return payload

@app.get("/delay/{seconds}")
async def delay(seconds: int):
    await asyncio.sleep(seconds)
    return f"Waited for {seconds} seconds"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3000)
