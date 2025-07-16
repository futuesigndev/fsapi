"""
Simple in-memory cache utility for FastAPI endpoints (for demo/prototype use only)
"""
import time
from typing import Any, Callable, Optional
from functools import wraps

_cache_store = {}


def cache_response(ttl_seconds: int = 60):
    """
    Decorator to cache function responses in memory for a given TTL (seconds)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (func.__name__, str(args), str(kwargs))
            now = time.time()
            if key in _cache_store:
                value, expires = _cache_store[key]
                if now < expires:
                    return value
            result = await func(*args, **kwargs)
            _cache_store[key] = (result, now + ttl_seconds)
            return result
        return wrapper
    return decorator
