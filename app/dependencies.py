import logging
import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv
from datetime import datetime
from app.services.oracle_service import get_user_credentials

# โหลดค่าใน .env
load_dotenv()

# กำหนดค่าที่ใช้ใน OAuth2
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# ตรวจสอบว่า SECRET_KEY ถูกตั้งค่า
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment variables")

# สร้าง OAuth2 Password Bearer Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    """
    สร้าง Access Token (JWT) สำหรับ Client ที่ผ่านการตรวจสอบ
    """
    from datetime import datetime, timedelta
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    logging.debug(f"Creating token with data: {to_encode}")  # Log Payload ก่อน encode
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        # ถอดรหัส Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id = payload.get("sub")

        if client_id is None:
            raise HTTPException(
                status_code=401, 
                detail={
                    "error": "INVALID_TOKEN_STRUCTURE",
                    "message": "Invalid token structure",
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "authentication_error"
                }
            )

        logging.debug(f"Token is valid for client_id: {client_id}")
        return {"client_id": client_id}  # ส่ง client_id กลับไป
    except JWTError as e:
        error_detail = str(e).lower()
        logging.error(f"JWT Error: {e}")
        
        # Determine specific error type
        if "expired" in error_detail:
            error_code = "TOKEN_EXPIRED"
            message = "Access token has expired"
        elif "invalid" in error_detail or "decode" in error_detail:
            error_code = "TOKEN_INVALID"
            message = "Invalid access token"
        else:
            error_code = "TOKEN_ERROR"
            message = "Token authentication failed"
            
        raise HTTPException(
            status_code=401, 
            detail={
                "error": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "authentication_error",
                "action": "refresh_token_or_relogin"
            }
        )


def verify_credentials(client_id: str, client_secret: str):
    credentials = get_user_credentials(client_id)

    if not credentials or credentials["client_secret"] != client_secret:
        return False

    logging.debug(f"Client {client_id} credentials verified.")
    return True


