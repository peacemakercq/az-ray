"""Utility functions for common operations across the application."""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Tuple, Type


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        backoff_factor: Factor to increase delay after each retry
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            break

                        delay = min(
                            base_delay * (backoff_factor ** attempt),
                            max_delay
                        )
                        logging.warning(
                            f"Attempt {attempt + 1} failed for "
                            f"{func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        await asyncio.sleep(delay)

                if last_exception:
                    raise last_exception

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                last_exception = None

                for attempt in range(max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            break

                        delay = min(
                            base_delay * (backoff_factor ** attempt),
                            max_delay
                        )
                        logging.warning(
                            f"Attempt {attempt + 1} failed for "
                            f"{func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        time.sleep(delay)

                if last_exception:
                    raise last_exception

            return sync_wrapper
    return decorator
