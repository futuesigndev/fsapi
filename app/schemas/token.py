"""
Token Schemas - JWT Token and Authentication related schemas
"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """
    JWT Token response schema
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Token payload data schema
    """
    client_id: Optional[str] = None
    employee_id: Optional[str] = None


class ClientCredentials(BaseModel):
    """
    Client credentials request schema
    """
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


class UserLogin(BaseModel):
    """
    User login request schema
    """
    employee_id: str
    password: str
