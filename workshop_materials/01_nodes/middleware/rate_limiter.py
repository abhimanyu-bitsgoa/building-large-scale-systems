"""
Rate Limiter Middleware

Implements Token Bucket rate limiting as FastAPI/Starlette middleware.
Students implement the is_allowed() method in TokenBucketStrategy.
"""

import time
from collections import defaultdict
from fastapi.responses import JSONResponse
from .strategies import RateLimitStrategy


class TokenBucketStrategy(RateLimitStrategy):
    """
    Token Bucket Rate Limiting Algorithm
    
    📝 STUDENT EXERCISE: Implement the is_allowed() method
    
    How Token Bucket works:
    ┌─────────────────────────────────────────────────────────┐
    │  🪣 Each client gets a "bucket" with tokens             │
    │  🔄 Tokens refill at a constant rate (e.g., 5/second)   │
    │  📤 Each request consumes 1 token                       │
    │  ❌ If bucket is empty, request is rejected (429)       │
    └─────────────────────────────────────────────────────────┘
    
    Example with rate=5:
    - Client starts with 5 tokens
    - Sends 3 requests rapidly → 2 tokens left
    - Waits 1 second → tokens refill to 5
    - Sends 6 requests rapidly → 5 succeed, 1 rejected
    """
    
    def __init__(self, rate: int = 5):
        """
        Initialize the token bucket.
        
        Args:
            rate: Maximum requests per second (also the bucket capacity)
        """
        self.rate = rate
        # Dictionary to track each client's bucket
        # Format: {client_id: {"tokens": float, "last_refill": float}}
        self.buckets = defaultdict(lambda: {"tokens": rate, "last_refill": time.time()})
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a request from this client should be allowed.
        
        ════════════════════════════════════════════════════════
        TODO: Implement the token bucket algorithm
        
        Steps:
        1. Get the bucket for this client_id (self.buckets[client_id])
        2. Calculate time elapsed since last refill
        3. Refill tokens: add (elapsed * self.rate) tokens
           - But don't exceed self.rate (the max capacity)
        4. Update last_refill time to now
        5. If tokens >= 1: consume 1 token, return True
        6. Otherwise: return False (rate limit exceeded)
        
        Hints:
        - Use time.time() to get current timestamp
        - bucket["tokens"] and bucket["last_refill"] are the fields
        - Use min() to cap tokens at self.rate
        ════════════════════════════════════════════════════════
        """
        # ─────────────────────────────────────────────────────
        # YOUR CODE HERE
        # ─────────────────────────────────────────────────────
        raise NotImplementedError(
            "Implement the token bucket algorithm! "
            "See the docstring above for step-by-step instructions."
        )


class RateLimiterMiddleware:
    """
    ASGI Middleware that applies rate limiting to all HTTP requests.
    
    Usage:
        from middleware import RateLimiterMiddleware
        app.add_middleware(RateLimiterMiddleware, rate=5)
    """
    
    def __init__(self, app, rate: int = 5, strategy: RateLimitStrategy = None):
        """
        Initialize the rate limiter middleware.
        
        Args:
            app: The ASGI application
            rate: Requests per second limit (default: 5)
            strategy: Optional custom strategy (defaults to TokenBucketStrategy)
        """
        self.app = app
        self.strategy = strategy or TokenBucketStrategy(rate=rate)
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - called for each request."""
        # Only apply to HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get client identifier (IP address)
        client_ip = scope["client"][0] if scope.get("client") else "unknown"
        
        # Check rate limit
        if not self.strategy.is_allowed(client_ip):
            # Rate limit exceeded - return 429 Too Many Requests
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please slow down.",
                    "retry_after": 1
                }
            )
            await response(scope, receive, send)
            return
        
        # Request allowed - continue to the actual handler
        await self.app(scope, receive, send)
