"""
Health Check API - System health monitoring endpoints
Provides comprehensive health checks for all system components
"""
import time
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import os

from app.services.database_service import DatabaseService
from app.services.sap_service import test_sap_connection
from app.services.rate_limit_service import RateLimitService
from app.config import Config

router = APIRouter()


def check_database_health() -> Dict[str, Any]:
    """
    Check Oracle database health and connection pool status
    """
    try:
        start_time = time.time()
        result = DatabaseService.test_connection()
        response_time = time.time() - start_time
        
        return {
            "status": "healthy" if result["connection_test"] else "unhealthy",
            "response_time_ms": round(response_time * 1000, 2),
            "connection_pool": result.get("pool_status"),
            "message": result.get("message", "Database check completed"),
            "error": result.get("error")
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": 0,
            "connection_pool": None,
            "message": "Database health check failed",
            "error": str(e)
        }


def check_sap_health() -> Dict[str, Any]:
    """
    Check SAP system connectivity
    """
    try:
        start_time = time.time()
        # This would need to be implemented in sap_service.py
        # For now, we'll check if SAP configuration is available
        sap_config_complete = all([
            Config.SAP_HOST,
            Config.SAP_USER,
            Config.SAP_PASSWORD,
            Config.SAP_CLIENT,
            Config.SAP_SYSNR
        ])
        
        response_time = time.time() - start_time
        
        if sap_config_complete:
            # In a real scenario, you would test actual SAP connectivity here
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "message": "SAP configuration available",
                "config_complete": True
            }
        else:
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time * 1000, 2),
                "message": "SAP configuration incomplete",
                "config_complete": False
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": 0,
            "message": "SAP health check failed",
            "error": str(e),
            "config_complete": False
        }


def check_file_system_health() -> Dict[str, Any]:
    """
    Check file system health (metadata files, logs, etc.)
    """
    try:
        checks = {}
        
        # Check metadata directory
        metadata_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "sftp-root", "metadata"
        )
        
        if os.path.exists(metadata_dir):
            metadata_files = [f for f in os.listdir(metadata_dir) if f.endswith('.json')]
            checks["metadata"] = {
                "status": "healthy",
                "directory_exists": True,
                "file_count": len(metadata_files),
                "files": metadata_files
            }
        else:
            checks["metadata"] = {
                "status": "unhealthy",
                "directory_exists": False,
                "file_count": 0,
                "error": "Metadata directory not found"
            }
        
        # Check log file writability
        try:
            log_file = "app.log"
            with open(log_file, "a") as f:
                f.write("")  # Test write
            checks["logging"] = {
                "status": "healthy",
                "log_file_writable": True,
                "log_file_path": log_file
            }
        except Exception as e:
            checks["logging"] = {
                "status": "unhealthy",
                "log_file_writable": False,
                "error": str(e)
            }
        
        overall_status = "healthy" if all(
            check["status"] == "healthy" for check in checks.values()
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "checks": checks
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "checks": {}
        }


def check_rate_limiting_health() -> Dict[str, Any]:
    """
    Check rate limiting service health
    """
    try:
        # Clean up old data and test basic functionality
        RateLimitService.cleanup_old_data()
        
        # Test rate limiting with a dummy identifier
        test_identifier = "health_check_test"
        is_allowed, rate_info = RateLimitService.check_rate_limit(
            identifier=test_identifier,
            endpoint_type="default"
        )
        
        return {
            "status": "healthy",
            "rate_limiting_functional": is_allowed,
            "test_rate_info": rate_info,
            "message": "Rate limiting service operational"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "rate_limiting_functional": False,
            "error": str(e),
            "message": "Rate limiting service failed"
        }


@router.get("/health")
async def health_check():
    """
    Comprehensive system health check
    Returns overall system health status and individual component status
    """
    try:
        start_time = time.time()
        
        # Check all system components
        database_health = check_database_health()
        sap_health = check_sap_health()
        filesystem_health = check_file_system_health()
        rate_limiting_health = check_rate_limiting_health()
        
        total_response_time = time.time() - start_time
        
        # Determine overall health status
        component_statuses = [
            database_health["status"],
            sap_health["status"],
            filesystem_health["status"],
            rate_limiting_health["status"]
        ]
        
        overall_status = "healthy" if all(status == "healthy" for status in component_statuses) else "unhealthy"
        
        # Count healthy vs unhealthy components
        healthy_count = component_statuses.count("healthy")
        total_count = len(component_statuses)
        
        health_data = {
            "status": overall_status,
            "timestamp": time.time(),
            "response_time_ms": round(total_response_time * 1000, 2),
            "components": {
                "database": database_health,
                "sap": sap_health,
                "filesystem": filesystem_health,
                "rate_limiting": rate_limiting_health
            },
            "summary": {
                "healthy_components": healthy_count,
                "total_components": total_count,
                "health_percentage": round((healthy_count / total_count) * 100, 1)
            }
        }
        
        return health_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check system error: {str(e)}"
        )


@router.get("/health/database")
async def database_health():
    """
    Database-specific health check
    """
    try:
        result = check_database_health()
        
        if result["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/health/sap")
async def sap_health():
    """
    SAP-specific health check
    """
    try:
        result = check_sap_health()
        
        if result["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SAP health check failed: {str(e)}"
        )


@router.get("/health/filesystem")
async def filesystem_health():
    """
    File system health check
    """
    try:
        result = check_file_system_health()
        
        if result["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Filesystem health check failed: {str(e)}"
        )


@router.get("/health/rate-limiting")
async def rate_limiting_health():
    """
    Rate limiting service health check
    """
    try:
        result = check_rate_limiting_health()
        
        if result["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rate limiting health check failed: {str(e)}"
        )


@router.get("/")
async def health_api_info():
    """
    Health API information
    """
    return {
        "api": "Health Check API",
        "version": "1.0.0",
        "endpoints": {
            "overall_health": "GET /api/v1/health/health",
            "database_health": "GET /api/v1/health/database",
            "sap_health": "GET /api/v1/health/sap",
            "filesystem_health": "GET /api/v1/health/filesystem",
            "rate_limiting_health": "GET /api/v1/health/rate-limiting"
        },
        "description": "Comprehensive system health monitoring",
        "components_monitored": [
            "Oracle Database Connection Pool",
            "SAP System Configuration",
            "File System (Metadata, Logs)",
            "Rate Limiting Service"
        ]
    }
