import time
import requests
import threading

TARGET_URL = "http://localhost:5001/data"

def good_user():
    """Sends 1 request every 1 second."""
    name = "😇 Good User"
    while True:
        try:
            start = time.time()
            resp = requests.get(f"http://localhost:5001/health")
            status = resp.status_code
            print(f"{name} | Status: {status} | Time: {time.time()-start:.2f}s")
        except Exception as e:
            print(f"{name} | Error: {e}")
        time.sleep(1)

def bad_actor():
    """Spams requests as fast as possible."""
    name = "😈 Bad Actor"
    while True:
        try:
            # spamming /data endpoint which might be protected or heavy
            resp = requests.post(TARGET_URL, json={"junk": "data"})
            status = resp.status_code
            if status == 429:
                print(f"{name} | ⛔ BLOCKED (429) - Rate Limit Working!")
            elif status == 200:
                print(f"{name} | ✅ SUCCESS (200) - Server Vulnerable!")
            else:
                print(f"{name} | Status: {status}")
        except Exception as e:
            print(f"{name} | Connection Error")
        time.sleep(0.1)

if __name__ == "__main__":
    print("Starting Rate Limit Visualization...")
    print("Good User: 1 req/s")
    print("Bad Actor: 10 req/s")
    
    t1 = threading.Thread(target=good_user)
    t2 = threading.Thread(target=bad_actor)
    
    t1.daemon = True
    t2.daemon = True
    
    t1.start()
    t2.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
