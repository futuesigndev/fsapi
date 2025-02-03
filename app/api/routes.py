import logging
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.sap_service import call_bapi  # นำเข้า SAP service

router = APIRouter()

class CallFunctionRequest(BaseModel):
    function_name: str
    parameters: Dict[str, Dict[str, Any]]

def load_metadata(function_name: str) -> Dict[str, Any]:
    """
    โหลด Metadata JSON จากไฟล์
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    metadata_file = os.path.join(base_dir, "metadata", f"{function_name}.json")

    if not os.path.exists(metadata_file):
        raise HTTPException(status_code=404, detail=f"Metadata for function '{function_name}' not found.")

    with open(metadata_file, "r", encoding="utf-8") as file:
        return json.load(file)

def validate_input_parameters(parameters: Dict[str, Any], metadata: Dict[str, Any]):
    """
    ตรวจสอบ input_parameters ว่าครบถ้วนหรือไม่
    """
    required_inputs = extract_required_fields(metadata.get("input_parameters", {}))
    missing_inputs = [field for field in required_inputs if not extract_nested_value(parameters.get("input", {}), field)]

    if missing_inputs:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required input parameters: {', '.join(missing_inputs)}"
        )

def validate_table_parameters(parameters: Dict[str, Any], metadata: Dict[str, Any]):
    """
    ตรวจสอบ table_parameters ว่าครบถ้วนหรือไม่
    """
    table_parameters_meta = metadata.get("table_parameters", {})
    request_tables = parameters.get("tables", {})

    if table_parameters_meta:
        for table_name, table_meta in table_parameters_meta.items():
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
                if field_meta.get("required", False)
            ]

            # รองรับทั้ง dict (1 แถว) และ list (หลายแถว)
            if isinstance(fields, dict):
                missing_fields = [field for field in required_fields if field not in fields]
            elif isinstance(fields, list):
                missing_fields = []
                for row in fields:
                    missing_fields.extend([field for field in required_fields if field not in row])

            if missing_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required fields in table '{table_name}': {', '.join(missing_fields)}"
                )

@router.post("/sap/call-function")
async def call_function_api(request: CallFunctionRequest):
    try:
        metadata = load_metadata(request.function_name)
        validate_input_parameters(request.parameters, metadata)
        validate_table_parameters(request.parameters, metadata)

        sap_data = prepare_sap_data(request.parameters, metadata)
        sap_response = call_bapi(request.function_name, sap_data)

        if sap_response.get("status") == "error":
            raise HTTPException(status_code=500, detail=sap_response.get("message"))

        filtered_response = filter_sap_response(sap_response.get("data", {}), metadata)

        error_found = any(entry["TYPE"] != "S" for entry in filtered_response.get("RETURN", []))
        status = "error" if error_found else "success"
        message = "Execution completed with errors." if error_found else "Execution completed."

        return {
            "status": status,
            "message": message,
            "sap_response": filtered_response,
        }

    except Exception as e:
        logging.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def prepare_sap_data(parameters: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    แปลงข้อมูลจาก JSON Request ให้ตรงกับโครงสร้างที่ SAP คาดหวัง
    """
    if not isinstance(parameters, dict):
        raise ValueError(f"parameters must be a dictionary, but got {type(parameters).__name__}")

    input_parameters = {
        key: (f"{val.split('.')[2]}{val.split('.')[1]}{val.split('.')[0]}" if key == "I_DATE" and val else val)
        for key, val in parameters.get("input", {}).items()
        if key in metadata.get("input_parameters", {})
    }

    table_parameters = {
        table_name: (
            [fields] if isinstance(fields := parameters["tables"].get(table_name, {}).get("fields", {}), dict) else fields
        )
        for table_name in metadata.get("table_parameters", {})
        if table_name in parameters.get("tables", {})
    }

    return {**input_parameters, **table_parameters}

def filter_sap_response(raw_response: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    กรองเฉพาะข้อมูลสำคัญจาก SAP Response โดยอิงโครงสร้าง metadata
    """
    output_parameters = metadata.get("output_parameters", {})

    return {
        key: ([{sub_key: entry.get(sub_key, "") for sub_key in value.keys()} for entry in raw_response[key]]
              if isinstance(value, dict) and key in raw_response and isinstance(raw_response[key], list)
              else raw_response.get(key, ""))
        for key, value in output_parameters.items()
    }

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
        if isinstance(value, dict) and value.get("required", False):
            required_fields.append(current_key)
        elif isinstance(value, dict):
            required_fields.extend(extract_required_fields(value, current_key))
    return required_fields
