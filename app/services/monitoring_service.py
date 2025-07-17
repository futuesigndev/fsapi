"""
Enhanced Logging and Monitoring Service
Provides structured logging, request tracking, and performance monitoring
"""
import time
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request, Response
from functools import wraps
from threading import Lock
from collections import defaultdict, deque
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.config import Config
from app.schemas.sap import SAPFunctionRequest, SAPFunctionResponse

class PerformanceMonitor:
    """
    Performance monitoring and metrics collection
    """
    
    def __init__(self):
        self._metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "recent_requests": deque(maxlen=100)
        })
        self._lock = Lock()
    
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int):
        """
        Record request metrics
        """
        key = f"{method}:{endpoint}"
        
        with self._lock:
            metrics = self._metrics[key]
            metrics["count"] += 1
            metrics["total_time"] += duration
            metrics["min_time"] = min(metrics["min_time"], duration)
            metrics["max_time"] = max(metrics["max_time"], duration)
            
            # Store recent request info
            metrics["recent_requests"].append({
                "timestamp": time.time(),
                "duration": duration,
                "status_code": status_code
            })
    
    def get_endpoint_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """
        Get performance statistics for endpoint(s)
        """
        with self._lock:
            if endpoint:
                if endpoint in self._metrics:
                    metrics = self._metrics[endpoint]
                    return self._calculate_stats(endpoint, metrics)
                return {}
            
            # Return all endpoint stats
            stats = {}
            for endpoint_key, metrics in self._metrics.items():
                stats[endpoint_key] = self._calculate_stats(endpoint_key, metrics)
            
            return stats
    
    def _calculate_stats(self, endpoint: str, metrics: Dict) -> Dict[str, Any]:
        """
        Calculate performance statistics
        """
        count = metrics["count"]
        if count == 0:
            return {"endpoint": endpoint, "count": 0}
        
        avg_time = metrics["total_time"] / count
        recent_requests = list(metrics["recent_requests"])
        
        # Calculate recent performance (last 10 requests)
        recent_times = [req["duration"] for req in recent_requests[-10:]]
        recent_avg = sum(recent_times) / len(recent_times) if recent_times else 0
        
        # Status code distribution
        status_codes = defaultdict(int)
        for req in recent_requests:
            status_codes[req["status_code"]] += 1
        
        return {
            "endpoint": endpoint,
            "total_requests": count,
            "average_response_time": round(avg_time, 3),
            "min_response_time": round(metrics["min_time"], 3),
            "max_response_time": round(metrics["max_time"], 3),
            "recent_avg_response_time": round(recent_avg, 3),
            "status_code_distribution": dict(status_codes),
            "recent_request_count": len(recent_requests)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get overall performance summary
        """
        with self._lock:
            total_requests = sum(m["count"] for m in self._metrics.values())
            total_time = sum(m["total_time"] for m in self._metrics.values())
            
            if total_requests == 0:
                return {"total_requests": 0, "average_response_time": 0}
            
            avg_response_time = total_time / total_requests
            
            # Find slowest and fastest endpoints
            endpoint_stats = self.get_endpoint_stats()
            
            slowest = max(endpoint_stats.values(), key=lambda x: x.get("average_response_time", 0)) if endpoint_stats else None
            fastest = min(endpoint_stats.values(), key=lambda x: x.get("average_response_time", float('inf'))) if endpoint_stats else None
            
            return {
                "total_requests": total_requests,
                "average_response_time": round(avg_response_time, 3),
                "total_endpoints": len(self._metrics),
                "slowest_endpoint": slowest,
                "fastest_endpoint": fastest
            }


class StructuredLogger:
    """
    Enhanced structured logging with JSON output and request tracking
    """
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self._setup_loggers()
    
    def _setup_loggers(self):
        """
        Setup structured loggers
        """
        # Request logger (separate from main app log)
        self.request_logger = logging.getLogger("fsapi.requests")
        self.request_logger.setLevel(logging.INFO)
        
        # Performance logger
        self.performance_logger = logging.getLogger("fsapi.performance")
        self.performance_logger.setLevel(logging.INFO)
        
        # Security logger
        self.security_logger = logging.getLogger("fsapi.security")
        self.security_logger.setLevel(logging.WARNING)
        
        # Setup file handlers if they don't exist
        if not self.request_logger.handlers:
            request_handler = logging.FileHandler("requests.log", encoding="utf-8")
            request_formatter = logging.Formatter('%(asctime)s - %(message)s')
            request_handler.setFormatter(request_formatter)
            self.request_logger.addHandler(request_handler)
        
        if not self.performance_logger.handlers:
            perf_handler = logging.FileHandler("performance.log", encoding="utf-8")
            perf_formatter = logging.Formatter('%(asctime)s - %(message)s')
            perf_handler.setFormatter(perf_formatter)
            self.performance_logger.addHandler(perf_handler)
        
        if not self.security_logger.handlers:
            security_handler = logging.FileHandler("security.log", encoding="utf-8")
            security_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            security_handler.setFormatter(security_formatter)
            self.security_logger.addHandler(security_handler)
    
    def log_request(self, request_data: Dict[str, Any]):
        """
        Log request in structured format
        """
        # Skip logging if DISABLE_REQUEST_LOGGING is set
        if os.getenv("DISABLE_REQUEST_LOGGING", "false").lower() == "true":
            return
            
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "request",
            **request_data
        }
        
        self.request_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_performance(self, perf_data: Dict[str, Any]):
        """
        Log performance metrics
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "performance",
            **perf_data
        }
        
        self.performance_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_security_event(self, event_data: Dict[str, Any], level: str = "WARNING"):
        """
        Log security-related events
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "security",
            **event_data
        }
        
        log_message = json.dumps(log_entry, ensure_ascii=False)
        
        if level == "WARNING":
            self.security_logger.warning(log_message)
        elif level == "ERROR":
            self.security_logger.error(log_message)
        elif level == "CRITICAL":
            self.security_logger.critical(log_message)


class RequestTracker:
    """
    Request tracking and correlation
    """
    
    def __init__(self):
        self.active_requests = {}
        self._lock = Lock()
    
    def start_request(self, request_id: str, request_data: Dict[str, Any]):
        """
        Start tracking a request
        """
        with self._lock:
            self.active_requests[request_id] = {
                "start_time": time.time(),
                "data": request_data
            }
    
    def end_request(self, request_id: str, response_data: Dict[str, Any]):
        """
        End request tracking and calculate duration
        """
        with self._lock:
            if request_id in self.active_requests:
                request_info = self.active_requests.pop(request_id)
                duration = time.time() - request_info["start_time"]
                
                return {
                    "duration": duration,
                    "request_data": request_info["data"],
                    "response_data": response_data
                }
        return None
    
    def get_active_requests_count(self) -> int:
        """
        Get number of currently active requests
        """
        with self._lock:
            return len(self.active_requests)


# Global monitoring instances
structured_logger = StructuredLogger()
request_tracker = RequestTracker()


async def monitoring_middleware(request: Request, call_next):
    """
    Middleware for request monitoring and logging
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Start request tracking
    start_time = time.time()
    
    # Extract request information
    request_data = {
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "content_type": request.headers.get("content-type"),
        "content_length": request.headers.get("content-length")
    }
    
    # Add forwarded IP if behind proxy
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        request_data["forwarded_for"] = forwarded_for.split(",")[0].strip()
    
    # Start tracking
    request_tracker.start_request(request_id, request_data)
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Response data
        response_data = {
            "status_code": response.status_code,
            "response_time": round(duration, 3)
        }
        
        # End tracking
        tracking_result = request_tracker.end_request(request_id, response_data)
        
        if tracking_result:
            # Log request
            full_request_data = {
                **tracking_result["request_data"],
                **tracking_result["response_data"],
                "duration": round(tracking_result["duration"], 3)
            }
            
            structured_logger.log_request(full_request_data)
            
            # Record performance metrics
            structured_logger.performance_monitor.record_request(
                endpoint=request.url.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code
            )
            
            # Log slow requests
            if duration > 1.0:  # Log requests slower than 1 second
                structured_logger.log_performance({
                    "event": "slow_request",
                    "request_id": request_id,
                    "endpoint": request.url.path,
                    "method": request.method,
                    "duration": round(duration, 3),
                    "status_code": response.status_code
                })
        
        # Add response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = str(round(duration * 1000, 2))
        
        return response
        
    except Exception as e:
        # Log error
        duration = time.time() - start_time
        
        error_data = {
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration": round(duration, 3),
            "endpoint": request.url.path,
            "method": request.method
        }
        
        structured_logger.log_security_event(error_data, "ERROR")
        
        # Record error in performance metrics
        structured_logger.performance_monitor.record_request(
            endpoint=request.url.path,
            method=request.method,
            duration=duration,
            status_code=500
        )
        
        raise


def log_security_event(event_type: str, details: Dict[str, Any], level: str = "WARNING"):
    """
    Helper function to log security events
    """
    event_data = {
        "event_type": event_type,
        **details
    }
    
    structured_logger.log_security_event(event_data, level)


def get_monitoring_stats() -> Dict[str, Any]:
    """
    Get comprehensive monitoring statistics
    """
    return {
        "performance": structured_logger.performance_monitor.get_summary(),
        "active_requests": request_tracker.get_active_requests_count(),
        "endpoint_stats": structured_logger.performance_monitor.get_endpoint_stats()
    }
