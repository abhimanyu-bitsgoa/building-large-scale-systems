import asyncio
import time
import random

# Global Database call counter
db_queries = 0

async def slow_database_query(key):
    """Simulates a heavy database query."""
    global db_queries
    db_queries += 1
    print(f"  [DB] Fetching key '{key}' from Disk... (Query #{db_queries})")
    await asyncio.sleep(2) # 2 seconds of heavy work
    return f"Value for {key}"

# --- SCENARIO 1: The Stampede ---

async def request_without_protection(client_id, key):
    print(f"Client {client_id}: Requesting '{key}'...")
    # No protection: everyone hits the DB if it's "not in cache"
    # (Simulating that it's always not in cache for this demo)
    value = await slow_database_query(key)
    print(f"Client {client_id}: Got {value}")

# --- SCENARIO 2: Single Flight protection ---

# A dictionary to track ongoing requests
inflight_requests = {}

async def request_with_single_flight(client_id, key):
    global inflight_requests
    print(f"Client {client_id}: Requesting '{key}' (SingleFlight active)...")

    if key in inflight_requests:
        print(f"  [SingleFlight] Client {client_id} waiting for existing request...")
        return await inflight_requests[key]

    # Create a future/task for the DB query
    task = asyncio.create_task(slow_database_query(key))
    inflight_requests[key] = task
    
    try:
        value = await task
        return value
    finally:
        # Clean up once done
        if key in inflight_requests:
            del inflight_requests[key]

async def run_scenario(mode):
    global db_queries
    db_queries = 0
    key = "user_42"
    num_clients = 5
    
    print(f"\n🚀 Running Scenario: {mode}")
    print("=" * 40)
    
    start_time = time.time()
    
    tasks = []
    for i in range(num_clients):
        if mode == "STAMPEDE":
            tasks.append(request_without_protection(i, key))
        else:
            tasks.append(request_with_single_flight(i, key))
            
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print("-" * 40)
    print(f"TOTAL DB QUERIES: {db_queries}")
    print(f"TOTAL TIME:       {duration:.2f}s")

if __name__ == "__main__":
    print("=== THUNDERING HERD DEMO ===")
    asyncio.run(run_scenario("STAMPEDE"))
    time.sleep(1)
    asyncio.run(run_scenario("SINGLE_FLIGHT"))
