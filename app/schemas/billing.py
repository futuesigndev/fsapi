# /app/schemas/billing.py

from pydantic import BaseModel, Field

# Model สำหรับ Request แบบใหม่ - รับแค่เลข DO
class CreateBillingRequest(BaseModel):
    delivery_number: str = Field(..., description="เลขที่ Delivery Order (DO)")
    test_run: bool = Field(False, description="ถ้าเป็น True จะเป็นการทดสอบ ไม่สร้างจริง")