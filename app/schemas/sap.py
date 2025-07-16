"""
SAP Schemas - SAP integration related schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union


class SAPFunctionRequest(BaseModel):
    """
    SAP function call request schema
    Maximum compatibility with legacy format
    """
    function_name: str = Field(..., description="SAP function name to call")
    parameters: Optional[Any] = Field(default=None, description="Function parameters - accepts any format")
    
    @validator('parameters', pre=True, always=True)
    def validate_parameters(cls, v):
        """Convert any input to dict format with maximum flexibility"""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except:
                return {"raw_string": v}
        if isinstance(v, (list, tuple)):
            return {"array_data": v}
        # For any other type, wrap it
        return {"data": v}
    
    class Config:
        extra = "allow"  # Allow extra fields
        arbitrary_types_allowed = True  # Allow any types


class SAPFunctionResponse(BaseModel):
    """
    SAP function call response schema
    """
    status: str
    message: str
    sap_response: Dict[str, Any]


class SAPInputParameter(BaseModel):
    """
    SAP input parameter schema
    """
    type: str
    length: int
    required: bool
    value: Optional[str] = None


class SAPTableParameter(BaseModel):
    """
    SAP table parameter schema
    """
    fields: Dict[str, Any]


class SAPFunctionMetadata(BaseModel):
    """
    SAP function metadata schema
    """
    function_name: str
    description: str
    input_parameters: Dict[str, SAPInputParameter]
    output_parameters: Dict[str, Any]
    table_parameters: Optional[Dict[str, Dict[str, Any]]] = None


class SAPReturnMessage(BaseModel):
    """
    SAP return message schema
    """
    TYPE: str  # Message type (S=Success, E=Error, W=Warning, I=Info)
    ID: str    # Message ID
    NUMBER: str  # Message number
    MESSAGE: str  # Message text


class SAPErrorResponse(BaseModel):
    """
    SAP error response schema
    """
    status: str = "error"
    message: str
    error_details: Optional[List[SAPReturnMessage]] = None


class AuthorizedFunction(BaseModel):
    """
    Authorized SAP function schema
    """
    function_name: str
    function_detail: str


class ClientFunctionListResponse(BaseModel):
    """
    Client authorized functions list response
    """
    status: str
    message: str
    client_id: str
    authorized_functions: List[AuthorizedFunction]
