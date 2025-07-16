"""
User Schemas - Employee and User related schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """
    Base user schema with common fields
    """
    employee_id: str
    employee_name: str
    department: str
    email: Optional[str] = None
    role: str


class UserProfile(UserBase):
    """
    Complete user profile schema
    """
    phone: Optional[str] = None
    position: Optional[str] = None
    manager_id: Optional[str] = None
    created_date: Optional[str] = None
    last_login: Optional[str] = None


class UserAuthentication(BaseModel):
    """
    User authentication response schema
    """
    employee_id: str
    employee_name: str
    department: str
    email: Optional[str] = None
    role: str
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
