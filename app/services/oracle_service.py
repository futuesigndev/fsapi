import logging
from app.services.database_service import DatabaseService

def get_user_credentials(client_id: str):
    """
    ดึง CLIENT_ID และ CLIENT_SECRET จาก Oracle
    Migrated to use DatabaseService for better connection management
    """
    try:
        query = """
            SELECT CLIENT_ID, CLIENT_SECRET, ID_BABI
            FROM FSAPI_USER
            WHERE CLIENT_ID = :client_id
        """
        
        row = DatabaseService.execute_query(
            query=query,
            params={"client_id": client_id},
            fetch_one=True,
            fetch_all=False
        )

        if row:
            return {
                "client_id": row[0],
                "client_secret": row[1],
                "id_babi": row[2]
            }
        return None
    except Exception as e:
        logging.error(f"Failed to fetch user credentials: {str(e)}")
        raise RuntimeError(f"Failed to fetch user credentials: {str(e)}")

def get_function_names(client_id: str):
    """
    Get authorized SAP functions for client
    Migrated to use DatabaseService for better connection management
    """
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
        
        rows = DatabaseService.execute_query(
            query=query,
            params={"client_id": client_id},
            fetch_all=True
        )
        
        result = [{"function_name": row[0], "function_detail": row[1]} for row in rows]
        logging.debug(f"Functions fetched for {client_id}: {result}")
        return result
    except Exception as e:
        logging.error(f"Error fetching functions for {client_id}: {e}")
        raise RuntimeError("Failed to fetch function names.")

