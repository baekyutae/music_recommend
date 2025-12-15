"""
VibeCurator Timing Utilities
시간 측정 유틸리티
"""

import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


def timed(func: Callable) -> Callable:
    """함수 실행 시간 측정 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


class Timer:
    """컨텍스트 매니저 타이머"""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.elapsed: float = 0.0
    
    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, *args) -> None:
        self.elapsed = time.perf_counter() - self._start
        if self.name:
            logger.debug(f"{self.name} took {self.elapsed:.4f}s")

