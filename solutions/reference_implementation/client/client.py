import httpx
import asyncio
import time
import argparse

async def main():
    parser = argparse.ArgumentParser(description="Python distributed systems client")
    parser.add_argument("--url", default="http://127.0.0.1:3000", help="Server URL")
    args = parser.parse_args()
    base_url = args.url

    async with httpx.AsyncClient(base_url=base_url) as client:
        # Test Root
        start = time.time()
        resp = await client.get("/")
        print(f"GET /: Status {resp.status_code}, Time: {time.time() - start:.4f}s")
        print(f"Response: {resp.text}\n")

        # Test Echo
        payload = {"message": "Hello Distributed World"}
        start = time.time()
        resp = await client.post("/echo", json=payload)
        print(f"POST /echo: Status {resp.status_code}, Time: {time.time() - start:.4f}s")
        print(f"Response: {resp.json()}\n")

        # Test Delay
        seconds = 2
        start = time.time()
        resp = await client.get(f"/delay/{seconds}")
        print(f"GET /delay/{seconds}: Status {resp.status_code}, Time: {time.time() - start:.4f}s")
        print(f"Response: {resp.text}\n")

if __name__ == "__main__":
    asyncio.run(main())
