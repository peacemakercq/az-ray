"""Test cases for utils module."""

import pytest

from src.utils import retry_with_backoff


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    def test_sync_function_success(self):
        """Test retry decorator with sync function that succeeds."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_sync_function_failure_then_success(self):
        """Test retry decorator with sync function that fails then succeeds."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 3

    def test_sync_function_max_retries_exceeded(self):
        """Test retry decorator when max retries are exceeded."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, base_delay=0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            test_func()
        assert call_count == 3  # Initial call + 2 retries

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test retry decorator with async function that succeeds."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await test_func()
        assert result == "async success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_failure_then_success(self):
        """Test retry decorator with async function that fails then succeeds."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Test error")
            return "async success"

        result = await test_func()
        assert result == "async success"
        assert call_count == 2

    def test_specific_exception_handling(self):
        """Test retry decorator with specific exception types."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.1,
            exceptions=(ValueError,)
        )
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise RuntimeError("Don't retry this")
            return "success"

        with pytest.raises(RuntimeError, match="Don't retry this"):
            test_func()
        assert call_count == 2
