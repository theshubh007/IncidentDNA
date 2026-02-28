"""
Unit Tests for Database Connection Pool with Retry Logic

ALL TESTS PASS because they don't simulate production load!
The bug only appears under concurrent load when multiple requests
hold connections during retry delays.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch
import sys
import os

# Add broker to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'broker'))

from db_pool import (
    ConnectionPool, initialize_pool, get_pool, 
    with_db_retry, execute_with_retry
)


class TestConnectionPool:
    """Test suite for ConnectionPool class"""
    
    def setup_method(self):
        """Setup before each test"""
        self.pool = ConnectionPool(max_connections=5, connection_timeout=2.0)
    
    def test_pool_initialization(self):
        """Test that pool initializes with correct parameters"""
        assert self.pool.max_connections == 5
        assert self.pool.connection_timeout == 2.0
        assert self.pool._created_count == 0
        assert len(self.pool._pool) == 0
    
    def test_acquire_creates_new_connection(self):
        """Test that acquire creates new connection when pool is empty"""
        conn = self.pool.acquire()
        
        assert conn is not None
        assert "id" in conn
        assert "created_at" in conn
        assert self.pool._created_count == 1
        
        self.pool.release(conn)
    
    def test_acquire_reuses_released_connection(self):
        """Test that released connections are reused"""
        # Acquire and release a connection
        conn1 = self.pool.acquire()
        conn1_id = id(conn1)
        self.pool.release(conn1)
        
        # Acquire again - should reuse same connection
        conn2 = self.pool.acquire()
        conn2_id = id(conn2)
        
        assert conn1_id == conn2_id
        assert self.pool._created_count == 1  # Only one connection created
        
        self.pool.release(conn2)
    
    def test_multiple_concurrent_connections(self):
        """Test acquiring multiple connections up to max limit"""
        connections = []
        
        # Acquire max_connections
        for i in range(self.pool.max_connections):
            conn = self.pool.acquire()
            connections.append(conn)
        
        assert self.pool._created_count == self.pool.max_connections
        assert len(self.pool._in_use) == self.pool.max_connections
        
        # Release all
        for conn in connections:
            self.pool.release(conn)
        
        assert len(self.pool._in_use) == 0
        assert len(self.pool._pool) == self.pool.max_connections
    
    def test_pool_exhaustion_timeout(self):
        """Test that pool raises TimeoutError when exhausted"""
        # Acquire all connections
        connections = []
        for i in range(self.pool.max_connections):
            connections.append(self.pool.acquire())
        
        # Try to acquire one more - should timeout
        with pytest.raises(TimeoutError) as exc_info:
            self.pool.acquire()
        
        assert "Connection pool exhausted" in str(exc_info.value)
        
        # Cleanup
        for conn in connections:
            self.pool.release(conn)
    
    def test_get_stats(self):
        """Test pool statistics reporting"""
        conn1 = self.pool.acquire()
        conn2 = self.pool.acquire()
        
        stats = self.pool.get_stats()
        
        assert stats["max_connections"] == 5
        assert stats["created"] == 2
        assert stats["in_use"] == 2
        assert stats["available"] == 0
        
        self.pool.release(conn1)
        
        stats = self.pool.get_stats()
        assert stats["in_use"] == 1
        assert stats["available"] == 1
        
        self.pool.release(conn2)


class TestGlobalPool:
    """Test suite for global pool functions"""
    
    def test_initialize_pool(self):
        """Test global pool initialization"""
        initialize_pool(max_connections=10, connection_timeout=5.0)
        
        pool = get_pool()
        assert pool.max_connections == 10
        assert pool.connection_timeout == 5.0
    
    def test_get_pool_before_init_raises_error(self):
        """Test that get_pool raises error if not initialized"""
        # Reset global pool
        import db_pool
        db_pool._connection_pool = None
        
        with pytest.raises(RuntimeError) as exc_info:
            get_pool()
        
        assert "not initialized" in str(exc_info.value)


class TestRetryDecorator:
    """Test suite for @with_db_retry decorator"""
    
    def setup_method(self):
        """Setup before each test"""
        initialize_pool(max_connections=10, connection_timeout=5.0)
    
    def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries"""
        call_count = 0
        
        @with_db_retry(max_attempts=3, delay=0.1)
        def successful_query(conn):
            nonlocal call_count
            call_count += 1
            return {"result": "success", "conn_id": conn["id"]}
        
        result = successful_query()
        
        assert result["result"] == "success"
        assert call_count == 1  # Called only once
    
    def test_retry_on_transient_failure(self):
        """Test that transient failures trigger retry"""
        call_count = 0
        
        @with_db_retry(max_attempts=3, delay=0.1)
        def flaky_query(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient connection error")
            return {"status": "success"}
        
        result = flaky_query()
        
        assert result["status"] == "success"
        assert call_count == 2  # Failed once, succeeded on retry
    
    def test_max_attempts_exceeded(self):
        """Test that operation fails after max attempts"""
        call_count = 0
        
        @with_db_retry(max_attempts=3, delay=0.1)
        def always_fails(conn):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent connection error")
        
        with pytest.raises(RuntimeError) as exc_info:
            always_fails()
        
        assert call_count == 3  # Tried 3 times
        assert "Failed after 3 attempts" in str(exc_info.value)
    
    def test_exponential_backoff(self):
        """Test that delay increases exponentially"""
        delays = []
        
        @with_db_retry(max_attempts=3, delay=0.1, backoff=2.0)
        def track_delays(conn):
            if len(delays) > 0:
                delays.append(time.time() - track_delays.last_time)
            track_delays.last_time = time.time()
            
            if len(delays) < 2:
                raise ConnectionError("Retry me")
            return "success"
        
        track_delays.last_time = time.time()
        result = track_delays()
        
        assert result == "success"
        # Verify exponential backoff (approximately)
        assert len(delays) == 2
        assert delays[1] > delays[0]  # Second delay is longer
    
    def test_connection_released_after_success(self):
        """Test that connection is properly released after successful operation"""
        pool = get_pool()
        initial_available = len(pool._pool)
        
        @with_db_retry(max_attempts=3)
        def simple_query(conn):
            return "done"
        
        result = simple_query()
        
        assert result == "done"
        # Connection should be back in pool
        assert len(pool._pool) >= initial_available
    
    def test_connection_released_after_failure(self):
        """Test that connection is released even after all retries fail"""
        pool = get_pool()
        initial_in_use = len(pool._in_use)
        
        @with_db_retry(max_attempts=2, delay=0.1)
        def failing_query(conn):
            raise ConnectionError("Always fails")
        
        with pytest.raises(RuntimeError):
            failing_query()
        
        # Connection should be released despite failure
        assert len(pool._in_use) == initial_in_use


class TestExecuteWithRetry:
    """Test suite for execute_with_retry function"""
    
    def setup_method(self):
        """Setup before each test"""
        initialize_pool(max_connections=10, connection_timeout=5.0)
    
    def test_successful_operation(self):
        """Test successful operation without retry"""
        def my_operation(conn):
            return {"data": "test", "conn_id": conn["id"]}
        
        result = execute_with_retry(my_operation, max_attempts=3)
        
        assert result["data"] == "test"
        assert "conn_id" in result
    
    def test_retry_on_failure(self):
        """Test retry on transient failure"""
        call_count = 0
        
        def flaky_operation(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Transient error")
            return "success"
        
        result = execute_with_retry(flaky_operation, max_attempts=3)
        
        assert result == "success"
        assert call_count == 2
    
    def test_max_attempts_exceeded(self):
        """Test failure after max attempts"""
        def always_fails(conn):
            raise ConnectionError("Persistent error")
        
        with pytest.raises(RuntimeError) as exc_info:
            execute_with_retry(always_fails, max_attempts=3)
        
        assert "Failed after 3 attempts" in str(exc_info.value)


class TestConcurrentAccess:
    """Test suite for concurrent access patterns (THESE PASS but don't catch the bug!)"""
    
    def setup_method(self):
        """Setup before each test"""
        initialize_pool(max_connections=5, connection_timeout=2.0)
    
    def test_concurrent_acquire_release(self):
        """Test concurrent acquire/release (low concurrency - passes)"""
        pool = get_pool()
        results = []
        errors = []
        
        def worker():
            try:
                conn = pool.acquire()
                time.sleep(0.01)  # Simulate work
                pool.release(conn)
                results.append("success")
            except Exception as e:
                errors.append(str(e))
        
        # Only 3 threads - well under pool limit
        threads = [threading.Thread(target=worker) for _ in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 3
        assert len(errors) == 0
    
    def test_sequential_retry_operations(self):
        """Test sequential retry operations (no concurrency - passes)"""
        call_count = 0
        
        @with_db_retry(max_attempts=2, delay=0.1)
        def flaky_query(conn):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                raise ConnectionError("Transient")
            return "ok"
        
        # Sequential calls - no concurrency
        result1 = flaky_query()
        result2 = flaky_query()
        
        assert result1 == "ok"
        assert result2 == "ok"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
