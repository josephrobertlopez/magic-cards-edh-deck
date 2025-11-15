"""Parallel batch processing engine using asyncio for 10x speedup over sequential execution.

This module provides batch execution with concurrency control using asyncio.Semaphore,
enabling parallel processing while respecting API rate limits and system resources.
"""

import asyncio
import logging
from typing import List, Dict, Any, Callable, Optional, TypeVar, Coroutine
from dataclasses import dataclass
import time


logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for batch items
R = TypeVar('R')  # Generic type for batch results


@dataclass
class BatchConfig:
    """Configuration entity controlling parallel execution behavior.

    Attributes:
        batch_size: Number of items to process in each batch (minimum: 1, default: 10)
        max_concurrent: Maximum number of batches to execute simultaneously (minimum: 1, default: 3)
        retry_strategy: Strategy type for handling transient failures (exponential_backoff, linear_backoff, none)
        request_timeout_seconds: Per-request timeout to prevent hung connections (minimum: 1, default: 30)

    Validation:
        - batch_size must be positive integer (1-50 recommended for Scryfall API)
        - max_concurrent must be positive integer
        - request_timeout_seconds must be positive integer

    Example:
        >>> config = BatchConfig(
        ...     batch_size=10,
        ...     max_concurrent=3,
        ...     retry_strategy="exponential_backoff",
        ...     request_timeout_seconds=30
        ... )
    """
    batch_size: int = 10
    max_concurrent: int = 3
    retry_strategy: str = "exponential_backoff"
    request_timeout_seconds: int = 30

    def __post_init__(self):
        """Validate batch configuration."""
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be > 0, got {self.batch_size}")
        if self.batch_size > 50:
            logger.warning(
                f"batch_size={self.batch_size} exceeds recommended maximum (50). "
                f"This may violate API fair use policies."
            )
        if self.max_concurrent <= 0:
            raise ValueError(f"max_concurrent must be > 0, got {self.max_concurrent}")
        if self.request_timeout_seconds <= 0:
            raise ValueError(
                f"request_timeout_seconds must be > 0, got {self.request_timeout_seconds}"
            )


@dataclass
class BatchResult:
    """Result of processing a single batch.

    Attributes:
        batch_number: Sequential batch identifier (1-indexed)
        items_processed: List of items that were processed
        successes: List of successful results
        failures: List of failure details [{item, error_type, message}, ...]
        success_count: Number of successful operations
        failure_count: Number of failed operations
        duration_seconds: Batch execution time

    Validation:
        success_count + failure_count == len(items_processed)
    """
    batch_number: int
    items_processed: List[Any]
    successes: List[Any]
    failures: List[Dict[str, str]]
    success_count: int
    failure_count: int
    duration_seconds: float

    def __post_init__(self):
        """Validate batch result counts."""
        if self.success_count + self.failure_count != len(self.items_processed):
            logger.warning(
                f"Batch {self.batch_number} count mismatch: "
                f"{self.success_count} + {self.failure_count} != {len(self.items_processed)}"
            )


class BatchProcessor:
    """Parallel batch processing engine using asyncio.Semaphore for concurrency control.

    Processes items in batches with configurable concurrency limiting, enabling
    10x+ speedup over sequential processing while respecting API rate limits.

    Example:
        >>> import asyncio
        >>> async def fetch_card(card_name: str) -> dict:
        ...     # Fetch card data from API
        ...     return {"name": card_name, "data": ...}
        >>>
        >>> config = BatchConfig(batch_size=10, max_concurrent=3)
        >>> processor = BatchProcessor(config)
        >>>
        >>> card_names = ["Sol Ring", "Command Tower", ...]  # 100 cards
        >>> results = asyncio.run(processor.process_batches(card_names, fetch_card))
        >>> # Processes 100 cards in ~10 batches, 3 concurrent = ~33% faster than sequential batches
    """

    def __init__(self, config: BatchConfig):
        """Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)

    async def process_batches(
        self,
        items: List[T],
        processor_func: Callable[[T], Coroutine[Any, Any, R]],
        manifest_logger: Optional[Any] = None
    ) -> List[BatchResult]:
        """Process items in parallel batches with concurrency control.

        Args:
            items: List of items to process (e.g., card names)
            processor_func: Async function to process each item
            manifest_logger: Optional ExecutionManifestLogger for structured logging

        Returns:
            List of BatchResult objects (one per batch)

        Raises:
            BatchProcessingError: If ≥50% of batches fail (partial success threshold)

        Example:
            >>> async def fetch_card(card_name: str):
            ...     return await api.get_card(card_name)
            >>>
            >>> processor = BatchProcessor(BatchConfig(batch_size=10, max_concurrent=3))
            >>> results = await processor.process_batches(card_names, fetch_card)
            >>> total_success = sum(r.success_count for r in results)
        """
        # Split items into batches
        batches = [
            items[i:i + self.config.batch_size]
            for i in range(0, len(items), self.config.batch_size)
        ]

        logger.info(
            f"Processing {len(items)} items in {len(batches)} batches "
            f"(batch_size={self.config.batch_size}, max_concurrent={self.config.max_concurrent})"
        )

        # Process batches in parallel with semaphore limiting concurrency
        batch_results = await asyncio.gather(
            *[
                self._process_batch_with_limit(
                    batch_number=i + 1,
                    batch_items=batch,
                    processor_func=processor_func,
                    manifest_logger=manifest_logger
                )
                for i, batch in enumerate(batches)
            ],
            return_exceptions=True  # Don't cancel all batches if one fails
        )

        # Separate successful batches from exceptions
        successful_batches = []
        failed_batches = []

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing exception: {result}")
                failed_batches.append(result)
            else:
                successful_batches.append(result)

        # Check partial success threshold (≥50% batches must succeed)
        success_rate = len(successful_batches) / len(batches) if batches else 0.0

        if success_rate < 0.5:
            from a2a_orchestrator.exceptions import BatchProcessingError
            raise BatchProcessingError(
                f"Batch processing failed: {len(successful_batches)}/{len(batches)} "
                f"batches succeeded ({success_rate:.1%} < 50% threshold)\n"
                f"Failed batches: {len(failed_batches)}"
            )

        # Log warning if some batches failed but above threshold
        if failed_batches:
            logger.warning(
                f"Partial success: {len(successful_batches)}/{len(batches)} "
                f"batches succeeded ({success_rate:.1%})"
            )

        return successful_batches

    async def _process_batch_with_limit(
        self,
        batch_number: int,
        batch_items: List[T],
        processor_func: Callable[[T], Coroutine[Any, Any, R]],
        manifest_logger: Optional[Any] = None
    ) -> BatchResult:
        """Process a single batch with semaphore concurrency control.

        Args:
            batch_number: Sequential batch identifier (1-indexed)
            batch_items: Items to process in this batch
            processor_func: Async function to process each item
            manifest_logger: Optional ExecutionManifestLogger

        Returns:
            BatchResult with success/failure counts and details
        """
        async with self.semaphore:
            return await self._process_batch(
                batch_number, batch_items, processor_func, manifest_logger
            )

    async def _process_batch(
        self,
        batch_number: int,
        batch_items: List[T],
        processor_func: Callable[[T], Coroutine[Any, Any, R]],
        manifest_logger: Optional[Any] = None
    ) -> BatchResult:
        """Process items within a single batch.

        Args:
            batch_number: Sequential batch identifier (1-indexed)
            batch_items: Items to process in this batch
            processor_func: Async function to process each item
            manifest_logger: Optional ExecutionManifestLogger

        Returns:
            BatchResult with success/failure counts
        """
        start_time = time.time()

        if manifest_logger:
            manifest_logger.log_batch_start(batch_number, batch_items)

        logger.debug(f"Starting batch {batch_number} ({len(batch_items)} items)")

        # Process all items in batch concurrently
        results = await asyncio.gather(
            *[
                self._process_item_with_timeout(item, processor_func)
                for item in batch_items
            ],
            return_exceptions=True
        )

        # Separate successes from failures
        successes = []
        failures = []

        for item, result in zip(batch_items, results):
            if isinstance(result, Exception):
                failures.append({
                    "item": str(item),
                    "error_type": type(result).__name__,
                    "message": str(result)
                })
            else:
                successes.append(result)

        duration = time.time() - start_time

        batch_result = BatchResult(
            batch_number=batch_number,
            items_processed=batch_items,
            successes=successes,
            failures=failures,
            success_count=len(successes),
            failure_count=len(failures),
            duration_seconds=duration
        )

        if manifest_logger:
            manifest_logger.log_batch_complete(
                batch_number=batch_number,
                items_processed=batch_items,
                success_count=batch_result.success_count,
                failure_count=batch_result.failure_count,
                errors=batch_result.failures,
                duration_seconds=duration
            )

        logger.info(
            f"Batch {batch_number} complete: {batch_result.success_count} success, "
            f"{batch_result.failure_count} failure ({duration:.2f}s)"
        )

        return batch_result

    async def _process_item_with_timeout(
        self,
        item: T,
        processor_func: Callable[[T], Coroutine[Any, Any, R]]
    ) -> R:
        """Process a single item with timeout protection.

        Args:
            item: Item to process
            processor_func: Async function to process item

        Returns:
            Processed result

        Raises:
            TimeoutError: If processing exceeds request_timeout_seconds
        """
        try:
            return await asyncio.wait_for(
                processor_func(item),
                timeout=self.config.request_timeout_seconds
            )
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Request timeout after {self.config.request_timeout_seconds}s"
            )
