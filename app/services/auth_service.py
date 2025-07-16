"""
Authentication Service - Client Credentials Validation
Handles client authentication and SAP function permissions
"""
import logging
from typing import Dict, List, Optional
from app.services.database_service import DatabaseService


class AuthService:
    """
    Service for handling client authentication and authorization
    """
    
    @staticmethod
    def get_client_credentials(client_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve client credentials from database
        
        Args:
            client_id (str): Client ID to lookup
            
        Returns:
            Dict with client_id, client_secret, id_babi or None if not found
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
            
            logging.debug(f"Client {client_id} not found in database")
            return None
            
        except Exception as e:
            logging.error(f"Failed to fetch client credentials for {client_id}: {e}")
            raise RuntimeError(f"Failed to fetch client credentials: {str(e)}")

    @staticmethod
    def verify_client_credentials(client_id: str, client_secret: str) -> bool:
        """
        Verify client credentials
        
        Args:
            client_id (str): Client ID
            client_secret (str): Client secret
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            credentials = AuthService.get_client_credentials(client_id)
            
            if not credentials:
                logging.debug(f"Client {client_id} not found")
                return False
                
            if credentials["client_secret"] != client_secret:
                logging.debug(f"Invalid client_secret for {client_id}")
                return False
                
            logging.debug(f"Client {client_id} credentials verified successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error verifying credentials for {client_id}: {e}")
            return False

    @staticmethod
    def get_authorized_functions(client_id: str) -> List[Dict[str, str]]:
        """
        Get list of SAP functions that client is authorized to use
        
        Args:
            client_id (str): Client ID
            
        Returns:
            List of authorized functions with function_name and function_detail
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
            
            result = [
                {
                    "function_name": row[0],
                    "function_detail": row[1]
                }
                for row in rows if row[0]  # Filter out None values
            ]
            
            logging.debug(f"Functions fetched for {client_id}: {len(result)} functions")
            return result
            
        except Exception as e:
            logging.error(f"Error fetching authorized functions for {client_id}: {e}")
            raise RuntimeError(f"Failed to fetch authorized functions: {str(e)}")

    @staticmethod
    def is_function_authorized(client_id: str, function_name: str) -> bool:
        """
        Check if client is authorized to use specific SAP function
        
        Args:
            client_id (str): Client ID
            function_name (str): SAP function name to check
            
        Returns:
            bool: True if authorized, False otherwise
        """
        try:
            # TEMPORARY: Allow all functions for testing
            # TODO: Remove this bypass in production
            if function_name in ['ZMAST_CUSTOMER', 'Z_GET_MATERIALS', 'ZMAST_BOM']:
                logging.info(f"BYPASS: Allowing {function_name} for {client_id} (testing mode)")
                return True
            
            authorized_functions = AuthService.get_authorized_functions(client_id)
            function_names = [func["function_name"] for func in authorized_functions]
            
            is_authorized = function_name in function_names
            logging.debug(f"Function {function_name} authorization for {client_id}: {is_authorized}")
            
            return is_authorized
            
        except Exception as e:
            logging.error(f"Error checking function authorization: {e}")
            return False
