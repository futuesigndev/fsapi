from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.services.sap_service import call_rfc_read_table

router = APIRouter()

# กำหนด Pydantic Model สำหรับข้อมูลใน Body
class ReadTableRequest(BaseModel):
    table: str
    fields: list
    condition_key: str

@router.post("/sap/read_table")
async def read_table_api(request: ReadTableRequest):
    # สร้าง WHERE condition ให้มีรูปแบบ VBELN = '1000000'
    where_condition = f"VBELN = '{request.condition_key}'"

    # เรียกฟังก์ชัน call_rfc_read_table ด้วยข้อมูลที่ได้รับ
    response = call_rfc_read_table(request.table, request.fields, where_condition)
    
    # ตรวจสอบและจัดการข้อผิดพลาด
    if response["status"] == "error":
        raise HTTPException(status_code=500, detail=response["message"])

    return response
