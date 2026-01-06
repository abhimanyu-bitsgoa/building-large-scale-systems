import requests
import time
import os

LOCK_SERVER = "http://localhost:14000/status"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        try:
            resp = requests.get(LOCK_SERVER, timeout=1)
            locks = resp.json()
            
            clear_screen()
            print("        🎟️  DISTRIBUTED LOCK (TICKET RACE)  🎟️")
            print("=" * 45)
            print("Resource       | Owner        | Expires In")
            print("-" * 45)
            
            if not locks:
                print("      No active locks held. Seats are free!")
            
            now = time.time()
            for resource, info in locks.items():
                ttl = info["expires"] - now
                if ttl > 0:
                    print(f" {resource:<13} | {info['owner']:<12} | {ttl:.1f}s")
                
        except:
            clear_screen()
            print("Waiting for Lock Server to start on port 14000...")

        print("-" * 45)
        print("\nHow to test:")
        print("1. Start Lock Server: python3 workshop_materials/14_locking/lock_server.py")
        print("2. Run 2 workers simultaneously in different terminals:")
        print("   python3 workshop_materials/14_locking/book_ticket.py --id NodeA")
        print("   python3 workshop_materials/14_locking/book_ticket.py --id NodeB")
        print("\n3. Only one node will 'win' the seat. The other will fail.")
        
        print("\nPress Ctrl+C to stop.")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
