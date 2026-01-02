"""
Database Connection Pool for Performance Optimization
Reuses connections instead of creating new ones for each request
"""

import sqlite3
from contextlib import contextmanager
from queue import Queue, Empty
import threading
from typing import Optional
import time


class ConnectionPool:
    """
    Thread-safe connection pool for SQLite.
    Dramatically improves performance by reusing connections.
    """
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 5.0):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections to maintain
            timeout: Timeout in seconds for getting connection from pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._all_connections = set()
        
        # Pre-create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
            self._all_connections.add(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON;")  # Read-only for safety
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
        conn.execute("PRAGMA temp_store = MEMORY;")  # Use memory for temp tables
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        Automatically returns it to pool when done.
        """
        conn = None
        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(timeout=self.timeout)
            except Empty:
                # Pool exhausted, create temporary connection
                print(f"⚠️ Connection pool exhausted, creating temporary connection")
                conn = self._create_connection()
            
            yield conn
            
        finally:
            if conn:
                # Return connection to pool if it's from the pool
                if conn in self._all_connections:
                    self._pool.put(conn)
                else:
                    # Close temporary connections
                    conn.close()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break
            self._all_connections.clear()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close_all()


class PostgresConnectionPool:
    """
    Connection pool for PostgreSQL databases.
    """
    
    def __init__(self, host: str, port: int, database: str, 
                 user: str, password: str, pool_size: int = 10):
        """Initialize PostgreSQL connection pool."""
        try:
            import psycopg2
            from psycopg2 import pool
            
            self.pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=pool_size,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                options='-c default_transaction_read_only=on'
            )
        except ImportError:
            raise RuntimeError("psycopg2 not installed. Install with: pip install psycopg2-binary")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def close_all(self):
        """Close all connections."""
        self.pool.closeall()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_connection_pool(db_type: str = "sqlite", pool_size: int = 10, **kwargs):
    """
    Create appropriate connection pool based on database type.
    
    Args:
        db_type: 'sqlite' or 'postgres'
        pool_size: Maximum number of connections
        **kwargs: Database-specific parameters
    
    Returns:
        ConnectionPool instance
    """
    if db_type == "sqlite":
        db_path = kwargs.get('db_path', 'sample.db')
        return ConnectionPool(db_path, pool_size=pool_size)
    elif db_type == "postgres":
        return PostgresConnectionPool(
            host=kwargs.get('host', 'localhost'),
            port=kwargs.get('port', 5432),
            database=kwargs['database'],
            user=kwargs['user'],
            password=kwargs['password'],
            pool_size=pool_size
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
