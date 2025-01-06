import cx_Oracle
from app.config import Config

def connect_to_oracle():
    """
    ฟังก์ชันสำหรับเชื่อมต่อ Oracle Database
    """
    connection = cx_Oracle.connect(
        user=Config.ORACLE_USER,
        password=Config.ORACLE_PASSWORD,
        dsn=Config.ORACLE_DSN,
        encoding=Config.ORACLE_CHARSET
    )
    return connection

def get_user_credentials(client_id: str):
    """
    ดึง CLIENT_ID และ CLIENT_SECRET จาก Oracle
    """
    connection = None
    cursor = None
    try:
        connection = connect_to_oracle()
        query = """
            SELECT CLIENT_ID, CLIENT_SECRET, ID_BABI
            FROM FSAPI_USER
            WHERE CLIENT_ID = :client_id
        """
        cursor = connection.cursor()
        cursor.execute(query, client_id=client_id)
        row = cursor.fetchone()

        if row:
            return {
                "client_id": row[0],
                "client_secret": row[1],
                "id_babi": row[2]
            }
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to fetch user credentials: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def get_function_names(client_id: str):
    connection = connect_to_oracle()
    try:
        query = """
        WITH BAPI_SPLIT AS (
            SELECT 
                TRIM(REGEXP_SUBSTR(ID_BABI, '[^,]+', 1, LEVEL)) AS BAPI_ID
            FROM 
                FSAPI_USER
            WHERE 
                CLIENT_ID = :client_id
            CONNECT BY 
                LEVEL <= REGEXP_COUNT(ID_BABI, ',') + 1
                AND PRIOR CLIENT_ID = CLIENT_ID
                AND PRIOR SYS_GUID() IS NOT NULL
        )
        SELECT 
            FSAPI_BABI.BABI AS FUNCTION_NAME,
            FSAPI_BABI.DETAIL AS FUNCTION_DETAIL
        FROM 
            BAPI_SPLIT
        LEFT JOIN 
            FSAPI_BABI
        ON 
            TO_NUMBER(BAPI_SPLIT.BAPI_ID) = FSAPI_BABI.ID
        ORDER BY 
            FSAPI_BABI.BABI
        """
        cursor = connection.cursor()
        cursor.execute(query, client_id=client_id)
        rows = cursor.fetchall()
        result = [{"function_name": row[0], "function_detail": row[1]} for row in rows]
        #logging.debug(f"Functions fetched for {client_id}: {result}")
        return result
    except Exception as e:
        #logging.error(f"Error fetching functions for {client_id}: {e}")
        raise RuntimeError("Failed to fetch function names.")
    finally:
        connection.close()

