"""
SAP Integration API V1 - Enhanced SAP function calling with improved security
Handles SAP BAPI function calls with authorization and metadata validation
"""
import logging
import os
import json
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import ValidationError

from app.schemas.sap import (
    SAPFunctionRequest, 
    SAPFunctionResponse, 
    SAPErrorResponse,
    ClientFunctionListResponse
)
from app.services.sap_service import call_bapi
from app.services.auth_service import AuthService
from app.dependencies_v1 import verify_client_token, verify_any_token
from app.schemas.token import TokenData
from app.services.rate_limit_service import SAPRateLimit

router = APIRouter()


def load_function_metadata(function_name: str) -> Dict[str, Any]:
    """
    Load SAP function metadata from JSON file
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        metadata_file = os.path.join(base_dir, "sftp-root", "metadata", f"{function_name}.json")

        if not os.path.exists(metadata_file):
            raise HTTPException(
                status_code=404, 
                detail=f"Metadata for function '{function_name}' not found"
            )

        with open(metadata_file, "r", encoding="utf-8-sig") as file:
            content = file.read() 
            
            #print(content) 

            # แปลงจากสตริงด้วย json.loads()
            data = json.loads(content) 
            return data
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to load metadata for function '{function_name}'"
        )


def validate_input_parameters(parameters: Dict[str, Any], metadata: Dict[str, Any]):
    """
    Validate input parameters against metadata
    """
    required_inputs = extract_required_fields(metadata.get("input_parameters", {}))
    missing_inputs = [
        field for field in required_inputs 
        if not extract_nested_value(parameters.get("input", {}), field)
    ]

    if missing_inputs:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required input parameters: {', '.join(missing_inputs)}"
        )


def validate_table_parameters(parameters: Dict[str, Any], metadata: Dict[str, Any]):
    """
    Validate table parameters against metadata
    """
    table_parameters_meta = metadata.get("table_parameters", {})
    request_tables = parameters.get("tables", {})

    if table_parameters_meta:
        for table_name, table_meta in table_parameters_meta.items():
            if table_name not in request_tables:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required table parameter: {table_name}"
                )

            fields = request_tables[table_name].get("fields", {})

            if not fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Table '{table_name}' has no fields"
                )

            required_fields = [
                field_name for field_name, field_meta in table_meta["fields"].items()
                if field_meta.get("required", False)
            ]

            # Support both dict (single row) and list (multiple rows)
            if isinstance(fields, dict):
                missing_fields = [field for field in required_fields if field not in fields]
            elif isinstance(fields, list):
                missing_fields = []
                for row in fields:
                    missing_fields.extend([field for field in required_fields if field not in row])

            if missing_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required fields in table '{table_name}': {', '.join(missing_fields)}"
                )


def prepare_sap_data(parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform request data to SAP expected format
    """
    if not isinstance(parameters, dict):
        raise ValueError(f"Parameters must be a dictionary, but got {type(parameters).__name__}")

    # Process input parameters
    input_parameters = {}
    for key, val in parameters.get("input", {}).items():
        if key in metadata.get("input_parameters", {}):
            # Special handling for date fields
            if key == "I_DATE" and val:
                # Convert YYYY.MM.DD to YYYYMMDD
                date_parts = val.split('.')
                if len(date_parts) == 3:
                    input_parameters[key] = f"{date_parts[2]}{date_parts[1]}{date_parts[0]}"
                else:
                    input_parameters[key] = val
            else:
                input_parameters[key] = val

    # Process table parameters
    table_parameters = {}
    for table_name in metadata.get("table_parameters", {}):
        if table_name in parameters.get("tables", {}):
            fields = parameters["tables"][table_name].get("fields", {})
            # Convert single dict to list if needed
            if isinstance(fields, dict):
                table_parameters[table_name] = [fields]
            else:
                table_parameters[table_name] = fields

    return {**input_parameters, **table_parameters}


def filter_sap_response(raw_response: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter SAP response based on metadata structure
    """
    output_parameters = metadata.get("output_parameters", {})

    filtered_response = {}
    for key, value in output_parameters.items():
        if key in raw_response:
            if isinstance(value, dict) and isinstance(raw_response[key], list):
                # Filter table data
                filtered_response[key] = [
                    {sub_key: entry.get(sub_key, "") for sub_key in value.keys()}
                    for entry in raw_response[key]
                ]
            else:
                # Simple parameter
                filtered_response[key] = raw_response.get(key, "")

    return filtered_response


def extract_nested_value(data, keys):
    """
    Extract nested value from JSON using dot notation
    """
    for key in keys.split('.'):
        if key in data:
            data = data[key]
        else:
            return None
    return data


def extract_required_fields(parameters, parent_key=""):
    """
    Extract required fields from metadata parameters
    """
    required_fields = []
    for key, value in parameters.items():
        current_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict) and value.get("required", False):
            required_fields.append(current_key)
        elif isinstance(value, dict):
            required_fields.extend(extract_required_fields(value, current_key))
    return required_fields


# V1 ENDPOINT WITH AUTHENTICATION
@router.post("/call-function", response_model=SAPFunctionResponse)
async def call_sap_function(
    sap_request: SAPFunctionRequest,
    current_user: TokenData = Depends(verify_client_token)
):
    """
    Call SAP BAPI function with authentication and full functionality
    """
    try:
        logging.info(f"V1 SAP call: {sap_request.function_name} by client: {current_user.client_id}")
        
        # Ensure parameters is not None
        if sap_request.parameters is None:
            sap_request.parameters = {}
        
        # Check function authorization
        if not AuthService.is_function_authorized(current_user.client_id, sap_request.function_name):
            raise HTTPException(
                status_code=403,
                detail=f"Client {current_user.client_id} is not authorized to use function {sap_request.function_name}"
            )

        # Load and validate metadata
        metadata = load_function_metadata(sap_request.function_name)
        validate_input_parameters(sap_request.parameters, metadata)
        validate_table_parameters(sap_request.parameters, metadata)

        # Prepare SAP data
        sap_data = prepare_sap_data(sap_request.parameters, metadata)
        
        # Call SAP BAPI
        sap_response = call_bapi(sap_request.function_name, sap_data)

        if sap_response.get("status") == "error":
            raise HTTPException(status_code=500, detail=sap_response.get("message"))

        # Filter response based on metadata
        filtered_response = filter_sap_response(sap_response.get("data", {}), metadata)

        # Check for SAP errors in RETURN messages
        return_messages = filtered_response.get("RETURN", [])
        error_found = any(entry.get("TYPE") != "S" for entry in return_messages if isinstance(entry, dict))
        
        status = "error" if error_found else "success"
        message = "Execution completed with errors." if error_found else "Execution completed successfully."

        return SAPFunctionResponse(
            status=status,
            message=message,
            sap_response=filtered_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during SAP function call: {str(e)}"
        )


# SIMPLIFIED TESTING ENDPOINT (NO AUTH)
@router.post("/call-function-test")
async def call_sap_function_test(sap_request: SAPFunctionRequest):
    """
    Call SAP BAPI function - SIMPLIFIED VERSION FOR TESTING (NO AUTH)
    """
    try:
        #logging.info(f"V1 SAP test call received: function={sap_request.function_name}")
        #logging.debug(f"Request parameters: {sap_request.parameters}")
        
        return {
            "status": "success",
            "message": "V1 test endpoint working without auth",
            "function_name": sap_request.function_name,
            "parameters": sap_request.parameters
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/test-function")
async def test_sap_function(request: SAPFunctionRequest):
    """
    Test endpoint without authentication for debugging
    """
    try:
        #logging.info(f"Test SAP call received: {request.function_name}")
        #logging.debug(f"Request data: {request.dict()}")
        
        return {
            "status": "success",
            "message": "Test endpoint working",
            "received_data": request.dict()
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e)
        }


@router.get("/functions", response_model=ClientFunctionListResponse)
async def get_authorized_functions(
    current_user: TokenData = Depends(verify_client_token)
):
    """
    Get list of SAP functions that current client is authorized to use
    """
    try:
        # Get authorized functions for client
        functions = AuthService.get_authorized_functions(current_user.client_id)

        #logging.debug(f"Authorized functions retrieved for client: {current_user.client_id}")

        return ClientFunctionListResponse(
            status="success",
            message=f"Found {len(functions)} authorized functions",
            client_id=current_user.client_id,
            authorized_functions=functions
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving authorized functions"
        )


@router.get("/functions/{function_name}/metadata")
async def get_function_metadata(
    function_name: str,
    current_user: TokenData = Depends(verify_any_token)
):
    """
    Get metadata for specific SAP function
    """
    try:
        # For client authentication, check authorization
        if current_user.client_id:
            if not AuthService.is_function_authorized(current_user.client_id, function_name):
                raise HTTPException(
                    status_code=403,
                    detail=f"Client {current_user.client_id} is not authorized to view function {function_name} metadata"
                )
        
        # Load metadata
        metadata = load_function_metadata(function_name)
        
        user_id = current_user.employee_id or current_user.client_id
        #logging.debug(f"Function metadata retrieved: {function_name} by {user_id}")
        
        return {
            "status": "success",
            "function_name": function_name,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error retrieving function metadata"
        )


@router.get("/", response_model=dict)
async def sap_api_info():
    """
    SAP API information endpoint
    """
    return {
        "api": "SAP Integration API V1",
        "version": "1.0.0",
        "endpoints": {
            "call_function": "POST /api/v1/sap/call-function",
            "get_functions": "GET /api/v1/sap/functions",
            "get_metadata": "GET /api/v1/sap/functions/{function_name}/metadata"
        },
        "description": "Enhanced SAP BAPI integration with authorization and metadata validation",
        "improvements": [
            "Function-level authorization",
            "Enhanced error handling",
            "Metadata validation",
            "Client access control",
            "Comprehensive logging"
        ]
    }
