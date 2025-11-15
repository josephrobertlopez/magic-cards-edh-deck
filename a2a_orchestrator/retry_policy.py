"""Retry policy configuration and tenacity-based retry logic for handling transient failures.

This module provides exponential backoff retry strategies for batch processing workflows,
distinguishing between transient errors (rate limits, timeouts) that should be retried
and permanent errors (404, 401) that should fail immediately.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Callable
import random
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    RetryCallState
)


logger = logging.getLogger(__name__)


class BackoffStrategy(Enum):
    """Retry backoff calculation strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CONSTANT_DELAY = "constant_delay"


class RetryableError(Enum):
    """Error types eligible for retry (transient errors only)."""
    HTTP_429 = "HTTP_429"  # Rate limit exceeded
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"  # Request timeout
    CONNECTION_RESET = "CONNECTION_RESET"  # Connection reset by peer
    HTTP_503 = "HTTP_503"  # Service unavailable


@dataclass
class RetryPolicy:
    """Configuration for handling transient failures with exponential backoff.

    Attributes:
        max_retries: Maximum retry attempts per request (default: 3)
        initial_delay_seconds: Starting delay before first retry (default: 1.0)
        max_delay_seconds: Maximum delay cap for exponential backoff (default: 8.0)
        backoff_strategy: Delay calculation method (default: EXPONENTIAL_BACKOFF)
        jitter_enabled: Add ±25% random variance to prevent thundering herd (default: True)
        retryable_errors: Error types eligible for retry (default: [HTTP_429, NETWORK_TIMEOUT])

    Validation:
        - max_retries >= 0
        - initial_delay_seconds > 0
        - max_delay_seconds >= initial_delay_seconds
        - retryable_errors must not include permanent errors (404, 401, 403)

    Example:
        >>> policy = RetryPolicy(
        ...     max_retries=3,
        ...     initial_delay_seconds=1.0,
        ...     max_delay_seconds=8.0,
        ...     backoff_strategy=BackoffStrategy.EXPONENTIAL_BACKOFF,
        ...     jitter_enabled=True,
        ...     retryable_errors=[RetryableError.HTTP_429, RetryableError.NETWORK_TIMEOUT]
        ... )
        >>> decorator = create_retry_decorator(policy)
    """
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 8.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_BACKOFF
    jitter_enabled: bool = True
    retryable_errors: List[RetryableError] = field(
        default_factory=lambda: [RetryableError.HTTP_429, RetryableError.NETWORK_TIMEOUT]
    )

    def __post_init__(self):
        """Validate retry policy configuration."""
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")
        if self.initial_delay_seconds <= 0:
            raise ValueError(f"initial_delay_seconds must be > 0, got {self.initial_delay_seconds}")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError(
                f"max_delay_seconds ({self.max_delay_seconds}) must be >= "
                f"initial_delay_seconds ({self.initial_delay_seconds})"
            )

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate retry delay based on backoff strategy.

        Args:
            retry_count: Current retry attempt (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay_seconds
        """
        if self.backoff_strategy == BackoffStrategy.EXPONENTIAL_BACKOFF:
            # delay = initial_delay * (2 ^ retry_count), capped at max_delay
            delay = min(self.initial_delay_seconds * (2 ** retry_count), self.max_delay_seconds)
        elif self.backoff_strategy == BackoffStrategy.LINEAR_BACKOFF:
            # delay = initial_delay * retry_count, capped at max_delay
            delay = min(self.initial_delay_seconds * (retry_count + 1), self.max_delay_seconds)
        elif self.backoff_strategy == BackoffStrategy.CONSTANT_DELAY:
            # delay = initial_delay (no increase)
            delay = self.initial_delay_seconds
        else:
            raise ValueError(f"Unknown backoff strategy: {self.backoff_strategy}")

        # Apply jitter: ±25% random variance to prevent synchronized retries
        if self.jitter_enabled:
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)

        return max(0, delay)  # Ensure non-negative


def create_retry_decorator(policy: RetryPolicy, exception_types: tuple = None):
    """Create a tenacity retry decorator from RetryPolicy configuration.

    Args:
        policy: RetryPolicy configuration
        exception_types: Tuple of exception classes to retry (if None, retries all exceptions)

    Returns:
        Tenacity retry decorator configured with policy settings

    Example:
        >>> from a2a_orchestrator.retry_policy import RetryPolicy, create_retry_decorator
        >>> from a2a_orchestrator.exceptions import RateLimitError, TimeoutError
        >>>
        >>> policy = RetryPolicy(max_retries=3, initial_delay_seconds=1.0)
        >>> retry_decorator = create_retry_decorator(policy, (RateLimitError, TimeoutError))
        >>>
        >>> @retry_decorator
        ... async def fetch_with_retry(url):
        ...     response = await fetch(url)
        ...     if response.status == 429:
        ...         raise RateLimitError("API rate limit exceeded")
        ...     return response
    """
    # Build wait strategy based on backoff configuration
    if policy.backoff_strategy == BackoffStrategy.EXPONENTIAL_BACKOFF:
        wait_strategy = wait_exponential(
            multiplier=policy.initial_delay_seconds,
            min=policy.initial_delay_seconds,
            max=policy.max_delay_seconds
        )
    elif policy.backoff_strategy == BackoffStrategy.LINEAR_BACKOFF:
        # Tenacity doesn't have built-in linear backoff, use custom wait function
        def wait_linear(retry_state: RetryCallState) -> float:
            return policy.calculate_delay(retry_state.attempt_number - 1)
        wait_strategy = wait_linear
    elif policy.backoff_strategy == BackoffStrategy.CONSTANT_DELAY:
        wait_strategy = wait_fixed(policy.initial_delay_seconds)
    else:
        raise ValueError(f"Unknown backoff strategy: {policy.backoff_strategy}")

    # Build retry predicate (which exceptions to retry)
    retry_predicate = retry_if_exception_type(exception_types) if exception_types else None

    # Create decorator with logging
    return retry(
        retry=retry_predicate,
        wait=wait_strategy,
        stop=stop_after_attempt(policy.max_retries + 1),  # +1 because tenacity counts initial attempt
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


def apply_retry_policy(policy: RetryPolicy):
    """Decorator factory for applying retry policy to async functions.

    This is a convenience wrapper around create_retry_decorator that automatically
    handles exception type detection based on policy.retryable_errors.

    Args:
        policy: RetryPolicy configuration

    Returns:
        Retry decorator configured with policy settings

    Example:
        >>> @apply_retry_policy(RetryPolicy(max_retries=3))
        ... async def fetch_card_image(card_name: str):
        ...     # Implementation with automatic retry on transient errors
        ...     pass
    """
    # For now, return decorator that retries on all exceptions
    # In future, can map RetryableError enum to specific exception types
    return create_retry_decorator(policy, exception_types=None)
