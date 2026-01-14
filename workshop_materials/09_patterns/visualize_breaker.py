import time
import os
from circuit_breaker import CircuitBreaker, State

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    url = "http://localhost:9001/"
    
    print("Starting Circuit Breaker Visualizer...")
    time.sleep(1)

    while True:
        clear_screen()
        print("        ⚡ CIRCUIT BREAKER DEMO ⚡")
        print("=" * 45)
        
        state_color = {
            State.CLOSED: "🟢 CLOSED (Healthy)",
            State.OPEN: "🔴 OPEN (Failing - Fast Fail)",
            State.HALF_OPEN: "🟡 HALF-OPEN (Testing Recovery)"
        }
        
        print(f"Current State: {state_color[breaker.state]}")
        print(f"Failures:      {breaker.failure_count}")
        print("-" * 45)
        
        try:
            print(f"Requesting {url}...")
            result = breaker.call(url)
            print(f"Response:      {result['message']}")
        except Exception as e:
            print(f"Error:         {str(e)}")

        print("-" * 45)
        print("\nHow to test:")
        print("1. Start flaky server: python3 workshop_materials/09_patterns/flaky_server.py")
        print("2. Make it fail: curl -X POST http://localhost:9001/fail")
        print("3. Watch the circuit open after 3 failures.")
        print("4. Recover it: curl -X POST http://localhost:9001/recover")
        print("5. Watch the circuit recover!")
        
        print("\nPress Ctrl+C to stop.")
        time.sleep(1)

if __name__ == "__main__":
    main()
