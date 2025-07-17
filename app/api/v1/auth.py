"""
Authentication API V1 - User authentication endpoints
Handles employee login and user profile management
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from app.schemas.user import UserLoginRequest, UserLoginResponse, UserProfile
from app.schemas.token import Token, TokenData
from app.services.user_service import UserService
from app.services.rate_limit_service import AuthRateLimit
from app.dependencies_v1 import verify_user_token, create_user_access_token

load_dotenv()

router = APIRouter()

# OAuth2 configuration for V1
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

@router.post("/login", response_model=UserLoginResponse)
async def user_login(
    login_request: UserLoginRequest,
    _rate_limit = Depends(AuthRateLimit)
):
    """
    Employee login endpoint
    Authenticates employee and returns JWT token
    """
    try:
        # Authenticate employee
        employee_data = UserService.authenticate_employee(
            login_request.employee_id, 
            login_request.password
        )
        
        if not employee_data:
            raise HTTPException(
                status_code=401,
                detail="Invalid employee credentials"
            )
        
        # Create JWT token with user type
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_user_access_token(
            data={
                "sub": str(employee_data["employee_id"]),
                "type": "user",
                "name": employee_data["employee_name"],
                "card": employee_data["employee_card"]
            },
            expires_delta=access_token_expires
        )
        
        # Prepare response
        user_auth_data = {
            "employee_id": str(employee_data["employee_id"]),
            "employee_name": employee_data["employee_name"],
            "employee_card": employee_data["employee_card"],
            "access_token": access_token,
            "token_type": "bearer"
        }
        
        return UserLoginResponse(
            status="success",
            message="Login successful",
            user_data=user_auth_data
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during login"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user(current_user: TokenData = Depends(verify_user_token)):
    """
    Get current user profile information
    """
    try:
        # Get user profile from database
        profile = UserService.get_employee_profile(current_user.employee_id)
                
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        return UserProfile(**profile)
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error retrieving profile"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(verify_user_token)):
    """
    Refresh user access token
    """
    try:
        # Get fresh user data
        profile = UserService.get_employee_profile(current_user.employee_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Create new token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_user_access_token(
            data={
                "sub": profile["employee_id"],
                "type": "user",
                "name": profile["employee_name"],
                "card": profile["employee_card"]
            },
            expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error refreshing token"
        )
