"""
Database Service - Centralized Database Connection Management
Provides centralized Oracle database connection with context manager for auto-cleanup
Enhanced with connection pooling for better performance
"""
import cx_Oracle
from contextlib import contextmanager
from threading import Lock
from typing import Optional
from app.config import Config


class DatabaseConnectionPool:
    """
    Oracle Database Connection Pool Manager
    Implements connection pooling for better performance and resource management
    """
    
    _instance = None
    _lock = Lock()
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """
        Initialize Oracle connection pool
        """
        try:
            # Connection pool parameters
            min_connections = 2
            max_connections = 10
            increment = 1
            
            self._pool = cx_Oracle.SessionPool(
                user=Config.ORACLE_USER,
                password=Config.ORACLE_PASSWORD,
                dsn=Config.ORACLE_DSN,
                min=min_connections,
                max=max_connections,
                increment=increment,
                encoding=Config.ORACLE_CHARSET,
                threaded=True,
                getmode=cx_Oracle.SPOOL_ATTRVAL_WAIT,
                timeout=300,  # 5 minutes timeout
                wait_timeout=5000,  # 5 seconds wait timeout
                max_lifetime_session=3600  # 1 hour max session lifetime
            )
            
        except Exception as e:
            raise RuntimeError(f"Connection pool initialization failed: {str(e)}")
    
    def get_connection(self):
        """
        Get connection from pool
        """
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            connection = self._pool.acquire()
            return connection
        except Exception as e:
            raise RuntimeError(f"Failed to get database connection: {str(e)}")
    
    def return_connection(self, connection):
        """
        Return connection to pool
        """
        if connection and self._pool:
            try:
                self._pool.release(connection)
            except Exception as e:
                pass
    
    def close_pool(self):
        """
        Close connection pool
        """
        if self._pool:
            try:
                self._pool.close()
                self._pool = None
            except Exception as e:
                pass
    
    def get_pool_status(self):
        """
        Get connection pool status information
        """
        if self._pool:
            return {
                "opened": self._pool.opened,
                "busy": self._pool.busy,
                "max": self._pool.max,
                "min": self._pool.min,
                "increment": self._pool.increment,
                "timeout": self._pool.timeout
            }
        return None


class DatabaseService:
    """
    Enhanced database service with connection pooling
    Implements connection management with context manager pattern and pooling
    """
    
    _pool_manager = None
    
    @classmethod
    def initialize(cls):
        """
        Initialize database service with connection pool
        """
        if cls._pool_manager is None:
            cls._pool_manager = DatabaseConnectionPool()
    
    @classmethod
    def get_connection(cls):
        """
        Get database connection from pool
        Returns: cx_Oracle.Connection
        """
        if cls._pool_manager is None:
            cls.initialize()
        
        try:
            connection = cls._pool_manager.get_connection()
            return connection
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {str(e)}")

    @classmethod
    @contextmanager
    def get_db_connection(cls):
        """
        Context manager for database connections with auto-cleanup and pooling
        Usage:
            with DatabaseService.get_db_connection() as conn:
                cursor = conn.cursor()
                # do database operations
        """
        connection = None
        try:
            connection = cls.get_connection()
            yield connection
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
        finally:
            if connection and cls._pool_manager:
                cls._pool_manager.return_connection(connection)

    @classmethod
    def execute_query(cls, query: str, params: dict = None, fetch_one: bool = False, fetch_all: bool = True):
        """
        Execute database query with automatic connection management and pooling
        
        Args:
            query (str): SQL query to execute
            params (dict): Query parameters
            fetch_one (bool): Fetch single row
            fetch_all (bool): Fetch all rows
            
        Returns:
            Query results or None
        """
        with cls.get_db_connection() as connection:
            cursor = connection.cursor()
            try:
                if params:
                    cursor.execute(query, **params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    connection.commit()
                    return cursor.rowcount
                    
            except Exception as e:
                raise
            finally:
                cursor.close()

    @classmethod
    def test_connection(cls):
        """
        Test database connection and pool status
        Returns: Dict with connection status and pool information
        """
        try:
            with cls.get_db_connection() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                cursor.close()
                
                pool_status = cls._pool_manager.get_pool_status() if cls._pool_manager else None
                
                return {
                    "connection_test": True,
                    "pool_status": pool_status,
                    "message": "Database connection and pool working correctly"
                }
        except Exception as e:
            return {
                "connection_test": False,
                "pool_status": None,
                "error": str(e)
            }
    
    @classmethod
    def shutdown(cls):
        """
        Shutdown database service and close connection pool
        """
        if cls._pool_manager:
            cls._pool_manager.close_pool()
            cls._pool_manager = None


# Initialize database service on module import
DatabaseService.initialize()
