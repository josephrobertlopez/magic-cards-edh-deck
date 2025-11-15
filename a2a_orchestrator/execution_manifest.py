"""Structured execution logging using JSON Lines format for batch workflow debugging.

This module provides append-only JSONL logging for batch execution state, enabling
debugging, resumption, and auditing of parallel workflow executions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of execution manifest events."""
    WORKFLOW_START = "workflow_start"
    BATCH_START = "batch_start"
    BATCH_COMPLETE = "batch_complete"
    WORKFLOW_COMPLETE = "workflow_complete"
    ERROR = "error"


class ExecutionManifestLogger:
    """Structured append-only logger for batch execution state.

    Logs batch processing events to JSON Lines (newline-delimited JSON) format,
    enabling streamable, resumable execution tracking.

    Attributes:
        manifest_path: Path to JSONL manifest file
        workflow_name: Name of workflow being executed
        workflow_run_id: Unique identifier for this workflow run

    File Format:
        Each line is a valid JSON object representing an event:
        - workflow_start: Workflow execution begins
        - batch_start: Batch processing starts
        - batch_complete: Batch processing completes (includes success/failure counts)
        - workflow_complete: Workflow execution ends
        - error: Critical error occurred

    Example:
        >>> logger = ExecutionManifestLogger(
        ...     manifest_path=Path(".execution_manifests/commander_proxies_20250115.jsonl"),
        ...     workflow_name="commander_to_proxies",
        ...     workflow_run_id="20250115_143022"
        ... )
        >>> logger.log_workflow_start({"commander": "Atraxa", "total_cards": 100})
        >>> logger.log_batch_start(batch_number=1, items=["Sol Ring", "Command Tower"])
        >>> logger.log_batch_complete(batch_number=1, success_count=2, failure_count=0, errors=[])
        >>> logger.log_workflow_complete({"status": "success", "pptx_path": "output.pptx"})
    """

    def __init__(self, manifest_path: Path, workflow_name: str, workflow_run_id: str):
        """Initialize execution manifest logger.

        Args:
            manifest_path: Path to JSONL manifest file (created if doesn't exist)
            workflow_name: Name of workflow being executed
            workflow_run_id: Unique identifier for this workflow run
        """
        self.manifest_path = Path(manifest_path)
        self.workflow_name = workflow_name
        self.workflow_run_id = workflow_run_id

        # Create parent directory if needed
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_event(self, event: Dict[str, Any]) -> None:
        """Append event to JSONL manifest file.

        Args:
            event: Event data (will be serialized to JSON)
        """
        with open(self.manifest_path, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def _create_base_event(self, event_type: EventType) -> Dict[str, Any]:
        """Create base event structure with timestamp and metadata.

        Args:
            event_type: Type of event being logged

        Returns:
            Base event dictionary with common fields
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "workflow_name": self.workflow_name,
            "workflow_run_id": self.workflow_run_id
        }

    def log_workflow_start(self, metadata: Dict[str, Any]) -> None:
        """Log workflow execution start event.

        Args:
            metadata: Workflow-specific metadata (e.g., commander name, total cards)

        Example:
            >>> logger.log_workflow_start({
            ...     "commander": "Atraxa, Praetors' Voice",
            ...     "total_cards": 100,
            ...     "batch_size": 10,
            ...     "max_concurrent": 3
            ... })
        """
        event = self._create_base_event(EventType.WORKFLOW_START)
        event.update(metadata)
        self._append_event(event)
        logger.info(f"Workflow '{self.workflow_name}' started (run_id: {self.workflow_run_id})")

    def log_batch_start(self, batch_number: int, items: List[str]) -> None:
        """Log batch processing start event.

        Args:
            batch_number: Sequential batch identifier (1-indexed)
            items: List of items in batch (e.g., card names)

        Example:
            >>> logger.log_batch_start(1, ["Sol Ring", "Command Tower", "Cyclonic Rift"])
        """
        event = self._create_base_event(EventType.BATCH_START)
        event.update({
            "batch_number": batch_number,
            "item_count": len(items),
            "items": items
        })
        self._append_event(event)
        logger.debug(f"Batch {batch_number} started ({len(items)} items)")

    def log_batch_complete(
        self,
        batch_number: int,
        items_processed: List[str],
        success_count: int,
        failure_count: int,
        errors: List[Dict[str, str]],
        duration_seconds: Optional[float] = None
    ) -> None:
        """Log batch processing completion event.

        Args:
            batch_number: Sequential batch identifier (1-indexed)
            items_processed: List of all items that were processed
            success_count: Number of successful operations
            failure_count: Number of failed operations
            errors: List of error details [{item, error_type, message}, ...]
            duration_seconds: Optional batch execution time for performance analysis

        Validation:
            success_count + failure_count must equal len(items_processed)

        Example:
            >>> logger.log_batch_complete(
            ...     batch_number=2,
            ...     items_processed=["Card1", "Card2", "Card3"],
            ...     success_count=2,
            ...     failure_count=1,
            ...     errors=[{
            ...         "item": "Card3",
            ...         "error_type": "HTTP_429",
            ...         "message": "Rate limit exceeded"
            ...     }],
            ...     duration_seconds=4.567
            ... )
        """
        # Validate counts
        if success_count + failure_count != len(items_processed):
            logger.warning(
                f"Batch {batch_number} count mismatch: "
                f"{success_count} success + {failure_count} failure "
                f"!= {len(items_processed)} processed"
            )

        event = self._create_base_event(EventType.BATCH_COMPLETE)
        event.update({
            "batch_number": batch_number,
            "items_processed": items_processed,
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors
        })

        if duration_seconds is not None:
            event["duration_seconds"] = round(duration_seconds, 3)

        self._append_event(event)
        logger.info(
            f"Batch {batch_number} complete: {success_count} success, "
            f"{failure_count} failure"
        )

    def log_workflow_complete(self, metadata: Dict[str, Any]) -> None:
        """Log workflow execution completion event.

        Args:
            metadata: Workflow completion metadata (e.g., final status, output paths)

        Example:
            >>> logger.log_workflow_complete({
            ...     "status": "success",
            ...     "total_batches": 10,
            ...     "total_success": 95,
            ...     "total_failure": 5,
            ...     "pptx_path": "outputs/atraxa_proxies.pptx"
            ... })
        """
        event = self._create_base_event(EventType.WORKFLOW_COMPLETE)
        event.update(metadata)
        self._append_event(event)
        logger.info(f"Workflow '{self.workflow_name}' completed (run_id: {self.workflow_run_id})")

    def log_error(self, error_message: str, error_context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical error event.

        Args:
            error_message: Error message
            error_context: Optional error context (e.g., batch number, item name)

        Example:
            >>> logger.log_error(
            ...     "Scryfall API completely unreachable",
            ...     {"batch_number": 3, "attempt": 5}
            ... )
        """
        event = self._create_base_event(EventType.ERROR)
        event.update({
            "error_message": error_message,
            "error_context": error_context or {}
        })
        self._append_event(event)
        logger.error(f"Error logged: {error_message}")

    def read_manifest(self) -> List[Dict[str, Any]]:
        """Parse manifest for resumption or debugging.

        Returns:
            List of all events from manifest file

        Example:
            >>> events = logger.read_manifest()
            >>> batch_events = [e for e in events if e["event_type"] == "batch_complete"]
            >>> total_success = sum(e["success_count"] for e in batch_events)
        """
        if not self.manifest_path.exists():
            return []

        events = []
        with open(self.manifest_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    events.append(json.loads(line.strip()))
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse manifest line {line_num}: {e}\n"
                        f"Line content: {line.strip()}"
                    )

        return events

    def get_batch_summary(self) -> Dict[str, Any]:
        """Get summary statistics from manifest.

        Returns:
            Dictionary with batch processing statistics

        Example:
            >>> summary = logger.get_batch_summary()
            >>> print(f"Success rate: {summary['success_rate']:.1%}")
            >>> print(f"Total batches: {summary['total_batches']}")
        """
        events = self.read_manifest()
        batch_events = [e for e in events if e.get("event_type") == "batch_complete"]

        if not batch_events:
            return {
                "total_batches": 0,
                "total_success": 0,
                "total_failure": 0,
                "success_rate": 0.0
            }

        total_success = sum(e.get("success_count", 0) for e in batch_events)
        total_failure = sum(e.get("failure_count", 0) for e in batch_events)
        total_items = total_success + total_failure

        return {
            "total_batches": len(batch_events),
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": total_success / total_items if total_items > 0 else 0.0,
            "all_errors": [
                error
                for event in batch_events
                for error in event.get("errors", [])
            ]
        }
