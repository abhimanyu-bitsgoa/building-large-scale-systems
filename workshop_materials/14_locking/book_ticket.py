import requests
import time
import argparse
import random

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str, required=True)
    parser.add_argument("--lock-server", type=str, default="http://localhost:14000")
    args = parser.parse_args()

    resource = "ticket_seat_A1"
    print(f"Worker {args.id} trying to book {resource}...")

    # 1. Try to acquire lock
    try:
        resp = requests.post(f"{args.lock_server}/acquire/{resource}?owner={args.id}&ttl=3")
        data = resp.json()
        
        if data["status"] == "granted":
            print(f"✅ WORKER {args.id}: Lock ACQUIRED!")
            print(f"   (Doing heavy booking logic for 2 seconds...)")
            time.sleep(2)
            
            # 2. Release lock
            requests.post(f"{args.lock_server}/release/{resource}?owner={args.id}")
            print(f"🏁 WORKER {args.id}: Booking COMPLETE, Lock Released.")
        else:
            print(f"❌ WORKER {args.id}: Permission DENIED. {data.get('reason')} - {data.get('owner')}")
            
    except Exception as e:
        print(f"Failed to connect to lock server: {e}")

if __name__ == "__main__":
    main()
