"""
User Schemas - Employee and User related schemas
"""
from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    """
    Base user schema with common fields
    """
    employee_id: str
    employee_name: str
    department: str


class UserProfile(UserBase):
    employee_card: Optional[str] = None
    division_desc_th: Optional[str] = None
    department_name_th: Optional[str] = None
    section_name: Optional[str] = None
    nationality: Optional[str] = None


class UserAuthentication(BaseModel):
    """
    User authentication response schema
    """
    employee_id: str
    employee_name: str
    employee_card: str
    access_token: str
    token_type: str = "bearer"


class UserLoginRequest(BaseModel):
    """
    User login request schema
    """
    employee_id: str
    password: str


class UserLoginResponse(BaseModel):
    """
    User login response schema
    """
    status: str
    message: str
    user_data: Optional[UserAuthentication] = None
