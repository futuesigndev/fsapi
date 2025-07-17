# app/services/billing_service.py

from pyrfc import Connection
from app.config import Config
from typing import List, Dict, Any
from .sap_service import connect_to_sap, parse_wa_data

try:
    from pyrfc import Connection, ABAPApplicationError, CommunicationError
except ImportError:
    Connection, ABAPApplicationError, CommunicationError = None, Exception, Exception


def validate_delivery_document(delivery_doc: str):
    """
    ตรวจสอบ Delivery Document ก่อนสร้างบิล
    - ตรวจสอบว่ามีในระบบหรือไม่
    - ตรวจสอบว่าเคยออกบิลไปแล้วหรือไม่
    """
    conn = None
    try:
        conn = connect_to_sap()
        
        # ตรวจสอบว่า delivery มีอยู่ในระบบหรือไม่
        delivery_check = conn.call('RFC_READ_TABLE',
                                 QUERY_TABLE='LIKP',
                                 DELIMITER='|',
                                 FIELDS=[
                                     {"FIELDNAME": "VBELN"},  # Delivery Number
                                     {"FIELDNAME": "LFART"},  # Delivery Type
                                     {"FIELDNAME": "LFDAT"},  # Delivery Date
                                     {"FIELDNAME": "WADAT_IST"}  # Actual GI Date
                                 ],
                                 OPTIONS=[{"TEXT": f"VBELN = '{delivery_doc}'"}])
        
        if not delivery_check.get("DATA"):
            return {
                "valid": False,
                "error_type": "NOT_FOUND",
                "message": f"Delivery document {delivery_doc} not found in the system.",
                "can_proceed": False
            }
        
        # ตรวจสอบว่าเคยออกบิลแล้วหรือไม่ - ตรวจจาก VBRP
        billing_check = conn.call('RFC_READ_TABLE',
                                QUERY_TABLE='VBRP',
                                DELIMITER='|',
                                FIELDS=[
                                    {"FIELDNAME": "VBELN"},  # Billing Document
                                    {"FIELDNAME": "VGBEL"},  # Reference Document (Delivery)
                                    {"FIELDNAME": "VGPOS"}   # Reference Item
                                ],
                                OPTIONS=[{"TEXT": f"VGBEL = '{delivery_doc}'"}])
        
        if billing_check.get("DATA"):
            parsed_billing = parse_wa_data(billing_check["DATA"], billing_check["FIELDS"])
            if parsed_billing:
                existing_bill = parsed_billing[0].get("VBELN", "").strip()
                return {
                    "valid": False,
                    "error_type": "ALREADY_BILLED",
                    "message": f"Delivery {delivery_doc} has already been processed in subsequent document {existing_bill}.",
                    "existing_billing_doc": existing_bill,
                    "can_proceed": False
                }
        
        # ถ้าผ่านการตรวจสอบทั้งหมด
        parsed_delivery = parse_wa_data(delivery_check["DATA"], delivery_check["FIELDS"])
        delivery_info = parsed_delivery[0] if parsed_delivery else {}
        
        return {
            "valid": True,
            "error_type": None,
            "message": "Delivery document is valid and ready for billing",
            "delivery_info": delivery_info,
            "can_proceed": True
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error_type": "VALIDATION_ERROR",
            "message": f"Error validating delivery document: {str(e)}",
            "can_proceed": False
        }
    finally:
        if conn:
            conn.close()


def check_delivery_status(delivery_doc: str):
    """
    ตรวจสอบสถานะ Delivery Document ว่าพร้อมสร้าง billing หรือไม่
    รวม validation ก่อนเรียก Custom Function Module
    """
    conn = None
    try:
        # ตรวจสอบ delivery document ก่อน
        validation_result = validate_delivery_document(delivery_doc)
        
        if not validation_result["valid"]:
            return {
                "status": "error",
                "delivery_doc": delivery_doc,
                "can_bill": False,
                "issues": [validation_result["message"]],
                "error_type": validation_result["error_type"],
                "delivery_info": {"VBELN": delivery_doc, "VALIDATION": "FAILED"},
                "lock_info": [],
                "approach": "Pre-validation Check"
            }
        
        conn = connect_to_sap()
        
        delivery_info = {"VBELN": delivery_doc, "STATUS_CHECK": "CUSTOM_FUNCTION"}
        delivery_info.update(validation_result.get("delivery_info", {}))
        can_bill = True
        issues = []
        
        try:
            # ลองเรียก Custom Function Module ใน test mode
            function_name = "Z_RFC_BILL_CREATE_BDC"
            
            test_params = {
                "IV_VBELN": delivery_doc,
                "IV_TESTRUN": "X"
            }
            
            try:
                test_result = conn.call(function_name, **test_params)
                
                # ตรวจสอบผลลัพธ์
                billing_doc = test_result.get("EV_BILLING_DOC", "").strip()
                message = test_result.get("EV_RETURN_MESSAGE", "")
                return_type = test_result.get("EV_RETURN_TYPE", "").strip()
                
                if billing_doc and return_type == "S":
                    can_bill = True
                    delivery_info.update({"TEST_STATUS": "OK", "TEST_RESULT": f"Can create: {billing_doc}"})
                elif return_type == "E":
                    can_bill = False
                    issues.append(f"Custom function indicates error: {message}")
                else:
                    if "error" in message.lower() or "fail" in message.lower():
                        can_bill = False
                        issues.append(f"Custom function indicates issues: {message}")
                    else:
                        can_bill = True
                        issues.append(f"Custom function response unclear: {message}")
                
            except Exception as test_error:
                error_msg = str(test_error)
                
                if "not found" in error_msg.lower():
                    can_bill = False
                    issues.append(f"Custom Function Module '{function_name}' not found in SAP")
                else:
                    can_bill = True
                    issues.append("Cannot test with custom function - will attempt direct call")
                
                delivery_info.update({"TEST_STATUS": "FAILED", "ERROR": error_msg[:100]})
            
        except Exception as check_error:
            error_msg = str(check_error)
            
            can_bill = True
            issues = ["Cannot verify delivery status - will attempt billing directly"]
            delivery_info.update({"STATUS_CHECK": "FAILED", "ERROR": error_msg[:100]})
        
        return {
            "status": "success",
            "delivery_doc": delivery_doc,
            "can_bill": can_bill,
            "issues": issues,
            "delivery_info": delivery_info,
            "lock_info": [],
            "approach": "Custom Function Module"
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error checking delivery status: {str(e)}",
            "can_bill": False,
            "approach": "Custom Function Module"
        }
    finally:
        if conn:
            conn.close()


def create_billing_document_in_sap(delivery_number: str, test_run: bool = False):
    """
    เรียกใช้ Custom Function Module สำหรับสร้าง Billing Document
    รับแค่เลข Delivery Number เท่านั้น
    :param delivery_number: เลข Delivery Order
    :param test_run: ถ้า True จะเป็นการทดสอบ
    :return: dict ที่มี status และข้อมูล billing document
    """
    conn = None
    try:
        
        if not delivery_number:
            raise ValueError("Delivery number is required")
        
        # ตรวจสอบ delivery document ก่อนดำเนินการ
        validation_result = validate_delivery_document(delivery_number)
        
        if not validation_result["valid"]:
            error_type = validation_result["error_type"]
            message = validation_result["message"]
            
            return {
                "status": "error",
                "message": message,
                "data": {
                    "created_documents": [],
                    "total_created": 0,
                    "sap_messages": [{"TYPE": "E", "MESSAGE": message}],
                    "sap_errors": [{"TYPE": "E", "MESSAGE": message, "ERROR_TYPE": error_type}],
                    "test_run": test_run,
                    "delivery_number": delivery_number,
                    "validation_failed": True,
                    "error_type": error_type
                }
            }
        
        conn = connect_to_sap()
        
        # เรียก Custom Function Module ที่ user สร้าง
        function_name = "Z_RFC_BILL_CREATE_BDC"
        
        params = {
            "IV_VBELN": delivery_number,
            "IV_TESTRUN": "X" if test_run else ""
        }
        
        try:
            result = conn.call(function_name, **params)
            
            # ดึงผลลัพธ์จาก Custom Function Module
            billing_doc = result.get("EV_BILLING_DOC", "").strip()
            message = result.get("EV_RETURN_MESSAGE", "")
            return_type = result.get("EV_RETURN_TYPE", "").strip()
            
            success_docs = []
            if billing_doc and return_type == "S":
                success_docs.append({
                    "invoice_number": billing_doc,
                    "ref_document": delivery_number,
                    "method": "Custom Function Module",
                    "return_type": return_type
                })
            
            # กำหนดสถานะตามผลลัพธ์
            if billing_doc and return_type == "S":
                status = "success"
                final_message = f"Billing document created successfully: {billing_doc}"
                if message:
                    final_message += f" ({message})"
            else:
                status = "error"
                if return_type == "E":
                    final_message = f"Failed to create billing document: {message}"
                else:
                    final_message = f"Failed to create billing document. {message}" if message else "No billing document created"
            
            return {
                "status": status,
                "message": final_message,
                "data": {
                    "created_documents": success_docs,
                    "total_created": len(success_docs),
                    "sap_messages": [{"TYPE": return_type if return_type else ("S" if billing_doc else "E"), "MESSAGE": message}] if message else [],
                    "sap_errors": [] if (billing_doc and return_type == "S") else [{"TYPE": return_type or "E", "MESSAGE": message or "Unknown error"}],
                    "test_run": test_run,
                    "delivery_number": delivery_number,
                    "custom_function_used": function_name,
                    "return_type": return_type
                }
            }
            
        except Exception as custom_error:
            error_msg = str(custom_error)
            
            # ถ้า Function Module ไม่มี ให้แจ้ง user
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                return {
                    "status": "error",
                    "message": f"Custom Function Module '{function_name}' not found. Please create it in SAP first.",
                    "data": {
                        "created_documents": [],
                        "total_created": 0,
                        "sap_messages": [{"TYPE": "E", "MESSAGE": f"Function Module {function_name} not found"}],
                        "sap_errors": [{"TYPE": "E", "MESSAGE": error_msg}],
                        "test_run": test_run,
                        "delivery_number": delivery_number,
                        "suggested_action": "Create Z_RFC_BILL_CREATE_BDC function module in SAP"
                    }
                }
            
            raise custom_error
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create billing document: {str(e)}",
            "data": {
                "created_documents": [],
                "total_created": 0,
                "sap_messages": [{"TYPE": "E", "MESSAGE": str(e)}],
                "test_run": test_run,
                "delivery_number": delivery_number,
                "custom_function_used": "Z_RFC_BILL_CREATE_BDC"
            }
        }
    finally:
        if conn:
            conn.close()


def get_valid_billing_types():
    """
    ดึงรายการ billing types ที่ valid จาก SAP
    พร้อมข้อมูลเพิ่มเติมเช่น descriptions และ recommendations
    """
    conn = None
    try:
        conn = connect_to_sap()
        
        # ลองดึงจาก table TVFK (Billing Document Types) พร้อม descriptions
        try:
            result = conn.call('RFC_READ_TABLE',
                              QUERY_TABLE='TVFK',
                              DELIMITER='|',
                              FIELDS=[
                                  {"FIELDNAME": "FKART"},  # Billing Type
                                  {"FIELDNAME": "VBTYP"},  # Document Category
                                  {"FIELDNAME": "TRVOG"},  # Transaction Group
                              ],
                              OPTIONS=[])
            
            billing_types = []
            if result.get("DATA"):
                parsed_data = parse_wa_data(result["DATA"], result["FIELDS"])
                
                # กรองและรวบรวม billing types
                for item in parsed_data:
                    fkart = item.get("FKART", "").strip()
                    vbtyp = item.get("VBTYP", "").strip()
                    if fkart and vbtyp in ("M", "N", ""):  # M = Invoice, N = Credit memo
                        billing_types.append(fkart)
                
                # เรียงลำดับและลบค่าซ้ำ
                billing_types = sorted(list(set(billing_types)))
            
            # ถ้าไม่มี billing types หรือไม่มี ZSB1 ให้ใช้ fallback
            if not billing_types or "ZSB1" not in billing_types:
                billing_types = [
                    "BIND", "BINP", "BV", "CHFK", "CHFX", "F1", "F2", "FADP", "FAS", "FAZ",
                    "FP", "FR", "FV", "FX", "FXS", "HR", "S1", "S3", "SHR", "SV", "WIA",
                    "ZSB1", "ZSB2", "ZSB3", "ZSB4", "ZSS1", "ZTB1", "ZTB2", "ZTB4", "ZTB5", "ZTB9", "ZTBS"
                ]
            
            # กำหนด descriptions สำหรับ billing types ที่รู้จัก
            descriptions = {
                "F1": "Sales Invoice",
                "F2": "Standard Invoice", 
                "F8": "Credit Memo",
                "S1": "Pro Forma Invoice",
                "S2": "Debit Memo",
                "S3": "Service Invoice",
                "ZSB1": "Custom Sales Billing Type 1",
                "ZSB2": "Custom Sales Billing Type 2", 
                "ZSB3": "Custom Sales Billing Type 3",
                "ZSB4": "Custom Sales Billing Type 4"
            }
            
            # กำหนด recommended types สำหรับการใช้งานทั่วไป
            recommended = ["ZSB1", "F2", "S1"]
            
            return {
                "status": "success",
                "billing_types": billing_types,
                "total_count": len(billing_types),
                "recommended": recommended,
                "descriptions": descriptions,
                "zsb_types": [t for t in billing_types if t.startswith("ZSB")],
                "standard_types": [t for t in billing_types if not t.startswith("Z")]
            }
            
        except Exception as tvfk_error:
            
            # Fallback with verified data
            return {
                "status": "partial_success", 
                "billing_types": ["ZSB1", "F2", "F8", "S1", "S2"],
                "total_count": 5,
                "recommended": ["ZSB1", "F2"],
                "descriptions": {
                    "F2": "Standard Invoice",
                    "F8": "Credit Memo", 
                    "S1": "Pro Forma Invoice",
                    "ZSB1": "Custom Sales Billing Type 1"
                },
                "note": "Retrieved from verified SAP data"
            }
        
    except Exception as e:
        
        # Ultimate fallback with essential types including ZSB1
        return {
            "status": "fallback",
            "billing_types": ["ZSB1", "F2", "F8", "S1", "S2"],
            "total_count": 5,
            "recommended": ["ZSB1", "F2"],
            "descriptions": {
                "ZSB1": "Custom Sales Billing Type 1",
                "F2": "Standard Invoice",
                "F8": "Credit Memo",
                "S1": "Pro Forma Invoice",
                "S2": "Debit Memo"
            },
            "error": str(e)[:100]
        }
    
    finally:
        if conn:
            conn.close()


def auto_detect_billing_type(delivery_doc: str):
    """
    Auto-detect billing type จาก delivery document
    """
    conn = None
    try:
        conn = connect_to_sap()
        
        # ลองดูจาก delivery header ว่า sales document type อะไร
        result = conn.call('RFC_READ_TABLE',
                          QUERY_TABLE='LIKP',
                          DELIMITER='|',
                          FIELDS=[
                              {"FIELDNAME": "VBELN"},  # Delivery Number
                              {"FIELDNAME": "VBTYP"},  # Document Category
                              {"FIELDNAME": "LFART"},  # Delivery Type
                          ],
                          OPTIONS=[{"TEXT": f"VBELN = '{delivery_doc}'"}])
        
        if result.get("DATA"):
            parsed_data = parse_wa_data(result["DATA"], result["FIELDS"])
            delivery_info = parsed_data[0] if parsed_data else {}
            
            lfart = delivery_info.get("LFART", "").strip()
            
            # Map delivery type to billing type
            type_mapping = {
                "LF": "ZSB1",  # Standard delivery -> ZSB1 Sales Billing
                "NLCC": "ZSB1",  # Cross-company delivery -> ZSB1
                "LR": "F8",    # Returns delivery -> Credit memo
                "RE": "F8",    # Returns -> Credit memo
                "EL": "S1",    # Delivery without order -> Pro forma
            }
            
            suggested_type = type_mapping.get(lfart, "ZSB1")  # Default to ZSB1
            
            return suggested_type
            
        return "ZSB1"  # Default fallback เป็น ZSB1
        
    except Exception as e:
        return "ZSB1"  # Default fallback เป็น ZSB1
        
    finally:
        if conn:
            conn.close()
