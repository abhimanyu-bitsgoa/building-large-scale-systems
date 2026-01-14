import requests
import time
import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_gauge(value, total, width=30):
    percent = value / total
    filled = int(width * percent)
    bar = "█" * filled + "-" * (width - filled)
    return f"[{bar}] {value}/{total} ({percent*100:.1f}%)"

def main():
    url = "http://localhost:12000/stats"
    
    while True:
        try:
            resp = requests.get(url, timeout=1)
            data = resp.json()
            
            clear_screen()
            print("        🛑  BACKPRESSURE VISUALIZER  🛑")
            print("=" * 45)
            print(f"Mode: {'✅ BACKPRESSURE ENABLED' if data['backpressure_enabled'] else '❌ NO BACKPRESSURE'}")
            print("-" * 45)
            print(f"Buffer Usage:  {draw_gauge(data['buffer_size'], data['buffer_limit'])}")
            print(f"Processed:     {data['processed']}")
            print(f"Dropped:       {data['dropped']}")
            print("-" * 45)
            
            if not data['backpressure_enabled'] and data['buffer_size'] >= data['buffer_limit']:
                print("\n🔥 SYSTEM OVERWHELMED! Data is being dropped.")
                print("Notice how 'Dropped' count is increasing.")
            elif data['backpressure_enabled'] and data['buffer_size'] >= data['buffer_limit']:
                print("\n✋ BACKPRESSURE ACTIVE! Producer has been told to wait.")
                print("Notice how 'Dropped' stays 0, but throughput slows down.")

        except:
            clear_screen()
            print("Waiting for Consumer to start on port 12000...")
            
        time.sleep(1)

if __name__ == "__main__":
    main()
