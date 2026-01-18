"""
Base Strategy Interfaces

These abstract base classes define the contracts for pluggable strategies.
While we currently implement one strategy per middleware, this design allows
future extension with additional strategies.

Example: Students could later implement FixedWindowStrategy or SlidingWindowStrategy
by extending RateLimitStrategy.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class RateLimitStrategy(ABC):
    """
    Base class for rate limiting algorithms.
    
    Implementations must define is_allowed() which determines
    whether a request from a given client should be permitted.
    """
    
    @abstractmethod
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a request from client_id should be allowed.
        
        Args:
            client_id: Unique identifier for the client (e.g., IP address)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        pass


class LoadBalanceStrategy(ABC):
    """
    Base class for load balancing algorithms.
    
    Implementations must define select_node() which chooses
    which backend node should handle the next request.
    """
    
    @abstractmethod
    def select_node(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best node to handle the next request.
        
        Args:
            nodes: List of available nodes, each with 'url' and optional 'active_requests'
            
        Returns:
            The selected node dictionary
        """
        pass
    
    def on_request_start(self, node: Dict[str, Any]) -> None:
        """Called when a request to a node begins. Override for tracking."""
        pass
    
    def on_request_end(self, node: Dict[str, Any]) -> None:
        """Called when a request to a node completes. Override for tracking."""
        pass


class BackpressureStrategy(ABC):
    """
    Base class for backpressure handling algorithms.
    
    Implementations define how to handle requests when the system is overloaded.
    """
    
    @abstractmethod
    def should_accept(self, current_queue_size: int, max_queue_size: int) -> bool:
        """
        Determine if a new request should be accepted.
        
        Args:
            current_queue_size: Number of requests currently queued
            max_queue_size: Maximum allowed queue size
            
        Returns:
            True if request should be accepted, False to reject with 429
        """
        pass
