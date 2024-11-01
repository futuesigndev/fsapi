import cx_Oracle
from app.config import Config

def connect_to_oracle():
    connection = cx_Oracle.connect(
        user=Config.ORACLE_USER,
        password=Config.ORACLE_PASSWORD,
        dsn=Config.ORACLE_DSN,
        encoding=Config.ORACLE_CHARSET
    )
    return connection
