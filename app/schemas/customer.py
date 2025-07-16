"""
Customer Schemas - Customer data related schemas
"""
from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum


class ErrorCode(str, Enum):
    """
    Standardized error codes for customer API
    """
    # Validation Errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Resource Errors
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    CUSTOMER_ALREADY_EXISTS = "CUSTOMER_ALREADY_EXISTS"
    
    # Service Errors
    DATABASE_ERROR = "DATABASE_ERROR"
    SAP_CONNECTION_ERROR = "SAP_CONNECTION_ERROR"
    SAP_PROCESSING_ERROR = "SAP_PROCESSING_ERROR"
    
    # Authentication/Authorization
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Internal Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class StandardError(BaseModel):
    """
    Standardized error response schema
    """
    error: bool = True
    code: ErrorCode
    message: str
    details: Optional[str] = None
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class StandardResponse(BaseModel):
    """
    Standardized success response schema
    """
    success: bool = True
    message: str
    timestamp: Optional[str] = None
    request_id: Optional[str] = None


class CustomerBase(BaseModel):
    """
    Base customer schema with essential fields
    """
    KUNNR: str  # Customer Number
    NAME1: str  # Customer Name 1
    NAME2: Optional[str] = ""  # Customer Name 2
    ORT01: Optional[str] = ""  # City
    ORT02: Optional[str] = ""  # District
    STRAS: Optional[str] = ""  # Street Address
    TELF1: Optional[str] = ""  # Telephone


class CustomerSummary(CustomerBase):
    """
    Customer summary for search results
    """
    STCD3: Optional[str] = ""  # Tax Number
    VKORG: Optional[str] = ""  # Sales Organization (from KNVV)
    VTWEG: Optional[str] = ""  # Distribution Channel
    BZIRK: Optional[str] = ""  # Sales District
    VKGRP: Optional[str] = ""  # Sales Group
    VKBUR: Optional[str] = ""  # Sales Office
    SPART: Optional[str] = ""  # Division (from KNVP or KNVV)
    KDGRP: Optional[str] = ""  # Customer Group (from KNVV)
    VSBED: Optional[str] = ""  # Shipping Conditions (from KNVV)
    ZTERM: Optional[str] = ""  # Payment Terms (from KNVV)


class CustomerDetail(CustomerSummary):
    """
    Complete customer details schema
    """
    NAME3: Optional[str] = ""  # Customer Name 3
    NAME4: Optional[str] = ""  # Customer Name 4
    PSTLZ: Optional[str] = ""  # Postal Code
    LAND1: Optional[str] = ""  # Country
    REGIO: Optional[str] = ""  # Region
    TELF2: Optional[str] = ""  # Telephone 2
    TELFX: Optional[str] = ""  # Fax
    SMTP_ADDR: Optional[str] = ""  # Email
    KTOKD: Optional[str] = ""  # Account Group
    BRSCH: Optional[str] = ""  # Industry
    ERDAT: Optional[str] = ""  # Created Date
    ERNAM: Optional[str] = ""  # Created By
    PLTYP: Optional[str] = ""  # Price List Type


class CustomerSearchRequest(BaseModel):
    """
    Customer search request schema
    """
    customer_number: Optional[str] = None
    customer_name: Optional[str] = None
    city: Optional[str] = None
    limit: Optional[int] = 50


class CustomerSearchResponse(BaseModel):
    """
    Customer search response schema
    """
    status: str
    message: str
    total_records: int
    customers: List[CustomerSummary]


class CustomerDetailResponse(BaseModel):
    """
    Customer detail response schema
    """
    status: str
    message: str
    customer: Optional[CustomerDetail] = None


class CustomerValidationResponse(BaseModel):
    """
    Customer validation response schema
    """
    exists: bool
    customer_number: str


class CustomerGeneralData(BaseModel):
    """
    Customer General Data - GENERAL_DATA group
    Only fields with inputType: 'M' (Mandatory) and 'O' (Optional)
    """
    NAME1: str  # Name-Surname (M)
    CITY: Optional[str] = ""  # City (O)
    DISTRICT: Optional[str] = ""  # District (O)
    TAX3: str  # Tax Number (M)
    TYPE_BUS: Optional[str] = ""  # Type of Business (O)
    POST_CODE: Optional[str] = ""  # Postal Code (O)
    STREET_NO: Optional[str] = ""  # Street Number (O)
    LOCATION: Optional[str] = ""  # Street 5 (O)
    TEL1_NUMBR: Optional[str] = ""  # First telephone no. (O)
    CONTACT: Optional[str] = ""  # Name 1 (O)
    CRM_REF: Optional[str] = ""  # Address notes (O)


class CustomerSaleData(BaseModel):
    """
    Customer Sale Data - SALE_DATA group
    Only fields with inputType: 'M' (Mandatory) and 'O' (Optional)
    """
    DIST_CHN: str  # Distribution Channel (M)
    CUST_GROUP: str  # Customer group (M)
    SALE_DIST: str  # Sales district (M)
    DEL_PIOR: Optional[str] = ""  # Delivery Priority (O)
    CUST_STS_GROUP: str  # Customer Statistics Group (M)


class CustomerCreateRequest(BaseModel):
    """
    Customer creation request schema
    Contains only user-inputtable fields (M and O types, excluding F types)
    """
    general_data: CustomerGeneralData
    sale_data: CustomerSaleData


class CustomerCreateResponse(BaseModel):
    """
    Customer creation response schema
    """
    status: str
    message: str
    customer_number: Optional[str] = None  # Generated KUNNR
    sap_response: Optional[dict] = None


class CustomerSpecField(BaseModel):
    """
    Customer specification field schema for FE
    """
    group: str
    fieldName: str
    label: str
    type: str
    length: int
    inputType: str  # 'M'=Mandatory, 'O'=Optional, 'F'=Fixed
    defaultValue: str
    layout: Optional[dict] = None
    options: Optional[List[dict]] = None


class CustomerSpecResponse(BaseModel):
    """
    Customer specification response for FE
    """
    status: str
    message: str
    specifications: List[CustomerSpecField]
