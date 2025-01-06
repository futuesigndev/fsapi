import logging
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

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
        logging.debug(f"Debug - Metadata file path: {metadata_file}")

        # โหลด Metadata JSON
        with open(metadata_file, "r", encoding="utf-8") as file:
            metadata = json.load(file)
            logging.debug(f"Debug - Loaded metadata: {json.dumps(metadata, indent=2)}")

        # ตรวจสอบ input_parameters
        logging.debug("Debug - Starting to extract required fields")
        required_inputs = extract_required_fields(metadata["input_parameters"])
        logging.debug(f"Debug - Extracted Required Inputs: {required_inputs}")

        logging.debug("Debug - Validating required inputs")
        missing_inputs = []
        for field in required_inputs:
            value = extract_nested_value(request.parameters["input"], field)
            if value is None or value == "":
                missing_inputs.append(field)

        logging.debug(f"Debug - Missing Inputs: {missing_inputs}")

        if missing_inputs:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required input parameters: {', '.join(missing_inputs)}"
            )

        return {
            "status": "success",
            "message": f"Function '{request.function_name}' JSON validation passed."
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Metadata for function '{request.function_name}' not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding metadata file for '{request.function_name}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
