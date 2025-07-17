"""
Dependencies V1 - Enhanced authentication and authorization for V1 APIs
Provides both client and user authentication dependencies
"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv
from typing import Union
from datetime import datetime, timedelta

from app.schemas.token import TokenData
from app.services.auth_service import AuthService
from app.services.user_service import UserService

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment variables")

# OAuth2 schemes for different authentication types
oauth2_scheme_client = OAuth2PasswordBearer(tokenUrl="/token")  # Legacy client auth
oauth2_scheme_user = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")  # V1 user auth


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def verify_client_token(token: str = Depends(oauth2_scheme_client)) -> TokenData:
    """
    Verify client JWT token (Legacy authentication)
    Returns client_id for legacy API compatibility
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        token_type: str = payload.get("type", "client")

        if client_id is None or token_type == "user":
            raise AuthenticationError({
                "error": "INVALID_CLIENT_TOKEN",
                "message": "Invalid client token structure",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "authentication_error"
            })

        return TokenData(client_id=client_id)
        
    except JWTError as e:
        error_detail = str(e).lower()
        
        if "expired" in error_detail:
            error_code = "CLIENT_TOKEN_EXPIRED"
            message = "Client access token has expired"
        elif "invalid" in error_detail:
            error_code = "CLIENT_TOKEN_INVALID"
            message = "Invalid client access token"
        else:
            error_code = "CLIENT_TOKEN_ERROR"
            message = "Client token authentication failed"
            
        raise AuthenticationError({
            "error": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "authentication_error",
            "action": "refresh_client_token"
        })


def verify_user_token(token: str = Depends(oauth2_scheme_user)) -> TokenData:
    """
    Verify user JWT token (V1 authentication)
    Returns employee_id for V1 API user authentication
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id: str = payload.get("sub")
        token_type: str = payload.get("type", "client")
        
        if employee_id is None or token_type != "user":
            raise AuthenticationError({
                "error": "INVALID_USER_TOKEN",
                "message": "Invalid user token structure",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "authentication_error"
            })
        
        # Verify user still exists and is active
        if not UserService.validate_employee_exists(employee_id):
            raise AuthenticationError({
                "error": "USER_NOT_FOUND",
                "message": "User account not found or inactive",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "authentication_error",
                "action": "contact_administrator"
            })
            
        return TokenData(employee_id=employee_id)
        
    except JWTError as e:
        error_detail = str(e).lower()
        
        if "expired" in error_detail:
            error_code = "USER_TOKEN_EXPIRED"
            message = "User access token has expired"
            action = "relogin_required"
        elif "invalid" in error_detail:
            error_code = "USER_TOKEN_INVALID"
            message = "Invalid user access token"
            action = "relogin_required"
        else:
            error_code = "USER_TOKEN_ERROR"
            message = "User token authentication failed"
            action = "relogin_required"
            
        raise AuthenticationError({
            "error": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "authentication_error",
            "action": action
        })


def verify_any_token(token: str = Depends(oauth2_scheme_client)) -> TokenData:
    """
    Verify either client or user token
    Useful for endpoints that accept both authentication types
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        token_type: str = payload.get("type", "client")
        
        if subject is None:
            raise AuthenticationError({
                "error": "INVALID_TOKEN_STRUCTURE",
                "message": "Invalid token structure",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "authentication_error"
            })
        
        if token_type == "user":
            # User token validation
            if not UserService.validate_employee_exists(subject):
                raise AuthenticationError({
                    "error": "USER_NOT_FOUND",
                    "message": "User account not found or inactive",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "authentication_error",
                    "action": "contact_administrator"
                })
            return TokenData(employee_id=subject)
        else:
            # Client token validation
            return TokenData(client_id=subject)
            
    except JWTError as e:
        error_detail = str(e).lower()
        
        if "expired" in error_detail:
            error_code = "TOKEN_EXPIRED"
            message = "Access token has expired"
            action = "refresh_token_or_relogin"
        elif "invalid" in error_detail:
            error_code = "TOKEN_INVALID"
            message = "Invalid access token"
            action = "refresh_token_or_relogin"
        else:
            error_code = "TOKEN_ERROR"
            message = "Token authentication failed"
            action = "refresh_token_or_relogin"
            
        raise AuthenticationError({
            "error": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "authentication_error",
            "action": action
        })


def create_user_access_token(data: dict, expires_delta: timedelta = None):
    """
    Create access token for user authentication
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def require_function_authorization(function_name: str):
    """
    Dependency factory for SAP function authorization
    Returns a dependency that checks if client is authorized for specific function
    """
    def check_authorization(current_token: TokenData = Depends(verify_client_token)):
        if not current_token.client_id:
            raise AuthenticationError("Client authentication required")
            
        # Check if client is authorized for this function
        if not AuthService.is_function_authorized(current_token.client_id, function_name):
            raise AuthorizationError(
                f"Client {current_token.client_id} is not authorized to use function {function_name}"
            )
            
        return current_token
    
    return check_authorization


def require_role(required_role: str):
    """
    Dependency factory for role-based authorization
    Returns a dependency that checks if user has required role
    """
    def check_role(current_user: TokenData = Depends(verify_user_token)):
        if not current_user.employee_id:
            raise AuthenticationError("User authentication required")
            
        # Get user profile to check role
        profile = UserService.get_employee_profile(current_user.employee_id)
        if not profile:
            raise AuthenticationError("User profile not found")
            
        if profile["role"] != required_role:
            raise AuthorizationError(
                f"Required role '{required_role}' not found. User role: '{profile['role']}'"
            )
            
        return current_user
    
    return check_role


def require_department(required_department: str):
    """
    Dependency factory for department-based authorization
    Returns a dependency that checks if user belongs to required department
    """
    def check_department(current_user: TokenData = Depends(verify_user_token)):
        if not current_user.employee_id:
            raise AuthenticationError("User authentication required")
            
        # Get user profile to check department
        profile = UserService.get_employee_profile(current_user.employee_id)
        if not profile:
            raise AuthenticationError("User profile not found")
            
        if profile["department"] != required_department:
            raise AuthorizationError(
                f"Required department '{required_department}' access denied. User department: '{profile['department']}'"
            )
            
        return current_user
    
    return check_department


# Convenience dependencies for common use cases
def get_current_client() -> TokenData:
    """Convenience function for client authentication"""
    return Depends(verify_client_token)

def get_current_user() -> TokenData:
    """Convenience function for user authentication"""
    return Depends(verify_user_token)

def get_current_token() -> TokenData:
    """Convenience function for any token authentication"""
    return Depends(verify_any_token)
