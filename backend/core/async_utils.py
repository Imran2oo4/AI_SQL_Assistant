"""
Async optimizations for FastAPI backend
Improves concurrency and throughput
"""

from fastapi import BackgroundTasks
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools


# =============================================================================
# THREAD POOL FOR CPU-BOUND TASKS
# =============================================================================

# Global executor for CPU-bound tasks
_executor: Optional[ThreadPoolExecutor] = None


def get_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """
    Get or create global thread pool executor.
    
    Args:
        max_workers: Maximum number of worker threads
    
    Returns:
        ThreadPoolExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


async def run_in_threadpool(func, *args, **kwargs):
    """
    Run CPU-bound function in thread pool.
    
    Usage:
        result = await run_in_threadpool(expensive_function, arg1, arg2)
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    partial_func = functools.partial(func, *args, **kwargs)
    return await loop.run_in_executor(executor, partial_func)


# All async utility functions have been consolidated into main.py where needed
