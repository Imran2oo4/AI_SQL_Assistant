"""
Performance Monitoring and Metrics Collection
Tracks system performance and bottlenecks
"""

from typing import Dict, Any, List, Optional
import time
from dataclasses import dataclass, field
from collections import defaultdict
import threading
from contextlib import contextmanager
import json


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    
    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Timing metrics (in milliseconds)
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    total_response_time: float = 0.0
    
    # Component timing breakdown
    rag_retrieval_time: float = 0.0
    sql_generation_time: float = 0.0
    query_execution_time: float = 0.0
    validation_time: float = 0.0
    
    # RAG metrics
    rag_cache_hits: int = 0
    rag_cache_misses: int = 0
    avg_rag_examples: float = 0.0
    
    # Database metrics
    db_queries_executed: int = 0
    db_cache_hits: int = 0
    db_cache_misses: int = 0
    avg_result_size: float = 0.0
    
    # Model metrics
    groq_calls: int = 0
    groq_errors: int = 0
    groq_rate_limits: int = 0
    tinyllama_calls: int = 0
    
    # Timestamp
    last_updated: float = field(default_factory=time.time)


class PerformanceMonitor:
    """
    Monitors and tracks system performance metrics.
    Thread-safe for concurrent requests.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics = PerformanceMetrics()
        self._lock = threading.RLock()
        self._request_times: List[float] = []
        self._component_times = defaultdict(list)
        self._max_history = 1000  # Keep last 1000 requests
    
    @contextmanager
    def track_request(self):
        """
        Context manager to track request timing.
        
        Usage:
            with monitor.track_request():
                # ... process request
        """
        start_time = time.time()
        try:
            yield
            # Success
            duration_ms = (time.time() - start_time) * 1000
            self._record_request(duration_ms, success=True)
        except Exception as e:
            # Failure
            duration_ms = (time.time() - start_time) * 1000
            self._record_request(duration_ms, success=False)
            raise
    
    @contextmanager
    def track_component(self, component_name: str):
        """
        Track timing for specific component.
        
        Args:
            component_name: Name of component ('rag', 'sql_gen', 'db_exec', etc.)
        
        Usage:
            with monitor.track_component('rag'):
                # ... RAG retrieval code
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self._record_component_time(component_name, duration_ms)
    
    def _record_request(self, duration_ms: float, success: bool):
        """Record request completion."""
        with self._lock:
            self.metrics.total_requests += 1
            
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            # Update timing
            self._request_times.append(duration_ms)
            if len(self._request_times) > self._max_history:
                self._request_times.pop(0)
            
            self.metrics.total_response_time += duration_ms
            self.metrics.avg_response_time = (
                self.metrics.total_response_time / self.metrics.total_requests
            )
            self.metrics.min_response_time = min(
                self.metrics.min_response_time, duration_ms
            )
            self.metrics.max_response_time = max(
                self.metrics.max_response_time, duration_ms
            )
            
            self.metrics.last_updated = time.time()
    
    def _record_component_time(self, component: str, duration_ms: float):
        """Record component timing."""
        with self._lock:
            self._component_times[component].append(duration_ms)
            if len(self._component_times[component]) > self._max_history:
                self._component_times[component].pop(0)
            
            # Update metric
            if component == 'rag':
                times = self._component_times['rag']
                self.metrics.rag_retrieval_time = sum(times) / len(times)
            elif component == 'sql_gen':
                times = self._component_times['sql_gen']
                self.metrics.sql_generation_time = sum(times) / len(times)
            elif component == 'db_exec':
                times = self._component_times['db_exec']
                self.metrics.query_execution_time = sum(times) / len(times)
            elif component == 'validation':
                times = self._component_times['validation']
                self.metrics.validation_time = sum(times) / len(times)
    
    def record_rag_cache(self, hit: bool):
        """Record RAG cache hit/miss."""
        with self._lock:
            if hit:
                self.metrics.rag_cache_hits += 1
            else:
                self.metrics.rag_cache_misses += 1
    
    def record_db_cache(self, hit: bool):
        """Record database cache hit/miss."""
        with self._lock:
            if hit:
                self.metrics.db_cache_hits += 1
            else:
                self.metrics.db_cache_misses += 1
    
    def record_db_query(self, result_count: int):
        """Record database query execution."""
        with self._lock:
            self.metrics.db_queries_executed += 1
            # Update rolling average
            n = self.metrics.db_queries_executed
            old_avg = self.metrics.avg_result_size
            self.metrics.avg_result_size = (
                (old_avg * (n - 1) + result_count) / n
            )
    
    def record_model_call(self, model: str, error: bool = False, rate_limited: bool = False):
        """Record LLM model call."""
        with self._lock:
            if model == 'groq':
                self.metrics.groq_calls += 1
                if error:
                    self.metrics.groq_errors += 1
                if rate_limited:
                    self.metrics.groq_rate_limits += 1
            elif model == 'tinyllama':
                self.metrics.tinyllama_calls += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            # Calculate percentiles
            percentiles = self._calculate_percentiles()
            
            # Calculate cache hit rates
            rag_total = self.metrics.rag_cache_hits + self.metrics.rag_cache_misses
            rag_hit_rate = (
                (self.metrics.rag_cache_hits / rag_total * 100)
                if rag_total > 0 else 0.0
            )
            
            db_total = self.metrics.db_cache_hits + self.metrics.db_cache_misses
            db_hit_rate = (
                (self.metrics.db_cache_hits / db_total * 100)
                if db_total > 0 else 0.0
            )
            
            success_rate = (
                (self.metrics.successful_requests / self.metrics.total_requests * 100)
                if self.metrics.total_requests > 0 else 0.0
            )
            
            groq_error_rate = (
                (self.metrics.groq_errors / self.metrics.groq_calls * 100)
                if self.metrics.groq_calls > 0 else 0.0
            )
            
            return {
                "overview": {
                    "total_requests": self.metrics.total_requests,
                    "successful": self.metrics.successful_requests,
                    "failed": self.metrics.failed_requests,
                    "success_rate_percent": round(success_rate, 2)
                },
                "response_times_ms": {
                    "average": round(self.metrics.avg_response_time, 2),
                    "min": round(self.metrics.min_response_time, 2),
                    "max": round(self.metrics.max_response_time, 2),
                    "p50": round(percentiles.get('p50', 0), 2),
                    "p95": round(percentiles.get('p95', 0), 2),
                    "p99": round(percentiles.get('p99', 0), 2)
                },
                "component_breakdown_ms": {
                    "rag_retrieval": round(self.metrics.rag_retrieval_time, 2),
                    "sql_generation": round(self.metrics.sql_generation_time, 2),
                    "query_execution": round(self.metrics.query_execution_time, 2),
                    "validation": round(self.metrics.validation_time, 2)
                },
                "cache_performance": {
                    "rag": {
                        "hits": self.metrics.rag_cache_hits,
                        "misses": self.metrics.rag_cache_misses,
                        "hit_rate_percent": round(rag_hit_rate, 2)
                    },
                    "database": {
                        "hits": self.metrics.db_cache_hits,
                        "misses": self.metrics.db_cache_misses,
                        "hit_rate_percent": round(db_hit_rate, 2)
                    }
                },
                "database": {
                    "queries_executed": self.metrics.db_queries_executed,
                    "avg_result_size": round(self.metrics.avg_result_size, 2)
                },
                "models": {
                    "groq": {
                        "calls": self.metrics.groq_calls,
                        "errors": self.metrics.groq_errors,
                        "rate_limits": self.metrics.groq_rate_limits,
                        "error_rate_percent": round(groq_error_rate, 2)
                    },
                    "tinyllama": {
                        "calls": self.metrics.tinyllama_calls
                    }
                },
                "last_updated": time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(self.metrics.last_updated)
                )
            }
    
    def _calculate_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles."""
        if not self._request_times:
            return {}
        
        sorted_times = sorted(self._request_times)
        n = len(sorted_times)
        
        return {
            'p50': sorted_times[int(n * 0.50)] if n > 0 else 0,
            'p95': sorted_times[int(n * 0.95)] if n > 0 else 0,
            'p99': sorted_times[int(n * 0.99)] if n > 0 else 0
        }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics = PerformanceMetrics()
            self._request_times.clear()
            self._component_times.clear()
    
    def export_json(self) -> str:
        """Export metrics as JSON string."""
        return json.dumps(self.get_summary(), indent=2)


# =============================================================================
# GLOBAL MONITOR INSTANCE
# =============================================================================

_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get or create global performance monitor.
    Uses singleton pattern.
    
    Returns:
        PerformanceMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor
