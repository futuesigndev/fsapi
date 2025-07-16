"""
Customer Service - Customer Data Operations
Handles customer search and data retrieval from Oracle database
"""
import logging
from typing import Dict, List, Optional
from app.services.database_service import DatabaseService
import re


class CustomerService:
    """
    Service for handling customer data operations
    """
    
    @staticmethod
    def search_customers(
        customer_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, any]:
        """
        Search customers with flexible criteria
        
        Args:
            customer_number (str, optional): Customer number (KUNNR)
            customer_name (str, optional): Customer name (NAME1, NAME2)
            city (str, optional): City (ORT01)
            limit (int): Maximum number of results
            
        Returns:
            Dict with status, message, total_records, and customers list
        """
        try:
            # Build dynamic WHERE clause
            where_conditions = ["1=1"]  # Base condition (no LOEVM field in your table)
            params = {}
            
            if customer_number:
                where_conditions.append("KNA1.KUNNR LIKE :customer_number")
                params["customer_number"] = f"%{customer_number}%"
                
            if customer_name:
                where_conditions.append(
                    "(UPPER(KNA1.NAME1) LIKE UPPER(:customer_name) OR UPPER(KNA1.NAME2) LIKE UPPER(:customer_name))"
                )
                params["customer_name"] = f"%{customer_name}%"
                
            if city:
                where_conditions.append("UPPER(KNA1.ORT01) LIKE UPPER(:city)")
                params["city"] = f"%{city}%"
            
            where_clause = " AND ".join(where_conditions)
            
            # Main query with customer data
            query = f"""
                SELECT 
                    KNA1.KUNNR,           -- Customer Number
                    KNA1.NAME1,           -- Customer Name 1
                    KNA1.NAME2,           -- Customer Name 2
                    KNA1.ORT01,           -- City
                    KNA1.ORT02,           -- District
                    KNA1.STRAS,           -- Street Address
                    KNA1.TELF1,           -- Telephone
                    KNA1.STCD3,           -- Tax Number
                    KNA1.LAND1,           -- Country
                    KNA1.PSTLZ,           -- Postal Code
                    KNA1.REGIO,           -- Region
                    KNA1.TELFX,           -- Fax
                    KNA1.KTOKD,           -- Account Group
                    KNA1.ERDAT            -- Created Date
                FROM KNA1
                WHERE {where_clause}
                AND ROWNUM <= :limit
                ORDER BY KNA1.KUNNR
            """
            
            params["limit"] = limit
            
            rows = DatabaseService.execute_query(
                query=query,
                params=params,
                fetch_all=True
            )
            
            customers = []
            for row in rows:
                customer = {
                    "KUNNR": row[0].strip() if row[0] else "",
                    "NAME1": row[1].strip() if row[1] else "",
                    "NAME2": row[2].strip() if row[2] else "",
                    "ORT01": row[3].strip() if row[3] else "",
                    "ORT02": row[4].strip() if row[4] else "",
                    "STRAS": row[5].strip() if row[5] else "",
                    "TELF1": row[6].strip() if row[6] else "",
                    "STCD3": row[7].strip() if row[7] else "",
                    "LAND1": row[8].strip() if row[8] else "",
                    "PSTLZ": row[9].strip() if row[9] else "",
                    "REGIO": row[10].strip() if row[10] else "",
                    "TELFX": row[11].strip() if row[11] else "",
                    "KTOKD": row[12].strip() if row[12] else "",
                    "ERDAT": row[13].strftime("%Y-%m-%d") if row[13] else ""
                }
                customers.append(customer)
            
            total_records = len(customers)
            message = f"Found {total_records} customer(s)"
            
            logging.debug(f"Customer search completed: {total_records} records found")
            
            return {
                "status": "success",
                "message": message,
                "total_records": total_records,
                "customers": customers
            }
            
        except Exception as e:
            logging.error(f"Error searching customers: {e}")
            return {
                "status": "error",
                "message": f"Customer search failed: {str(e)}",
                "total_records": 0,
                "customers": []
            }

    @staticmethod
    def get_customer_details(customer_number: str) -> Dict[str, any]:
        """
        Get detailed information for specific customer
        
        Args:
            customer_number (str): Customer number (KUNNR)
            
        Returns:
            Dict with customer details or error message
        """
        try:
            # Main customer query from KNA1 + JOIN KNVV + JOIN KNVP (PARVW='WE' AND PARZA=0)
            main_query = """
                SELECT 
                    KNA1.KUNNR,           -- Customer Number
                    KNA1.NAME1,           -- Customer Name 1
                    KNA1.NAME2,           -- Customer Name 2
                    KNA1.ORT01,           -- City
                    KNA1.ORT02,           -- District
                    KNA1.STRAS,           -- Street Address
                    KNA1.TELF1,           -- Telephone
                    KNA1.STCD3,           -- Tax Number
                    KNA1.LAND1,           -- Country
                    KNA1.PSTLZ,           -- Postal Code
                    KNA1.REGIO,           -- Region
                    KNA1.TELFX,           -- Fax
                    KNA1.KTOKD,           -- Account Group
                    KNA1.ERDAT,           -- Created Date
                    KNA1.SORTL,           -- Sort field
                    KNA1.LZONE,           -- Transportation zone
                    KNA1.STCEG,           -- VAT Registration Number
                    KNA1.COMPANY_ID,      -- Company ID
                    NVL(KNVV.VKORG, '') as VKORG,    -- Sales Organization
                    NVL(KNVV.VTWEG, '') as VTWEG,    -- Distribution Channel
                    NVL(KNVV.BZIRK, '') as BZIRK,    -- Sales District
                    NVL(KNVV.VKGRP, '') as VKGRP,    -- Sales Group
                    NVL(KNVV.VKBUR, '') as VKBUR,    -- Sales Office
                    KNVP.SPART,    -- SPART from KNVP (Ship-to Party)
                    NVL(KNVV.ZTERM, '') as ZTERM     -- Payment Terms
                FROM KNA1
                LEFT JOIN KNVV ON KNA1.KUNNR = KNVV.KUNNR
                LEFT JOIN KNVP ON KNA1.KUNNR = KNVP.KUNNR AND KNVP.PARVW = 'WE' AND KNVP.PARZA = 0
                WHERE KNA1.KUNNR = :customer_number
            """
            
            row = DatabaseService.execute_query(
                query=main_query,
                params={"customer_number": customer_number},
                fetch_one=True,
                fetch_all=False
            )
            
            if not row:
                return {
                    "status": "error",
                    "message": f"Customer {customer_number} not found",
                    "customer": None
                }
            
            # Map output fields to match SELECT order and completeness (only fields that exist in your schema)
            customer = {
                "KUNNR": row[0].strip() if row[0] else "",
                "NAME1": row[1].strip() if row[1] else "",
                "NAME2": row[2].strip() if row[2] else "",
                "ORT01": row[3].strip() if row[3] else "",
                "ORT02": row[4].strip() if row[4] else "",
                "STRAS": row[5].strip() if row[5] else "",
                "TELF1": row[6].strip() if row[6] else "",
                "STCD3": row[7].strip() if row[7] else "",
                "LAND1": row[8].strip() if row[8] else "",
                "PSTLZ": row[9].strip() if row[9] else "",
                "REGIO": row[10].strip() if row[10] else "",
                "TELFX": row[11].strip() if row[11] else "",
                "KTOKD": row[12].strip() if row[12] else "",
                "ERDAT": row[13].strftime("%Y-%m-%d") if row[13] else "",
                "SORTL": row[14].strip() if row[14] else "",
                "LZONE": row[15].strip() if row[15] else "",
                "STCEG": row[16].strip() if row[16] else "",
                "COMPANY_ID": str(row[17]) if row[17] is not None else "",
                "VKORG": row[18].strip() if row[18] else "",
                "VTWEG": row[19].strip() if row[19] else "",
                "BZIRK": row[20].strip() if row[20] else "",
                "VKGRP": row[21].strip() if row[21] else "",
                "VKBUR": row[22].strip() if row[22] else "",
                "SPART": row[23].strip() if row[23] else "",
                "ZTERM": row[24].strip() if row[24] else ""
            }
            
            logging.debug(f"Customer details retrieved for {customer_number}")
            
            return {
                "status": "success",
                "message": f"Customer {customer_number} details retrieved",
                "customer": customer
            }
            
        except Exception as e:
            logging.error(f"Error retrieving customer details for {customer_number}: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve customer details: {str(e)}",
                "customer": None
            }

    @staticmethod
    def validate_customer_exists(customer_number: str) -> bool:
        """
        Check if customer exists and is not deleted
        
        Args:
            customer_number (str): Customer number (KUNNR)
            
        Returns:
            bool: True if customer exists, False otherwise
        """
        try:
            query = """
                SELECT COUNT(1)
                FROM KNA1
                WHERE KUNNR = :customer_number
            """
            
            row = DatabaseService.execute_query(
                query=query,
                params={"customer_number": customer_number},
                fetch_one=True,
                fetch_all=False
            )
            
            exists = row[0] > 0 if row else False
            logging.debug(f"Customer {customer_number} exists: {exists}")
            
            return exists
            
        except Exception as e:
            logging.error(f"Error checking if customer {customer_number} exists: {e}")
            return False

    @staticmethod
    def get_customer_sales_views(customer_number: str) -> Dict[str, any]:
        """
        Get customer sales organization views from KNA1VV
        
        Args:
            customer_number (str): Customer number (KUNNR)
            
        Returns:
            Dict with sales views data or error message
        """
        try:
            query = """
                SELECT 
                    KUNNR,               -- Customer Number
                    VKORG,               -- Sales Organization
                    VTWEG,               -- Distribution Channel
                    ERDAT,               -- Created Date
                    KTOKD,               -- Account Group
                    NAME1,               -- Customer Name
                    KDGRP,               -- Customer Group
                    BZIRK,               -- Sales District
                    INCO1,               -- Incoterms
                    LPRIO,               -- Delivery Priority
                    EIKTO,               -- Customer Account Number
                    VSBED,               -- Shipping Conditions
                    KTGRD,               -- Account Assignment Group
                    ZTERM,               -- Payment Terms
                    VWERK,               -- Delivering Plant
                    VKGRP,               -- Sales Group
                    VKBUR,               -- Sales Office
                    AUFSD,               -- Order Block
                    FAKSD,               -- Billing Block
                    LIFSD,               -- Delivery Block
                    LOEVM,               -- Deletion Flag
                    SPERR,               -- Central Posting Block
                    COMPANY_ID           -- Company ID
                FROM KNA1VV
                WHERE KUNNR = :customer_number
                ORDER BY VKORG, VTWEG
            """
            
            rows = DatabaseService.execute_query(
                query=query,
                params={"customer_number": customer_number},
                fetch_all=True
            )
            
            if not rows:
                return {
                    "status": "success",
                    "message": f"No sales views found for customer {customer_number}",
                    "sales_views": []
                }
            
            sales_views = []
            for row in rows:
                sales_view = {
                    "KUNNR": row[0].strip() if row[0] else "",
                    "VKORG": row[1].strip() if row[1] else "",
                    "VTWEG": row[2].strip() if row[2] else "",
                    "ERDAT": row[3].strftime("%Y-%m-%d") if row[3] else "",
                    "KTOKD": row[4].strip() if row[4] else "",
                    "NAME1": row[5].strip() if row[5] else "",
                    "KDGRP": row[6].strip() if row[6] else "",
                    "BZIRK": row[7].strip() if row[7] else "",
                    "INCO1": row[8].strip() if row[8] else "",
                    "LPRIO": row[9] if row[9] else "",
                    "EIKTO": row[10].strip() if row[10] else "",
                    "VSBED": row[11].strip() if row[11] else "",
                    "KTGRD": row[12].strip() if row[12] else "",
                    "ZTERM": row[13].strip() if row[13] else "",
                    "VWERK": row[14].strip() if row[14] else "",
                    "VKGRP": row[15].strip() if row[15] else "",
                    "VKBUR": row[16].strip() if row[16] else "",
                    "AUFSD": row[17].strip() if row[17] else "",
                    "FAKSD": row[18].strip() if row[18] else "",
                    "LIFSD": row[19].strip() if row[19] else "",
                    "LOEVM": row[20].strip() if row[20] else "",
                    "SPERR": row[21].strip() if row[21] else "",
                    "COMPANY_ID": row[22] if row[22] else ""
                }
                sales_views.append(sales_view)
            
            return {
                "status": "success",
                "message": f"Found {len(sales_views)} sales view(s) for customer {customer_number}",
                "sales_views": sales_views
            }
            
        except Exception as e:
            logging.error(f"Error retrieving sales views for {customer_number}: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve sales views: {str(e)}",
                "sales_views": []
            }

    @staticmethod
    def get_customer_partner_functions(customer_number: str, vkorg: str = None, vtweg: str = None) -> Dict[str, any]:
        """
        Get customer partner functions from KNVP
        
        Args:
            customer_number (str): Customer number (KUNNR)
            vkorg (str, optional): Sales organization filter
            vtweg (str, optional): Distribution channel filter
            
        Returns:
            Dict with partner functions data or error message
        """
        try:
            # Build dynamic WHERE clause
            where_conditions = ["KUNNR = :customer_number"]
            params = {"customer_number": customer_number}
            
            if vkorg:
                where_conditions.append("VKORG = :vkorg")
                params["vkorg"] = vkorg
                
            if vtweg:
                where_conditions.append("VTWEG = :vtweg")
                params["vtweg"] = vtweg
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT 
                    KUNNR,               -- Customer Number
                    VKORG,               -- Sales Organization
                    VTWEG,               -- Distribution Channel
                    SPART,               -- Division
                    PARVW,               -- Partner Function
                    PARZA,               -- Partner Counter
                    KUNN2,               -- Partner Customer Number
                    COMPANY_ID           -- Company ID
                FROM KNVP
                WHERE {where_clause}
                ORDER BY VKORG, VTWEG, SPART, PARVW, PARZA
            """
            
            rows = DatabaseService.execute_query(
                query=query,
                params=params,
                fetch_all=True
            )
            
            if not rows:
                return {
                    "status": "success",
                    "message": f"No partner functions found for customer {customer_number}",
                    "partner_functions": []
                }
            
            partner_functions = []
            for row in rows:
                partner_function = {
                    "KUNNR": row[0].strip() if row[0] else "",
                    "VKORG": row[1].strip() if row[1] else "",
                    "VTWEG": row[2].strip() if row[2] else "",
                    "SPART": row[3].strip() if row[3] else "",
                    "PARVW": row[4].strip() if row[4] else "",
                    "PARZA": row[5] if row[5] else "",
                    "KUNN2": row[6].strip() if row[6] else "",
                    "COMPANY_ID": row[7] if row[7] else ""
                }
                partner_functions.append(partner_function)
            
            return {
                "status": "success",
                "message": f"Found {len(partner_functions)} partner function(s) for customer {customer_number}",
                "partner_functions": partner_functions
            }
            
        except Exception as e:
            logging.error(f"Error retrieving partner functions for {customer_number}: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve partner functions: {str(e)}",
                "partner_functions": []
            }

    @staticmethod
    def get_customer_complete_info(customer_number: str) -> Dict[str, any]:
        """
        Get complete customer information from all related tables
        
        Args:
            customer_number (str): Customer number (KUNNR)
            
        Returns:
            Dict with complete customer information
        """
        try:
            # Get main customer data
            main_result = CustomerService.get_customer_details(customer_number)
            if main_result["status"] == "error":
                return main_result
            
            # Get sales views
            sales_views_result = CustomerService.get_customer_sales_views(customer_number)
            
            # Get partner functions
            partner_functions_result = CustomerService.get_customer_partner_functions(customer_number)
            
            # Combine all data
            complete_info = {
                "status": "success",
                "message": f"Complete customer information retrieved for {customer_number}",
                "customer": main_result["customer"],
                "sales_views": sales_views_result.get("sales_views", []),
                "partner_functions": partner_functions_result.get("partner_functions", [])
            }
            
            logging.debug(f"Complete customer info retrieved for {customer_number}")
            
            return complete_info
            
        except Exception as e:
            logging.error(f"Error retrieving complete customer info for {customer_number}: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve complete customer information: {str(e)}",
                "customer": None,
                "sales_views": [],
                "partner_functions": []
            }

    @staticmethod
    def get_customer_specification() -> Dict[str, any]:
        """
        Get customer specification for FE form
        
        Returns:
            Dict with customer specification fields
        """
        try:
            specifications = [
                # GENERAL_DATA - Only M and O types (excluding F types)
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "NAME1",
                    "label": "Name-Surname",
                    "type": "CHAR",
                    "length": 35,
                    "inputType": "M",
                    "defaultValue": "EX.บจก. ธนวินท์ คอนสตรั๊คชั่น",
                    "layout": {"md": 12}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "CITY",
                    "label": "City",
                    "type": "CHAR",
                    "length": 40,
                    "inputType": "O",
                    "defaultValue": "EX.กรุงเทพมหานคร",
                    "layout": {"md": 6}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "DISTRICT",
                    "label": "District",
                    "type": "CHAR",
                    "length": 40,
                    "inputType": "O",
                    "defaultValue": "EX.เขตบางเขน",
                    "layout": {"md": 6}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "TAX3",
                    "label": "Tax Number",
                    "type": "CHAR",
                    "length": 16,
                    "inputType": "M",
                    "defaultValue": "EX. 9105545063268",
                    "layout": {"md": 6}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "TYPE_BUS",
                    "label": "Type of Business",
                    "type": "CHAR",
                    "length": 30,
                    "inputType": "O",
                    "defaultValue": "EX. 00000",
                    "layout": {"md": 4}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "POST_CODE",
                    "label": "Postal Code",
                    "type": "CHAR",
                    "length": 10,
                    "inputType": "O",
                    "defaultValue": "EX. 11000",
                    "layout": {"md": 4}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "STREET_NO",
                    "label": "Street Number for City/Street File",
                    "type": "CHAR",
                    "length": 12,
                    "inputType": "O",
                    "defaultValue": "EX.  89/506",
                    "layout": {"md": 12}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "LOCATION",
                    "label": "Street 5",
                    "type": "CHAR",
                    "length": 40,
                    "inputType": "O",
                    "defaultValue": "EX. แขวงท่าแร้ง",
                    "layout": {"md": 12}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "TEL1_NUMBR",
                    "label": "First telephone no.: dialling code+number",
                    "type": "CHAR",
                    "length": 30,
                    "inputType": "O",
                    "defaultValue": "EX.  22222222",
                    "layout": {"md": 10}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "CONTACT",
                    "label": "Name 1",
                    "type": "CHAR",
                    "length": 35,
                    "inputType": "O",
                    "defaultValue": "",
                    "layout": {"md": 12}
                },
                {
                    "group": "GENERAL_DATA",
                    "fieldName": "CRM_REF",
                    "label": "Address notes",
                    "type": "CHAR",
                    "length": 50,
                    "inputType": "O",
                    "defaultValue": "Crm No 123"
                },
                
                # SALE_DATA - Only M and O types (excluding F types)
                {
                    "group": "SALE_DATA",
                    "fieldName": "DIST_CHN",
                    "label": "Distribution Channel",
                    "type": "CHAR",
                    "length": 2,
                    "inputType": "M",
                    "defaultValue": "EX. 10",
                    "options": [
                        {"value": "10", "label": "ผู้รับเหมา"},
                        {"value": "20", "label": "ขายส่ง"},
                        {"value": "30", "label": "ขายปลีก (ขาจร)"},
                        {"value": "40", "label": "บริษัทในเครือ"},
                        {"value": "50", "label": "ต่างประเทศ"}
                    ]
                },
                {
                    "group": "SALE_DATA",
                    "fieldName": "CUST_GROUP",
                    "label": "Customer group",
                    "type": "CHAR",
                    "length": 2,
                    "inputType": "M",
                    "defaultValue": "EX. 1",
                    "options": [
                        {"value": "01", "label": "ผู้รับเหมา"},
                        {"value": "02", "label": "เจ้าของงาน"},
                        {"value": "03", "label": "นายหน้า/ขายส่ง"},
                        {"value": "04", "label": "ลูกค้าคู่แข่ง"},
                        {"value": "05", "label": "High Risk"},
                        {"value": "06", "label": "บุคคลทั่วไป"}
                    ]
                },
                {
                    "group": "SALE_DATA",
                    "fieldName": "SALE_DIST",
                    "label": "Sales district",
                    "type": "CHAR",
                    "length": 6,
                    "inputType": "M",
                    "defaultValue": "EX. 120000",
                    "layout": {"md": 12},
                    "options": [
                        {"value": "110000", "label": "Bangkok"},
                        {"value": "120000", "label": "Central"},
                        {"value": "130000", "label": "Northern"},
                        {"value": "140000", "label": "North Eastern"},
                        {"value": "150000", "label": "Southern"},
                        {"value": "160000", "label": "Eastern"},
                        {"value": "170000", "label": "Western"},
                        {"value": "210000", "label": "Asia"},
                        {"value": "220000", "label": "Europe"},
                        {"value": "230000", "label": "North America"},
                        {"value": "240000", "label": "South America"},
                        {"value": "250000", "label": "Middle East"},
                        {"value": "260000", "label": "Africa"},
                        {"value": "270000", "label": "Australia"}
                    ]
                },
                {
                    "group": "SALE_DATA",
                    "fieldName": "DEL_PIOR",
                    "label": "Delivery Priority",
                    "type": "NUMC",
                    "length": 2,
                    "inputType": "O",
                    "defaultValue": "EX.7",
                    "layout": {"md": 12},
                    "options": [
                        {"value": "01", "label": "คอนโด Low rise"},
                        {"value": "02", "label": "คอนโด Hight rise"},
                        {"value": "03", "label": "Mega Project"},
                        {"value": "04", "label": "ราชการ / อาคารทั่วไป"},
                        {"value": "05", "label": "ราชการ / อาคารขนาดใหญ่"},
                        {"value": "06", "label": "ราชการ / อาคารขนาดใหญ่"},
                        {"value": "07", "label": "ราชการ / โรงพยาบาล"},
                        {"value": "08", "label": "ราชการ / สถานศึกษา"},
                        {"value": "09", "label": "เอกชน / อาคารทั่วไป"},
                        {"value": "10", "label": "เอกชน / อาคารขนาดใหญ่"},
                        {"value": "11", "label": "เอกชน / อาคารขนาดใหญ่"},
                        {"value": "12", "label": "เอกชน / โรงพยาบาล"},
                        {"value": "13", "label": "เอกชน / สถานศึกษา"},
                        {"value": "14", "label": "โรงงาน / โกดัง"},
                        {"value": "15", "label": "งานถนน / สะพาน"},
                        {"value": "16", "label": "งานเขื่อน"},
                        {"value": "17", "label": "งานบ้าน"},
                        {"value": "18", "label": "ห้างสรรพสินค้า"},
                        {"value": "19", "label": "โรงไฟฟ้า"},
                        {"value": "20", "label": "งานระบบ"},
                        {"value": "21", "label": "ตกแต่ง / ต่อเติม"},
                        {"value": "22", "label": "อื่นๆ"},
                        {"value": "23", "label": "ขายส่ง"},
                        {"value": "24", "label": "โมเดิร์นเทรด"},
                        {"value": "25", "label": "เทรดเดอร์"},
                        {"value": "26", "label": "โรงแรม / รีสอร์ท"}
                    ]
                },
                {
                    "group": "SALE_DATA",
                    "fieldName": "CUST_STS_GROUP",
                    "label": "Customer Statistics Group",
                    "type": "CHAR",
                    "length": 1,
                    "inputType": "M",
                    "defaultValue": "EX. 01",
                    "layout": {"md": 12},
                    "options": [
                        {"value": "01", "label": "ผู้รับเหมา"},
                        {"value": "02", "label": "เจ้าของงาน"},
                        {"value": "03", "label": "นายหน้า/ขายส่ง"},
                        {"value": "04", "label": "ลูกค้าคู่แข่ง"},
                        {"value": "05", "label": "High Risk"},
                        {"value": "06", "label": "บุคคลทั่วไป"}
                    ]
                }
            ]
            
            return {
                "status": "success",
                "message": "Customer specification retrieved successfully",
                "specifications": specifications
            }
            
        except Exception as e:
            logging.error(f"Error getting customer specification: {e}")
            return {
                "status": "error",
                "message": f"Failed to get customer specification: {str(e)}",
                "specifications": []
            }

    @staticmethod
    def create_customer(general_data: dict, sale_data: dict) -> Dict[str, any]:
        """
        Create new customer with provided data
        
        Args:
            general_data (dict): General customer data
            sale_data (dict): Sales organization data
            
        Returns:
            Dict with creation result and generated customer number
        """
        try:
            # This would typically call SAP RFC to create customer
            # For now, we'll simulate the process
            
            # Generate customer number (in real implementation, this would come from SAP)
            import random
            customer_number = f"C{random.randint(1000000, 9999999)}"
            
            # Validate required fields
            required_general = ['NAME1', 'TAX3']
            required_sale = ['DIST_CHN', 'CUST_GROUP', 'SALE_DIST', 'CUST_STS_GROUP']
            
            for field in required_general:
                if not general_data.get(field):
                    return {
                        "status": "error",
                        "message": f"Required field missing: {field}",
                        "customer_number": None
                    }
            
            for field in required_sale:
                if not sale_data.get(field):
                    return {
                        "status": "error",
                        "message": f"Required field missing: {field}",
                        "customer_number": None
                    }
            
            # Prepare data for SAP call (with fixed values)
            customer_data = {
                # General Data with fixed values
                "GENERAL_DATA": {
                    **general_data,
                    "ACC_GROUP": "Z001",  # Fixed
                    "VAT_REG": general_data.get("TAX3", "") + ".00000",  # Fixed: TAX3+.00000
                    "COUNTRY": "TH",  # Fixed
                    "LANGU": "EN"  # Fixed
                },
                
                # Company Data (all fixed)
                "COMPANY_DATA": {
                    "COMPANY": "1000",
                    "SORT_KEY": "031",
                    "RECON_ACC": "110000",
                    "TERM": "T000",
                    "DUNN_PROC": "Z100",
                    "DUNN_CERK": "01"
                },
                
                # Sale Data with fixed values
                "SALE_DATA": {
                    **sale_data,
                    "SALE_OROG": "1000",  # Fixed
                    "DIVISION": "00",  # Fixed
                    "INCO1": "DOM",  # Fixed
                    "MAX_PARIAL": "9",  # Fixed
                    "SHIP_COND": "01",  # Fixed
                    "CURRENCY": "THB",  # Fixed
                    "ACC_ASS_GROUP": "01",  # Fixed
                    "TERM": "T000",  # Fixed
                    "SALE_GRP": "xxx",  # Fixed
                    "SALE_OFF": "FS GO GO",  # Fixed
                    "CUST_GROUP1": "01",  # Fixed
                    "POD_FLAG": "X"  # Fixed
                }
            }
            
            # Log the customer creation request
            logging.info(f"Creating customer with data: {customer_data}")
            
            # Here you would call SAP RFC function to create customer
            # sap_response = SAPService.call_function("CUSTOMER_CREATE", customer_data)
            
            # Simulate successful creation
            sap_response = {
                "status": "success",
                "customer_number": customer_number,
                "message": "Customer created successfully"
            }
            
            logging.info(f"Customer created successfully: {customer_number}")
            
            return {
                "status": "success",
                "message": f"Customer {customer_number} created successfully",
                "customer_number": customer_number,
                "sap_response": sap_response
            }
            
        except Exception as e:
            logging.error(f"Error creating customer: {e}")
            return {
                "status": "error",
                "message": f"Failed to create customer: {str(e)}",
                "customer_number": None,
                "sap_response": None
            }
    
    @staticmethod
    def lookup_customers(
        name: Optional[str] = None,
        phone: Optional[str] = None,
        tax_id: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, any]:
        """
        Quick customer lookup by name, phone, or tax ID
        Optimized for customer selection during data entry
        
        Args:
            name (str, optional): Customer name (NAME1, NAME2)
            phone (str, optional): Phone number (TELF1)
            tax_id (str, optional): Tax ID (STCD3)
            limit (int): Maximum number of results
            
        Returns:
            Dict with status, message, total_records, and customers list
        """
        try:
            # Build dynamic WHERE clause
            where_conditions = ["1=1"]  # Base condition
            params = {}
            
            if name:
                where_conditions.append(
                    "(UPPER(KNA1.NAME1) LIKE UPPER(:name) OR UPPER(KNA1.NAME2) LIKE UPPER(:name))"
                )
                params["name"] = f"%{name}%"
            
            if phone:
                # Normalize phone: remove all non-digits from input and DB
                search_phone = re.sub(r'\D', '', phone)
                where_conditions.append(
                    "REGEXP_REPLACE(TRIM(KNA1.TELF1), '[^0-9]', '') LIKE :phone"
                )
                params["phone"] = f"{search_phone}%"  # match เฉพาะขึ้นต้นด้วยเลขที่ค้นหา
            
            if tax_id:
                where_conditions.append("KNA1.STCD3 LIKE :tax_id")
                params["tax_id"] = f"%{tax_id}%"
            
            where_clause = " AND ".join(where_conditions)

            # Optimized query for quick lookup (JOIN KNVV)
            query = f"""
                SELECT 
                KNA1.KUNNR,           -- Customer Number
                KNA1.NAME1,           -- Customer Name 1
                KNA1.NAME2,           -- Customer Name 2
                KNA1.ORT01,           -- City
                KNA1.STRAS,           -- Street Address
                KNA1.TELF1,           -- Telephone
                KNA1.STCD3,           -- Tax Number
                KNA1.LAND1,           -- Country
                KNA1.PSTLZ,           -- Postal Code
                NVL(KNVV.VKORG, '') as VKORG,    -- Sales Organization
                NVL(KNVV.VTWEG, '') as VTWEG,    -- Distribution Channel
                NVL(KNVV.BZIRK, '') as BZIRK,    -- Sales District
                NVL(KNVV.VKGRP, '') as VKGRP,    -- Sales Group
                NVL(KNVV.VKBUR, '') as VKBUR,    -- Sales Office
                KNVP.SPART,    -- <<== SPART from KNVP (Ship-to Party)
                NVL(KNVV.ZTERM, '') as ZTERM     -- Payment Terms
            FROM KNA1
            LEFT JOIN KNVV ON KNA1.KUNNR = KNVV.KUNNR
            LEFT JOIN KNVP ON KNA1.KUNNR = KNVP.KUNNR AND PARVW = 'WE' AND PARZA = 0
            WHERE {where_clause}
            AND ROWNUM <= :limit
            ORDER BY KNA1.NAME1, KNA1.KUNNR
            """
            
            params["limit"] = limit
            
            rows = DatabaseService.execute_query(
                query=query,
                params=params,
                fetch_all=True
            )
            
            customers = []
            for row in rows:
                customer = {
                    "KUNNR": row[0].strip() if row[0] else "",
                    "NAME1": row[1].strip() if row[1] else "",
                    "NAME2": row[2].strip() if row[2] else "",
                    "ORT01": row[3].strip() if row[3] else "",
                    "STRAS": row[4].strip() if row[4] else "",
                    "TELF1": row[5].strip() if row[5] else "",
                    "STCD3": row[6].strip() if row[6] else "",
                    "LAND1": row[7].strip() if row[7] else "",
                    "PSTLZ": row[8].strip() if row[8] else "",
                    "VKORG": row[9].strip() if row[9] else "",
                    "VTWEG": row[10].strip() if row[10] else "",
                    "BZIRK": row[11].strip() if row[11] else "",
                    "VKGRP": row[12].strip() if row[12] else "",
                    "VKBUR": row[13].strip() if row[13] else "",
                    "SPART": row[14].strip() if row[14] else "",
                    "ZTERM": row[15].strip() if row[15] else ""
                }
                customers.append(customer)
            
            total_records = len(customers)
            search_criteria = []
            if name:
                search_criteria.append(f"name: {name}")
            if phone:
                search_criteria.append(f"phone: {phone}")
            if tax_id:
                search_criteria.append(f"tax_id: {tax_id}")
            
            message = f"Found {total_records} customer(s) matching {', '.join(search_criteria)}"
            
            logging.debug(f"Customer lookup completed: {total_records} records found")
            
            return {
                "status": "success",
                "message": message,
                "total_records": total_records,
                "customers": customers
            }
            
        except Exception as e:
            logging.error(f"Error in customer lookup: {e}")
            return {
                "status": "error",
                "message": f"Customer lookup failed: {str(e)}",
                "total_records": 0,
                "customers": []
            }
