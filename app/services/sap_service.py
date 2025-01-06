from pyrfc import Connection
from app.config import Config

def connect_to_sap():
    # เชื่อมต่อ SAP ด้วยข้อมูลการเชื่อมต่อจาก Config
    return Connection(
        ashost=Config.SAP_HOST,
        sysnr=Config.SAP_SYSNR,
        client=Config.SAP_CLIENT,
        user=Config.SAP_USER,
        passwd=Config.SAP_PASSWORD,
        lang=Config.SAP_LANG,
        codepage=Config.SAP_CODEPAGE
    )

def call_bapi(bapi_name: str, params: dict):
    """
    เรียก SAP BAPI และส่งพารามิเตอร์
    """
    conn = None
    try:
        conn = connect_to_sap()
        result = conn.call(bapi_name, **params)  # เรียก BAPI ด้วยชื่อและพารามิเตอร์
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()

    
def call_rfc_read_table(table, fields, where_conditions):
    conn = connect_to_sap()
    try:
        result = conn.call('RFC_READ_TABLE', 
                           QUERY_TABLE=table,
                           DELIMITER="|",
                           FIELDS=[{"FIELDNAME": field} for field in fields],
                           OPTIONS=[{"TEXT": where_conditions}])

        # ตรวจสอบว่ามีข้อมูลใน result["DATA"] หรือไม่
        record_found = bool(result.get("DATA"))

        # ถ้าไม่มีข้อมูลให้กำหนด DATA เป็นค่าว่าง
        parsed_data = parse_wa_data(result["DATA"], result["FIELDS"]) if record_found else []

        return {
            "status": "success",
            "record_found": record_found,  # true ถ้ามีข้อมูล, false ถ้าไม่มีข้อมูล
            "data": {
                "DATA": parsed_data,           # ส่ง DATA ที่แปลงแล้วกลับไป
                "FIELDS": result["FIELDS"],
                "OPTIONS": result["OPTIONS"]
            }
        }
    except Exception as e:
        return {"status": "failed", "message": str(e)}

def test_sap_connection():
    try:
        conn = connect_to_sap()
        # ทดสอบการเชื่อมต่อด้วยคำสั่ง ping หรือฟังก์ชันที่ไม่มีผลกระทบกับระบบ SAP
        conn.ping()
        print("Connection to SAP was successful.")
    except Exception as e:
        print(f"Failed to connect to SAP: {e}")

def parse_wa_data(data, fields):
    parsed_data = []
    for entry in data:
        wa_values = entry["WA"].split("|")  # แยกข้อมูลตามตัวคั่น "|"
        parsed_entry = {fields[i]["FIELDNAME"]: wa_values[i] for i in range(len(fields))}
        parsed_data.append(parsed_entry)
    return parsed_data

