"""
Middleware Package for Node.py

This package provides composable middleware for building resilient distributed systems.
Students can enable these middleware via CLI flags or direct configuration.

Phase 1 - Resilience:
- RateLimiterMiddleware: Token bucket rate limiting
- BackpressureMiddleware: Queue management with 429 responses
- CircuitBreakerMiddleware: Failure detection with fast-fail
- ServiceDiscoveryMiddleware: Registry integration with heartbeats

Phase 2 - Distribution:
- ShardingMiddleware: Consistent hashing for data distribution
- ReplicationMiddleware: Leader-follower replication
- LeaderlessReplicationMiddleware: Gossip-based eventual consistency
"""

# Phase 1: Resilience
from .rate_limiter import RateLimiterMiddleware
from .backpressure import BackpressureMiddleware
from .circuit_breaker import CircuitBreakerMiddleware
from .service_discovery import ServiceDiscoveryMiddleware

# Phase 2: Distribution
from .sharding import ShardingMiddleware
from .replication import ReplicationMiddleware
from .leaderless_replication import LeaderlessReplicationMiddleware

__all__ = [
    # Phase 1
    "RateLimiterMiddleware",
    "BackpressureMiddleware", 
    "CircuitBreakerMiddleware",
    "ServiceDiscoveryMiddleware",
    # Phase 2
    "ShardingMiddleware",
    "ReplicationMiddleware",
    "LeaderlessReplicationMiddleware",
]

