"""
User Service - Employee Authentication and Profile Management
Handles employee authentication and user profile operations
"""
import logging
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
            password (str): Employee password
            
        Returns:
            Dict with employee info or None if authentication failed
        """
        try:
            # Note: This is a placeholder implementation
            # In real implementation, you would:
            # 1. Hash the password properly
            # 2. Use secure password comparison
            # 3. Implement proper user table structure
            
            query = """
                SELECT EMPLOYEE_ID, EMPLOYEE_NAME, DEPARTMENT, EMAIL, ROLE
                FROM EMPLOYEE_MASTER
                WHERE EMPLOYEE_ID = :employee_id 
                AND PASSWORD = :password
                AND ACTIVE = 'Y'
            """
            
            row = DatabaseService.execute_query(
                query=query,
                params={
                    "employee_id": employee_id,
                    "password": password  # TODO: Implement proper password hashing
                },
                fetch_one=True,
                fetch_all=False
            )
            
            if row:
                employee_info = {
                    "employee_id": row[0],
                    "employee_name": row[1],
                    "department": row[2],
                    "email": row[3],
                    "role": row[4]
                }
                
                logging.debug(f"Employee {employee_id} authenticated successfully")
                return employee_info
            
            logging.debug(f"Authentication failed for employee {employee_id}")
            return None
            
        except Exception as e:
            logging.error(f"Error authenticating employee {employee_id}: {e}")
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
        try:
            query = """
                SELECT 
                    EMPLOYEE_ID, 
                    EMPLOYEE_NAME, 
                    DEPARTMENT, 
                    EMAIL, 
                    ROLE,
                    PHONE,
                    POSITION,
                    MANAGER_ID,
                    CREATED_DATE,
                    LAST_LOGIN
                FROM EMPLOYEE_MASTER
                WHERE EMPLOYEE_ID = :employee_id 
                AND ACTIVE = 'Y'
            """
            
            row = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=True,
                fetch_all=False
            )
            
            if row:
                profile = {
                    "employee_id": row[0],
                    "employee_name": row[1],
                    "department": row[2],
                    "email": row[3],
                    "role": row[4],
                    "phone": row[5] if row[5] else "",
                    "position": row[6] if row[6] else "",
                    "manager_id": row[7] if row[7] else "",
                    "created_date": row[8].strftime("%Y-%m-%d") if row[8] else "",
                    "last_login": row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else ""
                }
                
                logging.debug(f"Profile retrieved for employee {employee_id}")
                return profile
            
            logging.debug(f"Employee profile not found for {employee_id}")
            return None
            
        except Exception as e:
            logging.error(f"Error retrieving profile for employee {employee_id}: {e}")
            return None

    @staticmethod
    def update_last_login(employee_id: str) -> bool:
        """
        Update employee's last login timestamp
        
        Args:
            employee_id (str): Employee ID
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            query = """
                UPDATE EMPLOYEE_MASTER 
                SET LAST_LOGIN = SYSDATE
                WHERE EMPLOYEE_ID = :employee_id
            """
            
            rows_affected = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=False,
                fetch_all=False
            )
            
            if rows_affected > 0:
                logging.debug(f"Last login updated for employee {employee_id}")
                return True
            else:
                logging.debug(f"No rows updated for employee {employee_id}")
                return False
                
        except Exception as e:
            logging.error(f"Error updating last login for employee {employee_id}: {e}")
            return False

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
                FROM EMPLOYEE_MASTER
                WHERE EMPLOYEE_ID = :employee_id 
                AND ACTIVE = 'Y'
            """
            
            row = DatabaseService.execute_query(
                query=query,
                params={"employee_id": employee_id},
                fetch_one=True,
                fetch_all=False
            )
            
            exists = row[0] > 0 if row else False
            logging.debug(f"Employee {employee_id} exists: {exists}")
            
            return exists
            
        except Exception as e:
            logging.error(f"Error checking if employee {employee_id} exists: {e}")
            return False
