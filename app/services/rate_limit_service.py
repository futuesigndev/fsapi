"""
Rate Limiting Service - Request rate limiting and throttling
Provides rate limiting functionality for API endpoints
"""
import time
import logging
from typing import Dict, Optional
from threading import Lock
from collections import defaultdict, deque
from fastapi import HTTPException, Request
import hashlib


class RateLimiter:
    """
    Token bucket rate limiter implementation
    Supports different rate limits for different clients/users
    """
    
    def __init__(self):
        self._buckets: Dict[str, Dict] = {}
        self._lock = Lock()
    
    def _get_client_key(self, identifier: str, endpoint: str = "default") -> str:
        """
        Generate unique key for client and endpoint combination
        """
        return f"{identifier}:{endpoint}"
    
    def is_allowed(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 3600,  # 1 hour
        endpoint: str = "default"
    ) -> tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            identifier: Client/user identifier
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            endpoint: Specific endpoint (for endpoint-specific limits)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        current_time = time.time()
        client_key = self._get_client_key(identifier, endpoint)
        
        with self._lock:
            if client_key not in self._buckets:
                self._buckets[client_key] = {
                    "requests": deque(),
                    "max_requests": max_requests,
                    "window_seconds": window_seconds
                }
            
            bucket = self._buckets[client_key]
            requests = bucket["requests"]
            
            # Remove old requests outside the window
            while requests and requests[0] <= current_time - window_seconds:
                requests.popleft()
            
            # Check if limit exceeded
            if len(requests) >= max_requests:
                # Calculate retry after time
                oldest_request = requests[0] if requests else current_time
                retry_after = int(oldest_request + window_seconds - current_time)
                
                rate_info = {
                    "allowed": False,
                    "limit": max_requests,
                    "remaining": 0,
                    "reset_time": int(oldest_request + window_seconds),
                    "retry_after": max(retry_after, 1)
                }
                
                logging.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
                return False, rate_info
            
            # Add current request
            requests.append(current_time)
            
            rate_info = {
                "allowed": True,
                "limit": max_requests,
                "remaining": max_requests - len(requests),
                "reset_time": int(current_time + window_seconds),
                "retry_after": 0
            }
            
            return True, rate_info
    
    def get_stats(self, identifier: str, endpoint: str = "default") -> Optional[Dict]:
        """
        Get current rate limit statistics for client
        """
        client_key = self._get_client_key(identifier, endpoint)
        current_time = time.time()
        
        with self._lock:
            if client_key not in self._buckets:
                return None
            
            bucket = self._buckets[client_key]
            requests = bucket["requests"]
            window_seconds = bucket["window_seconds"]
            max_requests = bucket["max_requests"]
            
            # Clean old requests
            while requests and requests[0] <= current_time - window_seconds:
                requests.popleft()
            
            return {
                "limit": max_requests,
                "used": len(requests),
                "remaining": max_requests - len(requests),
                "window_seconds": window_seconds,
                "requests_timestamps": list(requests)
            }
    
    def cleanup_old_buckets(self, max_age_seconds: int = 3600):
        """
        Clean up old unused buckets to prevent memory leaks
        """
        current_time = time.time()
        
        with self._lock:
            keys_to_remove = []
            
            for client_key, bucket in self._buckets.items():
                requests = bucket["requests"]
                window_seconds = bucket["window_seconds"]
                
                # If no recent requests, mark for removal
                if not requests or (current_time - requests[-1]) > max_age_seconds:
                    keys_to_remove.append(client_key)
            
            for key in keys_to_remove:
                del self._buckets[key]
            
            if keys_to_remove:
                logging.debug(f"Cleaned up {len(keys_to_remove)} old rate limit buckets")


class RateLimitService:
    """
    Service for managing rate limits across the application
    """
    
    _limiter = RateLimiter()
    
    # Rate limit configurations
    RATE_LIMITS = {
        "default": {"max_requests": 100, "window_seconds": 3600},  # 100/hour
        "auth": {"max_requests": 10, "window_seconds": 300},       # 10/5min for auth
        "sap": {"max_requests": 50, "window_seconds": 3600},       # 50/hour for SAP
        "customer": {"max_requests": 200, "window_seconds": 3600}, # 200/hour for customers
    }
    
    @classmethod
    def check_rate_limit(
        cls,
        identifier: str,
        endpoint_type: str = "default",
        custom_limit: Optional[Dict] = None
    ) -> tuple[bool, Dict[str, any]]:
        """
        Check rate limit for specific client and endpoint type
        """
        # Use custom limit or default from configuration
        if custom_limit:
            limit_config = custom_limit
        else:
            limit_config = cls.RATE_LIMITS.get(endpoint_type, cls.RATE_LIMITS["default"])
        
        return cls._limiter.is_allowed(
            identifier=identifier,
            max_requests=limit_config["max_requests"],
            window_seconds=limit_config["window_seconds"],
            endpoint=endpoint_type
        )
    
    @classmethod
    def get_client_stats(cls, identifier: str, endpoint_type: str = "default") -> Optional[Dict]:
        """
        Get rate limit statistics for client
        """
        return cls._limiter.get_stats(identifier, endpoint_type)
    
    @classmethod
    def cleanup_old_data(cls):
        """
        Clean up old rate limit data
        """
        cls._limiter.cleanup_old_buckets()
    
    @classmethod
    def get_client_identifier(cls, request: Request, token_data: Optional[Dict] = None) -> str:
        """
        Generate client identifier from request and token data
        """
        if token_data:
            # Use authenticated user/client ID
            if "client_id" in token_data:
                return f"client:{token_data['client_id']}"
            elif "employee_id" in token_data:
                return f"user:{token_data['employee_id']}"
        
        # Fall back to IP address for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"
        
        # Use X-Forwarded-For if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"


def create_rate_limit_dependency(endpoint_type: str = "default", custom_limit: Optional[Dict] = None):
    """
    Dependency factory for rate limiting
    """
    def rate_limit_dependency(request: Request, token_data: Optional[Dict] = None):
        """
        Rate limiting dependency
        """
        try:
            # Get client identifier
            identifier = RateLimitService.get_client_identifier(request, token_data)
            
            # Check rate limit
            is_allowed, rate_info = RateLimitService.check_rate_limit(
                identifier=identifier,
                endpoint_type=endpoint_type,
                custom_limit=custom_limit
            )
            
            if not is_allowed:
                # Add rate limit headers to error response
                headers = {
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset_time"]),
                    "Retry-After": str(rate_info["retry_after"])
                }
                
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again after {rate_info['retry_after']} seconds.",
                    headers=headers
                )
            
            # Log successful rate limit check
            logging.debug(f"Rate limit check passed for {identifier} on {endpoint_type}")
            
            return rate_info
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Rate limiting error: {e}")
            # Don't block requests on rate limiting errors
            return {"allowed": True, "limit": 0, "remaining": 0}
    
    return rate_limit_dependency


# Pre-configured rate limit dependencies
DefaultRateLimit = create_rate_limit_dependency("default")
AuthRateLimit = create_rate_limit_dependency("auth")
SAPRateLimit = create_rate_limit_dependency("sap")
CustomerRateLimit = create_rate_limit_dependency("customer")
