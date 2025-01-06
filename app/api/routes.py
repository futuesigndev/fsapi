import logging
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.sap_service import call_bapi  # เพิ่มการนำเข้า SAP service

router = APIRouter()

class CallFunctionRequest(BaseModel):
    function_name: str
    parameters: Dict[str, Dict[str, Any]]

@router.post("/sap/call-function")
async def call_function_api(request: CallFunctionRequest):
    try:
        # ระบุเส้นทาง Metadata
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        metadata_file = os.path.join(base_dir, "metadata", f"{request.function_name}.json")

        # โหลด Metadata JSON
        with open(metadata_file, "r", encoding="utf-8") as file:
            metadata = json.load(file)

        # ตรวจสอบ input_parameters
        required_inputs = extract_required_fields(metadata["input_parameters"])
        missing_inputs = [
            field for field in required_inputs
            if not extract_nested_value(request.parameters["input"], field)
        ]
        if missing_inputs:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required input parameters: {', '.join(missing_inputs)}"
            )

        # ตรวจสอบ table_parameters
        request_tables = request.parameters.get("tables", {})
        if not request_tables:
            raise HTTPException(
                status_code=400,
                detail="Request table parameters are missing or empty"
            )

        for table_name, table_meta in metadata["table_parameters"].items():
            if table_name not in request_tables:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required table parameter: {table_name}"
                )

            fields = request_tables[table_name].get("fields", {})
            if not fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Table '{table_name}' has no fields"
                )

            required_fields = [
                field_name for field_name, field_meta in table_meta["fields"].items()
                if field_meta["required"]
            ]
            missing_fields = [field for field in required_fields if not fields.get(field)]
            if missing_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required fields in table '{table_name}': {', '.join(missing_fields)}"
                )

        # เตรียมข้อมูลสำหรับส่งไปยัง SAP
        sap_data = prepare_sap_data(request.parameters, metadata)
        # **Log ข้อมูล sap_data**
        #logging.debug(f"Debug - SAP Data being sent: {json.dumps(sap_data, indent=2, default=str)}")


        # **เรียก SAP**
        sap_response = call_bapi(request.function_name, sap_data)
        #logging.debug(f"Debug - SAP Data being sentBack: {json.dumps(sap_response, indent=2, default=str)}")

        # ตรวจสอบข้อผิดพลาดใน Response
        if sap_response.get("status") == "error":
            raise HTTPException(status_code=500, detail=sap_response.get("message"))

        # **กรองข้อมูลผลลัพธ์**
        filtered_response = filter_sap_response(sap_response.get("data", {}), metadata)

         # ตรวจสอบ TYPE ใน RETURN
        error_found = any(entry["TYPE"] != "S" for entry in filtered_response.get("RETURN", []))
        status = "error" if error_found else "success"
        message = (
            "Execution completed with errors." if error_found else "Execution completed."
        )

        # ส่งผลลัพธ์กลับ
        return {
            "status": status,
            "message": message,
            "sap_response": filtered_response,
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Metadata for function '{request.function_name}' not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding metadata file for '{request.function_name}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def prepare_sap_data(parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    แปลงข้อมูลจาก JSON Request ให้ตรงกับโครงสร้างที่ SAP คาดหวัง
    """
    # ตรวจสอบว่า parameters เป็น dict
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")

    # เตรียมข้อมูล Import Parameters
    input_parameters = {
        key: parameters.get("input", {}).get(key)
        for key in metadata.get("input_parameters", {})
    }

    # เตรียมข้อมูล Table Parameters
    table_parameters = {}
    for table_name, table_meta in metadata.get("table_parameters", {}).items():
        if table_name in parameters.get("tables", {}):
            fields = parameters["tables"][table_name].get("fields", {})
            if not isinstance(fields, dict):
                raise ValueError(f"fields in table '{table_name}' must be a dictionary")
            table_parameters[table_name] = [
                {
                    field_name: field_value
                    for field_name, field_value in fields.items()
                }
            ]

    return {
        **input_parameters,
        **table_parameters
    }



def filter_sap_response(raw_response: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    กรองเฉพาะข้อมูลสำคัญจาก SAP Response โดยอิงโครงสร้าง metadata
    """
    output_parameters = metadata.get("output_parameters", {})
    return_data = {}

    # กรองข้อมูลที่ระบุใน output_parameters
    for key, value in output_parameters.items():
        if isinstance(value, dict):  # สำหรับโครงสร้าง nested เช่น RETURN
            if key in raw_response and isinstance(raw_response[key], list):
                return_data[key] = [
                    {
                        sub_key: entry.get(sub_key, "")
                        for sub_key in value.keys()
                    }
                    for entry in raw_response[key]
                ]
            else:
                return_data[key] = raw_response.get(key, "")
        else:  # สำหรับโครงสร้าง simple
            return_data[key] = raw_response.get(key, "")

    return return_data


def extract_nested_value(data, keys):
    """
    ค้นหาค่าจาก JSON แบบ nested ตาม path ที่ระบุใน keys
    """
    for key in keys.split('.'):
        if key in data:
            data = data[key]
        else:
            return None
    return data


def extract_required_fields(parameters, parent_key=""):
    """
    ดึงฟิลด์ที่มี required = true จาก metadata
    """
    required_fields = []
    for key, value in parameters.items():
        current_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict) and "required" in value:
            if value["required"]:
                required_fields.append(current_key)
        elif isinstance(value, dict):
            required_fields.extend(extract_required_fields(value, current_key))
    return required_fields
