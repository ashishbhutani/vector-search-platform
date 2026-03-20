"""vector-search-service package."""

from .routing import RouterConfig, ShardRouter, create_router

__all__ = ["RouterConfig", "ShardRouter", "create_router"]
