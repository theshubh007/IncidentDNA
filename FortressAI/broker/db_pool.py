# DEPLOYED: 2026-03-01 00:47:07 UTC | DPL-20241129-0042
"""
Database Connection Pool with Retry Logic
Improves resilience for logging and audit trail storage
"""
import time
import logging
from typing import Optional, Any, Callable
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class ConnectionPool:
    """
    Simple connection pool for database operations
    Manages a pool of reusable connections to reduce overhead
    """

    def __init__(self, max_connections: int = 20, connection_timeout: float = 30.0):
        """
        Initialize connection pool

        Args:
            max_connections: Maximum number of connections in pool
            connection_timeout: Timeout for acquiring connection (seconds)
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self._pool = []
        self._in_use = set()
        self._lock = threading.Lock()
        self._created_count = 0

        logger.info(f"Connection pool initialized: max={max_connections}, timeout={connection_timeout}s")

    def acquire(self) -> dict:
        """
        Acquire a connection from the pool

        Returns:
            Connection object (mock dict for demo)

        Raises:
            TimeoutError: If no connection available within timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                # Try to reuse existing connection
                if self._pool:
                    conn = self._pool.pop()
                    self._in_use.add(id(conn))
                    logger.debug(f"Reused connection from pool (pool_size={len(self._pool)})")
                    return conn

                # Create new connection if under limit
                if self._created_count < self.max_connections:
                    conn = self._create_connection()
                    self._in_use.add(id(conn))
                    self._created_count += 1
                    logger.debug(f"Created new connection (total={self._created_count}/{self.max_connections})")
                    return conn

            # Pool exhausted, wait and retry
            elapsed = time.time() - start_time
            if elapsed >= self.connection_timeout:
                raise TimeoutError(
                    f"Connection pool exhausted: {self._created_count} connections in use, "
                    f"waited {elapsed:.2f}s"
                )

            logger.warning(
                f"Connection pool exhausted, waiting... "
                f"(in_use={len(self._in_use)}, pool={len(self._pool)})"
            )
            time.sleep(0.1)  # Wait before retry

    def release(self, conn: dict):
        """
        Release a connection back to the pool

        Args:
            conn: Connection to release
        """
        with self._lock:
            conn_id = id(conn)
            if conn_id in self._in_use:
                self._in_use.remove(conn_id)
                self._pool.append(conn)
                logger.debug(f"Released connection to pool (pool_size={len(self._pool)})")
            else:
                logger.warning("Attempted to release unknown connection")

    def _create_connection(self) -> dict:
        """
        Create a new database connection (mock implementation)

        Returns:
            Connection object
        """
        # Mock connection - in real implementation, this would be a DB connection
        return {
            "id": self._created_count + 1,
            "created_at": time.time(),
            "queries_executed": 0
        }

    def get_stats(self) -> dict:
        """Get pool statistics"""
        with self._lock:
            return {
                "max_connections": self.max_connections,
                "created": self._created_count,
                "in_use": len(self._in_use),
                "available": len(self._pool)
            }


# Global connection pool instance
_connection_pool: Optional[ConnectionPool] = None


def initialize_pool(max_connections: int = 20, connection_timeout: float = 30.0):
    """
    Initialize the global connection pool

    Args:
        max_connections: Maximum number of connections
        connection_timeout: Timeout for acquiring connection
    """
    global _connection_pool
    _connection_pool = ConnectionPool(max_connections, connection_timeout)
    logger.info("Global connection pool initialized")


def get_pool() -> ConnectionPool:
    """
    Get the global connection pool instance

    Returns:
        ConnectionPool instance

    Raises:
        RuntimeError: If pool not initialized
    """
    if _connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call initialize_pool() first.")
    return _connection_pool


def with_db_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry database operations on transient failures

    THE PROBLEM: This holds connections during retry delays, causing pool exhaustion!

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each attempt

    Example:
        @with_db_retry(max_attempts=3)
        def save_log_entry(data):
            conn = get_pool().acquire()
            try:
                # ... database operation ...
                return result
            finally:
                get_pool().release(conn)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            current_delay = delay
            last_exception = None

            # Acquire connection ONCE (this is the problem!)
            pool = get_pool()
            conn = pool.acquire()

            try:
                while attempt < max_attempts:
                    try:
                        # Pass connection to function
                        result = func(conn, *args, **kwargs)

                        if attempt > 0:
                            logger.info(
                                f"DB operation succeeded on attempt {attempt + 1}/{max_attempts}: "
                                f"{func.__name__}"
                            )

                        return result

                    except Exception as e:
                        attempt += 1
                        last_exception = e

                        if attempt >= max_attempts:
                            logger.error(
                                f"DB operation failed after {max_attempts} attempts: {func.__name__}",
                                exc_info=True
                            )
                            raise RuntimeError(
                                f"Failed after {max_attempts} attempts: {str(e)}"
                            ) from e

                        logger.warning(
                            f"DB operation failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {current_delay}s: {func.__name__} - {str(e)}"
                        )

                        # THE BUG: Sleep while holding connection!
                        # This prevents other requests from using this connection
                        time.sleep(current_delay)
                        current_delay *= backoff

                raise RuntimeError("Unexpected retry loop exit") from last_exception

            finally:
                # Release connection after all retries
                pool.release(conn)

        return wrapper
    return decorator


def execute_with_retry(operation: Callable, max_attempts: int = 3) -> Any:
    """
    Execute a database operation with retry logic (non-decorator version)

    THE PROBLEM: Same issue - holds connection during retries!

    Args:
        operation: Callable that takes a connection and performs DB operation
        max_attempts: Maximum retry attempts

    Returns:
        Result of the operation

    Example:
        def my_query(conn):
            # ... use conn ...
            return result

        result = execute_with_retry(my_query, max_attempts=3)
    """
    pool = get_pool()
    conn = pool.acquire()

    attempt = 0
    delay = 1.0

    try:
        while attempt < max_attempts:
            try:
                result = operation(conn)
                return result
            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    raise RuntimeError(f"Failed after {max_attempts} attempts: {str(e)}") from e

                logger.warning(f"Operation failed, retrying in {delay}s...")
                time.sleep(delay)  # BUG: Holding connection during sleep!
                delay *= 2.0

        raise RuntimeError("Unexpected retry loop exit")
    finally:
        pool.release(conn)
