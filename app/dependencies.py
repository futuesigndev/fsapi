import logging
import os
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv
from app.services.oracle_service import get_user_credentials

# โหลดค่าใน .env
load_dotenv()

# กำหนดค่าที่ใช้ใน OAuth2
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

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
            raise HTTPException(status_code=401, detail="Invalid token structure")

        logging.debug(f"Token is valid for client_id: {client_id}")
        return {"client_id": client_id}  # ส่ง client_id กลับไป
    except JWTError as e:
        logging.error(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Token has expired or is invalid")


def verify_credentials(client_id: str, client_secret: str):
    credentials = get_user_credentials(client_id)

    if not credentials or credentials["client_secret"] != client_secret:
        return False

    logging.debug(f"Client {client_id} credentials verified.")
    return True


