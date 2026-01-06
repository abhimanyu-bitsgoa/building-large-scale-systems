import asyncio
import time
import random

# --- The Queues ---
main_queue = [
    {"id": 1, "data": "Normal Task"},
    {"id": 2, "data": "POISON_PILL"}, # This one will crash the worker
    {"id": 3, "data": "Normal Task"},
    {"id": 4, "data": "Another Task"},
]

dlq = [] # Dead Letter Queue
retry_counts = {} # {msg_id: count}
MAX_RETRIES = 3

async def process_message(msg):
    """Simulates processing. Crashes on specific data."""
    print(f"  [Worker] Attempting to process Message {msg['id']}...")
    await asyncio.sleep(0.5)
    
    if msg["data"] == "POISON_PILL":
        raise ValueError("CRITICAL ERROR: Malformed Data! (Simulated Crash)")
    
    return True

async def worker():
    global main_queue, dlq
    
    while main_queue:
        msg = main_queue.pop(0)
        msg_id = msg["id"]
        
        try:
            await process_message(msg)
            print(f"  ✅ SUCCESS: Message {msg_id} done.")
        except Exception as e:
            print(f"  ❌ FAILURE: Message {msg_id} failed!")
            
            # Increment retry count
            count = retry_counts.get(msg_id, 0) + 1
            retry_counts[msg_id] = count
            
            if count >= MAX_RETRIES:
                print(f"  ⚠️  MAX RETRIES REACHED. Moving Message {msg_id} to DLQ.")
                dlq.append(msg)
            else:
                print(f"  🔄 Retrying message {msg_id} (Attempt {count}/{MAX_RETRIES})...")
                # Put it back at the END of the queue (or front, depending on strategy)
                main_queue.append(msg)
                
        await asyncio.sleep(1)

async def main():
    print("🚀 Worker Starting. Processing Queue...")
    print("=" * 45)
    
    await worker()
    
    print("\n" + "=" * 45)
    print("🎉 Queue Empty. Final Status:")
    print(f"   DLQ Count: {len(dlq)} messages")
    for m in dlq:
        print(f"   - DLQ Entry: Message {m['id']} ('{m['data']}')")

if __name__ == "__main__":
    asyncio.run(main())
