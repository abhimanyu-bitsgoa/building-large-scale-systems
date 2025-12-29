from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Callable

class RateLimitMiddleware:
    """
    Simple Token Bucket Rate Limiter Middleware.
    
    Students can swap this for a FixedWindowStrategy later.
    """
    def __init__(self, app, requests_per_second: int = 5):
        self.app = app
        self.requests_per_second = requests_per_second
        self.tokens_per_ip = defaultdict(lambda: {'tokens': requests_per_second, 'last_refill': time.time()})
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get client IP
        client_ip = scope["client"][0] if scope.get("client") else "unknown"
        
        # Refill tokens based on time elapsed
        now = time.time()
        bucket = self.tokens_per_ip[client_ip]
        elapsed = now - bucket['last_refill']
        
        # Refill tokens (1 token per second)
        bucket['tokens'] = min(
            self.requests_per_second,
            bucket['tokens'] + elapsed * self.requests_per_second
        )
        bucket['last_refill'] = now
        
        # Check if we have tokens
        if bucket['tokens'] < 1:
            # Rate limit exceeded
            response = JSONResponse(
                status_code=429,
                content={"error": "Too Many Requests", "retry_after": 1}
            )
            await response(scope, receive, send)
            return
        
        # Consume a token
        bucket['tokens'] -= 1
        
        # Continue with the request
        await self.app(scope, receive, send)

# Example usage (students will add this to their node.py):
# from rate_limit_middleware import RateLimitMiddleware
# app.add_middleware(RateLimitMiddleware, requests_per_second=5)
