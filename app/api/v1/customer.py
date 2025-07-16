# /api/v1/customers.py
"""
Customer Management API V1 - Customer data endpoints
Handles customer search and detail retrieval
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import uuid

from app.schemas.customer import (
    CustomerSearchRequest, 
    CustomerSearchResponse, 
    CustomerDetailResponse,
    CustomerValidationResponse,
    CustomerCreateRequest,
    CustomerCreateResponse,
    CustomerSpecResponse,
    StandardError, ErrorCode
)
from app.services.customer_service import CustomerService
from app.dependencies_v1 import verify_user_token, verify_any_token
from app.schemas.token import TokenData
from app.services.rate_limit_service import CustomerRateLimit
from app.utils.cache import cache_response

router = APIRouter()


def error_response(code: ErrorCode, message: str, details: str = None, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content=StandardError(
            code=code,
            message=message,
            details=details,
            timestamp=datetime.utcnow().isoformat(),
            request_id=str(uuid.uuid4())
        ).dict()
    )


@router.get("/search", response_model=CustomerSearchResponse, responses={400: {"model": StandardError}, 500: {"model": StandardError}})
async def search_customers_get(
    customer_number: Optional[str] = Query(None, description="Customer number (KUNNR)"),
    customer_name: Optional[str] = Query(None, description="Customer name (NAME1/NAME2)"),
    city: Optional[str] = Query(None, description="City (ORT01)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    current_user: TokenData = Depends(verify_any_token),
    _rate_limit = Depends(CustomerRateLimit)
):
    """
    Search customers using query parameters (GET method)
    Supports search by customer number, name, or city
    """
    try:
        # Log the search request
        search_params = {
            "customer_number": customer_number,
            "customer_name": customer_name,
            "city": city,
            "limit": limit
        }
        
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer search request from {user_id}: {search_params}")
        
        # Validate at least one search criteria
        if not any([customer_number, customer_name, city]):
            return error_response(
                code=ErrorCode.INVALID_INPUT,
                message="At least one search criteria is required: customer_number, customer_name, or city",
                status_code=400
            )
        
        # Perform search
        result = CustomerService.search_customers(
            customer_number=customer_number,
            customer_name=customer_name,
            city=city,
            limit=limit
        )
        
        if result["status"] == "error":
            return error_response(
                code=ErrorCode.DATABASE_ERROR,
                message=result["message"],
                status_code=500
            )
        
        logging.debug(f"Customer search completed: {result['total_records']} records found")
        
        return CustomerSearchResponse(
            status=result["status"],
            message=result["message"],
            total_records=result["total_records"],
            customers=result["customers"]
        )
        
    except Exception as e:
        logging.error(f"Customer search error: {e}")
        return error_response(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Internal server error during customer search",
            details=str(e),
            status_code=500
        )


@router.post("/search", response_model=CustomerSearchResponse, responses={400: {"model": StandardError}, 500: {"model": StandardError}})
async def search_customers_post(
    search_request: CustomerSearchRequest,
    current_user: TokenData = Depends(verify_any_token),
    _rate_limit = Depends(CustomerRateLimit)
):
    """
    Search customers using JSON request body (POST method)
    Supports search by customer number, name, or city
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer search request from {user_id}: {search_request.dict()}")
        
        # Validate at least one search criteria
        if not any([
            search_request.customer_number,
            search_request.customer_name,
            search_request.city
        ]):
            return error_response(
                code=ErrorCode.INVALID_INPUT,
                message="At least one search criteria is required: customer_number, customer_name, or city",
                status_code=400
            )
        
        # Set default limit if not provided
        limit = search_request.limit or 50
        
        # Perform search
        result = CustomerService.search_customers(
            customer_number=search_request.customer_number,
            customer_name=search_request.customer_name,
            city=search_request.city,
            limit=limit
        )
        
        if result["status"] == "error":
            return error_response(
                code=ErrorCode.DATABASE_ERROR,
                message=result["message"],
                status_code=500
            )
        
        logging.debug(f"Customer search completed: {result['total_records']} records found")
        
        return CustomerSearchResponse(
            status=result["status"],
            message=result["message"],
            total_records=result["total_records"],
            customers=result["customers"]
        )
        
    except Exception as e:
        logging.error(f"Customer search error: {e}")
        return error_response(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Internal server error during customer search",
            details=str(e),
            status_code=500
        )


@router.get("/lookup", response_model=CustomerSearchResponse, responses={400: {"model": StandardError}, 500: {"model": StandardError}})
@cache_response(ttl_seconds=30)  # Cache lookup for 30 seconds
async def lookup_customer(
    name: Optional[str] = Query(None, description="Customer name (NAME1/NAME2)"),
    phone: Optional[str] = Query(None, description="Phone number (TELF1)"),
    tax_id: Optional[str] = Query(None, description="Tax ID (STCD3)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: TokenData = Depends(verify_any_token),
    _rate_limit = Depends(CustomerRateLimit)
):
    """
    Lookup customers by name, phone, or tax ID for quick customer selection
    Optimized for customer lookup during data entry
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer lookup request from {user_id}")
        
        # Validate at least one search criteria
        if not any([name, phone, tax_id]):
            return error_response(
                code=ErrorCode.INVALID_INPUT,
                message="At least one search criteria is required: name, phone, or tax_id",
                status_code=400
            )
        
        # Perform lookup with specialized query
        result = CustomerService.lookup_customers(
            name=name,
            phone=phone,
            tax_id=tax_id,
            limit=limit
        )
        
        if result["status"] == "error":
            return error_response(
                code=ErrorCode.DATABASE_ERROR,
                message=result["message"],
                status_code=500
            )
        
        logging.debug(f"Customer lookup completed: {result['total_records']} records found")
        
        return CustomerSearchResponse(
            status=result["status"],
            message=result["message"],
            total_records=result["total_records"],
            customers=result["customers"]
        )
        
    except Exception as e:
        logging.error(f"Customer lookup error: {e}")
        return error_response(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Internal server error during customer lookup",
            details=str(e),
            status_code=500
        )


@router.get("/{customer_number}", response_model=CustomerDetailResponse)
async def get_customer_details(
    customer_number: str,
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get detailed information for specific customer by customer number
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer detail request from {user_id} for customer: {customer_number}")
        
        # Validate customer number format (basic validation)
        if not customer_number or len(customer_number) == 0:
            raise HTTPException(
                status_code=400,
                detail="Customer number cannot be empty"
            )
        
        customer_number = customer_number.strip().upper()
        
        # Get customer details
        result = CustomerService.get_customer_details(customer_number)
        
        if result["status"] == "error":
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=500, detail=result["message"])
        
        logging.debug(f"Customer details retrieved for: {customer_number}")
        
        return CustomerDetailResponse(
            status=result["status"],
            message=result["message"],
            customer=result["customer"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Customer detail error for {customer_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving customer details"
        )


@router.get("/{customer_number}/validate", response_model=CustomerValidationResponse)
async def validate_customer(
    customer_number: str,
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Validate if customer exists and is active
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.debug(f"Customer validation request from {user_id} for: {customer_number}")
        
        # Validate customer number format
        if not customer_number or len(customer_number) == 0:
            raise HTTPException(
                status_code=400,
                detail="Customer number cannot be empty"
            )
        
        customer_number = customer_number.strip().upper()
        
        # Check if customer exists
        exists = CustomerService.validate_customer_exists(customer_number)
        
        logging.debug(f"Customer validation result for {customer_number}: {exists}")
        
        return CustomerValidationResponse(
            exists=exists,
            customer_number=customer_number
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Customer validation error for {customer_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during customer validation"
        )


@router.get("/{customer_number}/sales-views", response_model=dict)
async def get_customer_sales_views(
    customer_number: str,
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get customer sales organization views from KNA1VV table
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer sales views request from {user_id} for: {customer_number}")
        
        customer_number = customer_number.strip().upper()
        
        # Get sales views
        result = CustomerService.get_customer_sales_views(customer_number)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        logging.debug(f"Sales views retrieved for: {customer_number}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Sales views error for {customer_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving sales views"
        )


@router.get("/{customer_number}/partner-functions", response_model=dict)
async def get_customer_partner_functions(
    customer_number: str,
    vkorg: Optional[str] = Query(None, description="Sales organization filter"),
    vtweg: Optional[str] = Query(None, description="Distribution channel filter"),
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get customer partner functions from KNVP table
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer partner functions request from {user_id} for: {customer_number}")
        
        customer_number = customer_number.strip().upper()
        
        # Get partner functions
        result = CustomerService.get_customer_partner_functions(
            customer_number=customer_number,
            vkorg=vkorg,
            vtweg=vtweg
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        logging.debug(f"Partner functions retrieved for: {customer_number}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Partner functions error for {customer_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving partner functions"
        )


@router.get("/{customer_number}/complete", response_model=dict)
async def get_customer_complete_info(
    customer_number: str,
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get complete customer information from all related tables (KNA1, KNVV, KNA1VV, KNVP)
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Complete customer info request from {user_id} for: {customer_number}")
        
        customer_number = customer_number.strip().upper()
        
        # Get complete customer information
        result = CustomerService.get_customer_complete_info(customer_number)
        
        if result["status"] == "error":
            if "not found" in result["message"].lower():
                raise HTTPException(status_code=404, detail=result["message"])
            else:
                raise HTTPException(status_code=500, detail=result["message"])
        
        logging.debug(f"Complete customer info retrieved for: {customer_number}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Complete customer info error for {customer_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving complete customer information"
        )


@router.get("/spec", response_model=CustomerSpecResponse)
async def get_customer_specification(
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get customer specification for FE form
    Returns field specifications for customer creation form
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer specification request from {user_id}")
        
        # Get customer specification
        result = CustomerService.get_customer_specification()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        logging.debug("Customer specification retrieved successfully")
        
        return CustomerSpecResponse(
            status=result["status"],
            message=result["message"],
            specifications=result["specifications"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Customer specification error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving customer specification"
        )


@router.post("/create", response_model=CustomerCreateResponse)
async def create_customer(
    create_request: CustomerCreateRequest,
    current_user: TokenData = Depends(verify_any_token),
    _rate_limit = Depends(CustomerRateLimit)
):
    """
    Create new customer with provided data
    Only accepts user-inputtable fields (M and O types)
    Fixed fields (F type) are automatically populated
    """
    try:
        user_id = current_user.employee_id or current_user.client_id
        logging.info(f"Customer creation request from {user_id}")
        
        # Convert Pydantic models to dict
        general_data = create_request.general_data.dict()
        sale_data = create_request.sale_data.dict()
        
        # Log the creation request (excluding sensitive data)
        logging.info(f"Creating customer with general_data keys: {list(general_data.keys())}")
        logging.info(f"Creating customer with sale_data keys: {list(sale_data.keys())}")
        
        # Create customer
        result = CustomerService.create_customer(
            general_data=general_data,
            sale_data=sale_data
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        logging.info(f"Customer created successfully: {result.get('customer_number')}")
        
        return CustomerCreateResponse(
            status=result["status"],
            message=result["message"],
            customer_number=result.get("customer_number"),
            sap_response=result.get("sap_response")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Customer creation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during customer creation"
        )


@router.get("/", response_model=dict)
async def customer_api_info():
    """
    Customer API information endpoint
    """
    return {
        "api": "Customer Management API V1",
        "version": "1.0.0",
        "endpoints": {
            "search_get": "GET /api/v1/customers/search",
            "search_post": "POST /api/v1/customers/search",
            "details": "GET /api/v1/customers/{customer_number}",
            "validate": "GET /api/v1/customers/{customer_number}/validate",
            "sales_views": "GET /api/v1/customers/{customer_number}/sales-views",
            "partner_functions": "GET /api/v1/customers/{customer_number}/partner-functions",
            "complete_info": "GET /api/v1/customers/{customer_number}/complete",
            "specification": "GET /api/v1/customers/spec",
            "create": "POST /api/v1/customers/create",
            "lookup": "GET /api/v1/customers/lookup"
        },
        "tables_used": [
            "KNA1 - Customer Master (General Data)",
            "KNVV - Customer Master (Sales and Distribution)",
            "KNA1VV - Customer Master (Sales Organization Views)",
            "KNVP - Customer Master (Partner Functions)"
        ],
        "description": "Customer data management and search functionality with comprehensive SAP customer data integration",
        "main_workflows": {
            "customer_lookup": {
                "endpoint": "GET /api/v1/customers/lookup",
                "purpose": "Quick customer search by name, phone, or tax ID",
                "use_case": "For selecting existing customers during data entry",
                "parameters": ["name", "phone", "tax_id"],
                "example": "GET /api/v1/customers/lookup?name=ธนวินท์&limit=10"
            },
            "customer_creation": {
                "endpoints": [
                    "GET /api/v1/customers/spec - Get form specification",
                    "POST /api/v1/customers/create - Create new customer"
                ],
                "purpose": "Create new customer with guided form",
                "use_case": "For adding new customers to the system",
                "steps": [
                    "1. GET /spec to get form fields",
                    "2. Present form to user (exclude F-type fields)",
                    "3. POST /create with user input"
                ]
            }
        }
    }

