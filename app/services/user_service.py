"""
User Service - Employee Authentication and Profile Management
Handles employee authentication and user profile operations
"""
from typing import Dict, Optional
from app.services.database_service import DatabaseService


class UserService:
    """
    Service for handling employee authentication and user management
    """
    
    @staticmethod
    def authenticate_employee(employee_id: str, password: str) -> Optional[Dict[str, str]]:
        """
        Authenticate employee with employee_id and password
        
        Args:
            employee_id (str): Employee ID
            password (str): Last 4 digits of employee card
        
        Returns:
            Dict with employee info or None if authentication failed
        """
        try:
            query = """
                SELECT ME.EMPLOYEE_ID, 
                    ME.EMPLOYEE_CARD,
                    CONCAT(ME.FIRST_NAME_TH, CONCAT(' ', ME.LAST_NAME_TH)) AS EMPLOYEE_NAME
                FROM MASTER_EMPLOYEES ME
                WHERE EMPLOYEE_ID = :employee_id 
                AND ACTIVE = '1'
            """
            row = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=True,
                fetch_all=False
            )
            if row:
                employee_card = row[1]
                if employee_card and employee_card[-4:] == password:
                    employee_info = {
                        "employee_id": row[0],
                        "employee_card": row[1],
                        "employee_name": row[2]
                    }
                    return employee_info
                else:
                    return None
            return None
        except Exception:
            return None

    @staticmethod
    def get_employee_profile(employee_id: str) -> Optional[Dict[str, str]]:
        """
        Get employee profile information
        
        Args:
            employee_id (str): Employee ID
        
        Returns:
            Dict with employee profile or None if not found
        """
        def safe_lob_to_str(val):
            try:
                return str(val.read()) if hasattr(val, 'read') else str(val)
            except Exception:
                return None
        try:
            query = """
                SELECT ME.EMPLOYEE_ID, 
                    ME.EMPLOYEE_CARD,
                    CONCAT(ME.FIRST_NAME_TH, CONCAT(' ', ME.LAST_NAME_TH)) AS EMPLOYEE_NAME,
                    DI.DIVISION_DESC_TH,
                    MD.DEPARTMENT_NAME_TH,
                    MS.SECTION_NAME,
                    MN.NATIONALITY,
                    ME.DEPARTMENT_ID
                FROM MASTER_EMPLOYEES ME
                LEFT JOIN MASTER_DEPARTMENT MD ON MD.DEPARTMENT_ID = ME.DEPARTMENT_ID
                LEFT JOIN MASTER_DIVISION DI ON DI.DIVISION_ID = ME.DIVISION_ID
                LEFT JOIN MASTER_SECTION MS ON MS.SECTION_ID = ME.SECTION_ID
                LEFT JOIN MASTER_NATIONALITY MN ON MN.NATIONALITY_ID = ME.NATIONALITY_ID 
                WHERE ME.EMPLOYEE_ID = :employee_id 
                AND ME.ACTIVE = '1'
            """
            row = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=True,
                fetch_all=False
            )
            if row:
                profile = {
                    "employee_id": safe_lob_to_str(row[0]),
                    "employee_card": safe_lob_to_str(row[1]),
                    "employee_name": safe_lob_to_str(row[2]),
                    "division_desc_th": safe_lob_to_str(row[3]),
                    "department_name_th": safe_lob_to_str(row[4]),
                    "section_name": safe_lob_to_str(row[5]),
                    "nationality": safe_lob_to_str(row[6]),
                    "department": safe_lob_to_str(row[7])
                }
                return profile
            return None
        except Exception:
            return None

    
    @staticmethod
    def validate_employee_exists(employee_id: str) -> bool:
        """
        Check if employee exists and is active
        
        Args:
            employee_id (str): Employee ID
            
        Returns:
            bool: True if employee exists and is active, False otherwise
        """
        try:
            
            query = """
                SELECT COUNT(1)
                FROM MASTER_EMPLOYEES
                WHERE EMPLOYEE_ID = :employee_id 
                AND ACTIVE = '1'
            """
            
            row = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=True,
                fetch_all=False
            )
            
            exists = row[0] > 0 if row else False
            
            return exists
            
        except Exception as e:
            return False
