# /app/api/v1/billing.py

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.billing import CreateBillingRequest
from app.services.billing_service import create_billing_document_in_sap, check_delivery_status, get_valid_billing_types, auto_detect_billing_type
from app.dependencies_v1 import verify_any_token

try:
    from pyrfc import ABAPApplicationError, CommunicationError
except ImportError:
    ABAPApplicationError, CommunicationError = Exception, Exception

router = APIRouter(
    tags=["Billing - v1"],
)

@router.post("/create")
@router.post("/create/")
async def create_billing_document_endpoint(
    request: CreateBillingRequest,
    current_token = Depends(verify_any_token)
):
    """
    สร้าง Billing Document จาก Delivery Order
    รับแค่เลข Delivery Number เท่านั้น
    **Requires Authentication.**
    """
    
    try:
        result = create_billing_document_in_sap(
            delivery_number=request.delivery_number,
            test_run=request.test_run
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": result["message"],
                "delivery_number": request.delivery_number,
                "test_run": request.test_run,
                "data": result["data"]
            }
        else:
            # Return error with proper status code
            status_code = 400  # Bad Request for validation errors
            if "not found" in result.get("message", "").lower():
                status_code = 404  # Not Found
            elif "already been processed" in result.get("message", "").lower():
                status_code = 409  # Conflict
                
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": result["message"],
                    "delivery_number": request.delivery_number,
                    "test_run": request.test_run,
                    "data": result.get("data", {})
                }
            )
            
    except HTTPException:
        raise
    except ABAPApplicationError as abap_error:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SAP ABAP Error occurred",
                "details": str(abap_error),
                "delivery_number": request.delivery_number
            }
        )
    except CommunicationError as comm_error:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Cannot connect to SAP system",
                "details": str(comm_error),
                "delivery_number": request.delivery_number
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "details": str(e),
                "delivery_number": request.delivery_number
            }
        )


@router.get("/delivery/{delivery_doc}/status")
async def check_delivery_status_endpoint(
    delivery_doc: str,
    current_token = Depends(verify_any_token)
):
    """
    ตรวจสอบสถานะ Delivery Document ว่าสามารถสร้าง billing ได้หรือไม่
    """
    
    try:
        result = check_delivery_status(delivery_doc)
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": result["message"],
                    "delivery_doc": delivery_doc
                }
            )
        
        return {
            "status": "success",
            "message": "Delivery status checked successfully",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking delivery status: {str(e)}")


@router.get("/types")
async def get_billing_types_endpoint(
    current_token = Depends(verify_any_token)
):
    """
    ดึงรายการ billing types ที่ valid จาก SAP system
    """
    
    try:
        result = get_valid_billing_types()
        
        return {
            "status": "success",
            "message": f"Found billing types",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting billing types: {str(e)}")


@router.get("/delivery/{delivery_doc}/suggest-type")
async def suggest_billing_type_endpoint(
    delivery_doc: str,
    current_token = Depends(verify_any_token)
):
    """
    แนะนำ billing type ที่เหมาะสมสำหรับ delivery document
    """
    
    try:
        suggested_type = auto_detect_billing_type(delivery_doc)
        
        return {
            "status": "success",
            "message": f"Suggested billing type for delivery {delivery_doc}",
            "data": {
                "delivery_doc": delivery_doc,
                "suggested_type": suggested_type,
                "alternatives": ["F2", "F8", "S1"],
                "note": "F2=Invoice, F8=Credit Memo, S1=Pro Forma"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error suggesting billing type: {str(e)}")
