"""
Token Bucket Solution

📋 SOLUTION FILE - Students can copy this to see the rate limiter working.

Copy the is_allowed() method below into your TokenBucketStrategy class
in middleware/rate_limiter.py to complete the exercise.
"""

import time
from collections import defaultdict


def is_allowed_solution(self, client_id: str) -> bool:
    """
    Complete implementation of the token bucket algorithm.
    
    Copy this method into your TokenBucketStrategy class.
    """
    now = time.time()
    bucket = self.buckets[client_id]
    
    # Step 1-2: Calculate time elapsed since last refill
    elapsed = now - bucket["last_refill"]
    
    # Step 3: Refill tokens based on elapsed time
    # Add tokens at rate of self.rate tokens per second
    # But don't exceed the maximum capacity (self.rate)
    bucket["tokens"] = min(
        self.rate,  # Maximum capacity
        bucket["tokens"] + (elapsed * self.rate)  # Current + refilled
    )
    
    # Step 4: Update last refill time
    bucket["last_refill"] = now
    
    # Step 5-6: Check if we have tokens available
    if bucket["tokens"] >= 1:
        # Consume one token
        bucket["tokens"] -= 1
        return True
    else:
        # No tokens available - rate limit exceeded
        return False


# ═══════════════════════════════════════════════════════════════════
# QUICK COPY-PASTE VERSION
# ═══════════════════════════════════════════════════════════════════
# Replace the entire is_allowed method in rate_limiter.py with this:

"""
def is_allowed(self, client_id: str) -> bool:
    now = time.time()
    bucket = self.buckets[client_id]
    
    elapsed = now - bucket["last_refill"]
    bucket["tokens"] = min(self.rate, bucket["tokens"] + (elapsed * self.rate))
    bucket["last_refill"] = now
    
    if bucket["tokens"] >= 1:
        bucket["tokens"] -= 1
        return True
    return False
"""
