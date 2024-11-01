import os
from dotenv import load_dotenv

load_dotenv()  # โหลดตัวแปรจาก .env

class Config:
    # SAP Configuration
    SAP_USER = os.getenv("SAP_USER")
    SAP_PASSWORD = os.getenv("SAP_PASSWORD")
    SAP_HOST = os.getenv("SAP_HOST")
    SAP_SYSNR = os.getenv("SAP_SYSNR")
    SAP_CLIENT = os.getenv("SAP_CLIENT")
    SAP_LANG = os.getenv("SAP_LANG")
    SAP_CODEPAGE = os.getenv("SAP_CODEPAGE")

    # Oracle Configuration
    ORACLE_USER = os.getenv("ORACLE_USER")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
    ORACLE_DSN = os.getenv("ORACLE_DSN")
    ORACLE_CHARSET = os.getenv("ORACLE_CHARSET")
