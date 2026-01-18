"""
Backpressure Middleware

Implements queue-based backpressure to prevent system overload.
When the request queue exceeds capacity, new requests are rejected with 429.

This is a complete implementation - students observe the behavior.
"""

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time


class BackpressureMiddleware:
    """
    ASGI Middleware that implements backpressure via request queue management.
    
    How it works:
    ┌─────────────────────────────────────────────────────────────┐
    │  📥 New requests enter a virtual queue                     │
    │  📊 When queue size > max_queue_size, reject with 429      │
    │  📤 When requests complete, queue shrinks                  │
    │  ⚡ This prevents memory exhaustion and cascading failures │
    └─────────────────────────────────────────────────────────────┘
    
    Usage:
        from middleware import BackpressureMiddleware
        app.add_middleware(BackpressureMiddleware, max_queue_size=50)
    """
    
    def __init__(self, app, max_queue_size: int = 50):
        """
        Initialize backpressure middleware.
        
        Args:
            app: The ASGI application
            max_queue_size: Maximum concurrent requests before rejecting
        """
        self.app = app
        self.max_queue_size = max_queue_size
        self.current_queue_size = 0
        
        # Stats for visualization
        self.total_accepted = 0
        self.total_rejected = 0
        self.peak_queue_size = 0
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - called for each request."""
        # Only apply to HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if we're at capacity
        if self.current_queue_size >= self.max_queue_size:
            self.total_rejected += 1
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Server Overloaded",
                    "message": "Backpressure: Too many concurrent requests",
                    "queue_size": self.current_queue_size,
                    "max_queue_size": self.max_queue_size,
                    "retry_after": 1
                }
            )
            await response(scope, receive, send)
            return
        
        # Accept request - increment queue
        self.current_queue_size += 1
        self.total_accepted += 1
        self.peak_queue_size = max(self.peak_queue_size, self.current_queue_size)
        
        try:
            # Process the request
            await self.app(scope, receive, send)
        finally:
            # Request complete - decrement queue
            self.current_queue_size -= 1


def add_backpressure_stats_endpoint(app: FastAPI, middleware: BackpressureMiddleware):
    """
    Add a /queue-stats endpoint to visualize backpressure state.
    
    Usage:
        bp_middleware = BackpressureMiddleware(app, max_queue_size=50)
        add_backpressure_stats_endpoint(app, bp_middleware)
    """
    @app.get("/queue-stats")
    def queue_stats():
        return {
            "current_queue_size": middleware.current_queue_size,
            "max_queue_size": middleware.max_queue_size,
            "utilization_percent": round(
                (middleware.current_queue_size / middleware.max_queue_size) * 100, 1
            ),
            "total_accepted": middleware.total_accepted,
            "total_rejected": middleware.total_rejected,
            "rejection_rate": round(
                (middleware.total_rejected / (middleware.total_accepted + middleware.total_rejected)) * 100, 2
            ) if (middleware.total_accepted + middleware.total_rejected) > 0 else 0,
            "peak_queue_size": middleware.peak_queue_size
        }
