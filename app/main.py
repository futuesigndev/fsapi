import logging
from fastapi import FastAPI, HTTPException, Form
from app.dependencies import create_access_token, verify_credentials
from app.api.routes import router  # นำเข้า router จาก routes.py
import logging

app = FastAPI()

logging.basicConfig(
    level=logging.DEBUG,  # แสดง Log ตั้งแต่ระดับ DEBUG ขึ้นไป
    format="%(asctime)s - %(levelname)s - %(message)s",  # รูปแบบ Log
    handlers=[
        logging.StreamHandler()  # ส่ง Log ไปยัง Console
    ]
)

@app.post("/token")
async def token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    # ตรวจสอบ CLIENT_ID และ CLIENT_SECRET
    is_verified = verify_credentials(client_id, client_secret)

    if not is_verified:
        raise HTTPException(status_code=401, detail="Invalid CLIENT_ID or CLIENT_SECRET")

    # สร้าง Token ที่ไม่มี authorized_functions
    access_token = create_access_token(data={"sub": client_id})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# รวมเส้นทาง API จาก router ใน app/api/routes.py
app.include_router(router, prefix="/api")

# รัน Uvicorn เมื่อไฟล์นี้ถูกเรียกใช้งานโดยตรง
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)