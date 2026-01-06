import time
import requests
from enum import Enum

class State(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, don't even try
    HALF_OPEN = "HALF_OPEN" # Testing if it's back

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=5):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = State.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def call(self, url):
        if self.state == State.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = State.HALF_OPEN
                print("⚡ Circuit semi-closed: Entering HALF_OPEN")
            else:
                raise Exception("Circuit is OPEN (Fast Fail)")

        try:
            # Try the actual request
            response = requests.get(url, timeout=1)
            response.raise_for_status()
            
            # If successful, reset everything
            self.success()
            return response.json()
            
        except Exception as e:
            self.failure()
            raise e

    def success(self):
        if self.state == State.HALF_OPEN:
            print("✅ Circuit closed: Recovery successful!")
        self.state = State.CLOSED
        self.failure_count = 0

    def failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == State.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self.state = State.OPEN
            print(f"💥 Circuit split: Entering OPEN state (Failures: {self.failure_count})")
