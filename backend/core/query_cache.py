"""
LRU Cache for Query Results
Caches SQL query results to avoid redundant database hits
"""

from functools import lru_cache
from typing import List, Dict, Any, Tuple, Optional
import hashlib
import json
import time
from collections import OrderedDict
import threading


class QueryCache:
    """
    Thread-safe LRU cache for SQL query results.
    Dramatically improves performance for repeated queries.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        Initialize query cache.
        
        Args:
            max_size: Maximum number of cached queries
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, sql: str, db_identifier: str = "default") -> str:
        """
        Create cache key from SQL query.
        
        Args:
            sql: SQL query string
            db_identifier: Database identifier (for multi-database support)
        
        Returns:
            Cache key (hash of normalized SQL)
        """
        # Normalize SQL (lowercase, remove extra whitespace)
        normalized = " ".join(sql.lower().split())
        key_str = f"{db_identifier}:{normalized}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, sql: str, db_identifier: str = "default") -> Optional[Tuple[List[Dict], float]]:
        """
        Get cached result for SQL query.
        
        Args:
            sql: SQL query string
            db_identifier: Database identifier
        
        Returns:
            (results, timestamp) if cached and not expired, None otherwise
        """
        with self._lock:
            key = self._make_key(sql, db_identifier)
            
            if key not in self._cache:
                self._misses += 1
                return None
            
            results, timestamp = self._cache[key]
            
            # Check if expired
            if time.time() - timestamp > self.ttl_seconds:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return results, timestamp
    
    def set(self, sql: str, results: List[Dict], db_identifier: str = "default"):
        """
        Cache query results.
        
        Args:
            sql: SQL query string
            results: Query results
            db_identifier: Database identifier
        """
        with self._lock:
            key = self._make_key(sql, db_identifier)
            
            # Remove oldest if cache is full
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (results, time.time())
    
    def invalidate(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: SQL pattern to match (None = clear all)
        """
        with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                # Remove matching entries
                keys_to_remove = []
                for key in self._cache.keys():
                    # This is simplified - could implement regex matching
                    keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 2),
                "ttl_seconds": self.ttl_seconds
            }
    
    def clear_stats(self):
        """Reset statistics counters."""
        with self._lock:
            self._hits = 0
            self._misses = 0


# =============================================================================
# GLOBAL CACHE INSTANCE
# =============================================================================

# Global cache instance for easy access
_global_cache: Optional[QueryCache] = None


def get_query_cache(max_size: int = 1000, ttl_seconds: int = 300) -> QueryCache:
    """
    Get or create global query cache instance.
    Uses singleton pattern to ensure one cache across application.
    
    Args:
        max_size: Maximum cache size
        ttl_seconds: Cache TTL
    
    Returns:
        QueryCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryCache(max_size=max_size, ttl_seconds=ttl_seconds)
    return _global_cache


# =============================================================================
# DECORATOR FOR AUTOMATIC CACHING
# =============================================================================

def cache_query_results(ttl_seconds: int = 300):
    """
    Decorator to automatically cache function results.
    
    Usage:
        @cache_query_results(ttl_seconds=300)
        def execute_query(sql: str) -> List[Dict]:
            # ... database execution
            return results
    """
    def decorator(func):
        def wrapper(self, sql: str, *args, **kwargs):
            cache = get_query_cache(ttl_seconds=ttl_seconds)
            db_id = getattr(self, 'db_identifier', 'default')
            
            # Try cache first
            cached = cache.get(sql, db_id)
            if cached is not None:
                results, _ = cached
                return results
            
            # Execute query
            results = func(self, sql, *args, **kwargs)
            
            # Cache results
            if isinstance(results, (list, tuple)) and len(results) <= 10000:
                # Only cache reasonably sized results
                cache.set(sql, results, db_id)
            
            return results
        
        return wrapper
    return decorator
