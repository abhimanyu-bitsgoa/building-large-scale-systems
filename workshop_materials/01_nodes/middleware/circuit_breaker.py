"""
Circuit Breaker Middleware

Implements the Circuit Breaker pattern to prevent cascading failures.
When a downstream service is failing, the circuit "opens" and requests
fail fast without even attempting the call.

This is a complete implementation - students observe the behavior.
"""

import time
from enum import Enum
from fastapi import FastAPI
from fastapi.responses import JSONResponse


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"       # 🟢 Normal operation - requests flow through
    OPEN = "OPEN"           # 🔴 Failing - reject requests immediately (fast fail)
    HALF_OPEN = "HALF_OPEN" # 🟡 Testing - allow one request to test recovery


class CircuitBreakerMiddleware:
    """
    ASGI Middleware that implements the Circuit Breaker pattern.
    
    State Machine:
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │   🟢 CLOSED ──(N failures)──> 🔴 OPEN                       │
    │       ↑                          │                          │
    │       │                     (timeout)                       │
    │       │                          ↓                          │
    │   (success)               🟡 HALF_OPEN                      │
    │       │                          │                          │
    │       └──────────────────────────┘                          │
    │                               (failure) ──> 🔴 OPEN         │
    └─────────────────────────────────────────────────────────────┘
    
    Usage:
        from middleware import CircuitBreakerMiddleware
        app.add_middleware(CircuitBreakerMiddleware, failure_threshold=3)
    """
    
    def __init__(self, app, failure_threshold: int = 3, recovery_timeout: int = 5):
        """
        Initialize circuit breaker middleware.
        
        Args:
            app: The ASGI application
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Seconds to wait before trying HALF_OPEN
        """
        self.app = app
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        
        # Stats
        self.total_requests = 0
        self.total_fast_fails = 0
        self.state_changes = []
    
    def _change_state(self, new_state: CircuitState):
        """Record a state change."""
        old_state = self.state
        self.state = new_state
        self.state_changes.append({
            "from": old_state.value,
            "to": new_state.value,
            "time": time.time()
        })
        # Keep only last 10 changes
        if len(self.state_changes) > 10:
            self.state_changes.pop(0)
    
    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed through."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.recovery_timeout:
                self._change_state(CircuitState.HALF_OPEN)
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Allow one test request
            return True
        
        return False
    
    def record_success(self):
        """Record a successful request."""
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN:
            # Recovery successful!
            self._change_state(CircuitState.CLOSED)
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Recovery failed - go back to OPEN
            self._change_state(CircuitState.OPEN)
        elif self.failure_count >= self.failure_threshold:
            # Threshold exceeded - open circuit
            self._change_state(CircuitState.OPEN)
    
    async def __call__(self, scope, receive, send):
        """ASGI interface - called for each request."""
        # Only apply to HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        self.total_requests += 1
        
        # Check if circuit allows request
        if not self._should_allow_request():
            self.total_fast_fails += 1
            response = JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Circuit breaker is OPEN - fast failing",
                    "circuit_state": self.state.value,
                    "retry_after": self.recovery_timeout
                }
            )
            await response(scope, receive, send)
            return
        
        # Track response status
        response_status = [None]  # Use list to capture in nested function
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
            
            # Check if response was successful (2xx or 3xx)
            if response_status[0] and response_status[0] < 400:
                self.record_success()
            elif response_status[0] and response_status[0] >= 500:
                self.record_failure()
        except Exception as e:
            self.record_failure()
            raise


def add_circuit_status_endpoint(app: FastAPI, middleware: CircuitBreakerMiddleware):
    """
    Add a /circuit-status endpoint to visualize circuit breaker state.
    
    Usage:
        cb_middleware = CircuitBreakerMiddleware(app, failure_threshold=3)
        add_circuit_status_endpoint(app, cb_middleware)
    """
    @app.get("/circuit-status")
    def circuit_status():
        state_emoji = {
            CircuitState.CLOSED: "🟢",
            CircuitState.OPEN: "🔴",
            CircuitState.HALF_OPEN: "🟡"
        }
        return {
            "state": middleware.state.value,
            "state_display": f"{state_emoji[middleware.state]} {middleware.state.value}",
            "failure_count": middleware.failure_count,
            "failure_threshold": middleware.failure_threshold,
            "total_requests": middleware.total_requests,
            "total_fast_fails": middleware.total_fast_fails,
            "success_count": middleware.success_count,
            "recovery_timeout": middleware.recovery_timeout,
            "last_failure_time": middleware.last_failure_time,
            "recent_state_changes": middleware.state_changes[-5:]
        }
