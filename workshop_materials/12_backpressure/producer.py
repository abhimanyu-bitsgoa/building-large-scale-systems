import requests
import time
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=str, default="http://localhost:12000/push")
    parser.add_argument("--rate", type=float, default=0.1, help="Sleep time between requests")
    args = parser.parse_args()

    print(f"Producer starting. Targeting {args.target}...")
    
    count = 0
    while True:
        try:
            resp = requests.post(args.target, json={"id": count, "ts": time.time()}, timeout=1)
            
            if resp.status_code == 200:
                print(f"[{count}] Sent successfully")
                count += 1
            elif resp.status_code == 429:
                print(f"⚠️  BACKPRESSURE RECEIVED! Sleeping for 2 seconds...")
                time.sleep(2)
            else:
                print(f"Error: {resp.status_code}")
                
        except Exception as e:
            print(f"Failed to connect: {e}")
            time.sleep(1)

        time.sleep(args.rate)

if __name__ == "__main__":
    main()
