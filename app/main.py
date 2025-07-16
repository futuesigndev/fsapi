import logging
import time
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.dependencies import create_access_token, verify_credentials
from app.api.routes import router  # นำเข้า router จาก routes.py

# Import V1 API routers
from app.api.v1.auth import router as auth_v1_router
from app.api.v1.customer import router as customer_v1_router  
from app.api.v1.sap import router as sap_v1_router
from app.api.v1.health import router as health_v1_router
from app.api.v1.billing import router as billing_v1_router 

# Import monitoring services
from app.services.monitoring_service import monitoring_middleware, get_monitoring_stats

app = FastAPI(
    title="FS Central API",
    description="API Gateway for SAP and Oracle Database Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add custom exception handlers for better debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.error(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed",
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, 'body') else None
        }
    )

@app.exception_handler(ValidationError)
async def pydantic_exception_handler(request: Request, exc: ValidationError):
    logging.error(f"Pydantic validation error on {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Schema validation failed",
            "errors": exc.errors()
        }
    )

# Add monitoring middleware
app.middleware("http")(monitoring_middleware)  

@app.get("/")
async def root():
    """
    API Health Check and Information
    """
    return {
        "api": "FS Central API",
        "version": "1.0.0",
        "status": "healthy",
        "description": "API Gateway for SAP and Oracle Database Integration",
        "endpoints": {
            "legacy": {
                "client_auth": "POST /token",
                "sap_legacy": "POST /api/sap/call-function"
            },
            "v1": {
                "user_auth": "POST /api/v1/auth/login",
                "user_profile": "GET /api/v1/auth/me",
                "customer_search": "GET|POST /api/v1/customers/search",
                "customer_details": "GET /api/v1/customers/{customer_number}",
                "sap_functions": "POST /api/v1/sap/call-function",
                "sap_authorized": "GET /api/v1/sap/functions",
                "health_check": "GET /api/v1/health/health",
                "monitoring": "GET /api/v1/monitoring/stats",
                "billing_create": "POST /api/v1/billing/create/",
                "billing_status_check": "GET /api/v1/billing/delivery/{delivery_doc}/status",
                "billing_types": "GET /api/v1/billing/types",
                "billing_suggest_type": "GET /api/v1/billing/delivery/{delivery_doc}/suggest-type"
            }
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/api/v1/monitoring/stats")
async def monitoring_stats():
    """
    Get comprehensive monitoring and performance statistics
    """
    try:
        stats = get_monitoring_stats()
        return {
            "status": "success",
            "timestamp": time.time(),
            "monitoring_data": stats
        }
    except Exception as e:
        logging.error(f"Monitoring stats error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve monitoring statistics"
        )


@app.post("/token")
async def token(
    grant_type: str = Form(default=""),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    """
    Legacy Client Authentication Endpoint
    
    Returns JWT access token for client authentication.
    Token expires in 120 minutes (2 hours).
    
    Error Responses:
    - 401: Invalid credentials
    - 422: Validation error
    
    Success Response:
    {
        "access_token": "jwt_token_here",
        "token_type": "bearer",
        "expires_in": 7200
    }
    """
    # ตรวจสอบ CLIENT_ID และ CLIENT_SECRET
    is_verified = verify_credentials(client_id, client_secret)

    if not is_verified:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "INVALID_CREDENTIALS",
                "message": "Invalid CLIENT_ID or CLIENT_SECRET",
                "timestamp": time.time(),
                "type": "authentication_error"
            }
        )

    # สร้าง Token ที่ไม่มี authorized_functions
    access_token = create_access_token(data={"sub": client_id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 7200  # 120 minutes in seconds
    }


# รวมเส้นทาง API จาก router ใน app/api/routes.py (Legacy APIs)
app.include_router(router, prefix="/api", tags=["Legacy APIs"])

# รวมเส้นทาง V1 APIs
app.include_router(
    auth_v1_router, 
    prefix="/api/v1/auth", 
    tags=["Authentication - v1"]
)

app.include_router(
    customer_v1_router, 
    prefix="/api/v1/customers", 
    tags=["Customer Management - v1"]
)

app.include_router(
    sap_v1_router, 
    prefix="/api/v1/sap", 
    tags=["SAP Integration - v1"]
)

app.include_router(
    health_v1_router, 
    prefix="/api/v1/health", 
    tags=["System Health - v1"]
)

app.include_router(
    billing_v1_router,
    prefix="/api/v1/billing", 
    tags=["Billing - v1"]
)

# รัน Uvicorn เมื่อไฟล์นี้ถูกเรียกใช้งานโดยตรง
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True, workers=4, proxy_headers=True)
