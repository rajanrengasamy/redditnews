"""
StageBase - Abstract Base Class for Reddit News Pipeline Stages

This module provides a common foundation for all pipeline stages, handling:
- Input validation and file existence checks
- JSON loading and saving with consistent encoding
- Logger setup and configuration
- Rate limiting utilities
- Output path derivation
- API key retrieval
"""

from abc import ABC, abstractmethod
import json
import logging
import os
import re
import time
from typing import List, Dict, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field

from .json_utils import clean_llm_json_response, safe_json_parse


T = TypeVar('T', bound=Dict[str, Any])


class StageBase(ABC, Generic[T]):
    """
    Abstract base class for all pipeline stages.

    Provides common functionality for:
    - Input validation
    - JSON file I/O
    - Logging
    - Rate limiting
    - Output path management
    - API key retrieval

    Attributes:
        stage_number: The stage number (1-6)
        stage_name: Human-readable stage name
        output_filename: Name of the output JSON file
        default_rate_limit: Default sleep duration between operations
        requires_input: Whether stage requires input file (False for stage 1)
        api_key_env_var: Environment variable name for API key
        api_key_fallback: Fallback environment variable name
    """

    # Class attributes to be overridden by subclasses
    stage_number: int = 0
    stage_name: str = "Base Stage"
    output_filename: str = "output.json"
    default_rate_limit: float = 1.0
    requires_input: bool = True
    api_key_env_var: Optional[str] = None
    api_key_fallback: Optional[str] = None

    def __init__(self, input_file: Optional[str] = None):
        """
        Initialize the stage.

        Args:
            input_file: Path to input JSON file (required for stages 2-6)
        """
        self.input_file = input_file
        self.output_file: Optional[str] = None
        self.output_dir: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._api_key: Optional[str] = None

        # Derive output paths if input is provided
        if input_file:
            self.output_dir = os.path.dirname(input_file)
            self.output_file = os.path.join(self.output_dir, self.output_filename)

    # =========================================================================
    # Input Validation
    # =========================================================================

    def validate_input_file(self, path: Optional[str] = None) -> bool:
        """
        Validate that the input file exists.

        Args:
            path: Path to validate (defaults to self.input_file)

        Returns:
            True if validation passes, False otherwise.
        """
        file_path = path or self.input_file

        if not self.requires_input:
            return True

        if not file_path:
            self.logger.error("Input file path not provided")
            return False

        if not os.path.exists(file_path):
            self.logger.error(f"Input file not found: {file_path}")
            return False

        return True

    def get_api_key(self, key_name: Optional[str] = None, required: bool = True) -> Optional[str]:
        """
        Get API key from environment.

        Args:
            key_name: Environment variable name (defaults to self.api_key_env_var)
            required: If True, logs error when key is missing

        Returns:
            API key string or None if not found
        """
        env_var = key_name or self.api_key_env_var

        if not env_var:
            return None

        value = os.getenv(env_var)

        # Try fallback if primary not found
        if not value and self.api_key_fallback:
            value = os.getenv(self.api_key_fallback)
            if value:
                self.logger.debug(f"Using fallback key '{self.api_key_fallback}'")

        if not value and required:
            fallback_msg = f" or {self.api_key_fallback}" if self.api_key_fallback else ""
            self.logger.error(f"{env_var}{fallback_msg} not found in environment")

        self._api_key = value
        return value

    @property
    def api_key(self) -> Optional[str]:
        """Get the API key (lazy loaded)."""
        if self._api_key is None and self.api_key_env_var:
            self.get_api_key()
        return self._api_key

    # =========================================================================
    # JSON I/O Operations
    # =========================================================================

    def load_input(self, file_path: Optional[str] = None) -> List[T]:
        """
        Load items from a JSON file.

        Args:
            file_path: Path to JSON file (defaults to self.input_file)

        Returns:
            List of items loaded from the file.
        """
        path = file_path or self.input_file
        if not path:
            raise ValueError("No file path provided for loading JSON")

        self.logger.debug(f"Loading JSON from {path}")

        with open(path, 'r', encoding='utf-8') as f:
            items: List[T] = json.load(f)

        self.logger.info(f"Loaded {len(items)} items from {path}")
        return items

    def save_output(
        self,
        items: List[T],
        file_path: Optional[str] = None,
        indent: int = 2,
        ensure_ascii: bool = False
    ) -> str:
        """
        Save items to a JSON file.

        Args:
            items: List of items to save.
            file_path: Path to output file (defaults to self.output_file)
            indent: JSON indentation level (default: 2)
            ensure_ascii: Whether to escape non-ASCII characters (default: False)

        Returns:
            Path to the saved file.
        """
        path = file_path or self.output_file
        if not path:
            raise ValueError("No file path provided for saving JSON")

        # Ensure output directory exists
        output_dir = os.path.dirname(path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        self.logger.debug(f"Saving JSON to {path}")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=indent, ensure_ascii=ensure_ascii)

        self.logger.info(f"Saved {len(items)} items to {path}")
        return path

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    def rate_limit(self, seconds: Optional[float] = None) -> None:
        """
        Apply rate limiting by sleeping for specified duration.

        Args:
            seconds: Duration to sleep (defaults to self.default_rate_limit)
        """
        duration = seconds if seconds is not None else self.default_rate_limit
        if duration > 0:
            time.sleep(duration)

    # =========================================================================
    # Logging Helpers
    # =========================================================================

    def log_start(self) -> None:
        """Log the start of this stage."""
        self.logger.info(f"Starting Stage {self.stage_number}: {self.stage_name}")

    def log_complete(self, item_count: Optional[int] = None) -> None:
        """Log the completion of this stage."""
        msg = f"Stage {self.stage_number} complete"
        if item_count is not None:
            msg += f": processed {item_count} items"
        if self.output_file:
            msg += f" -> {self.output_file}"
        self.logger.info(msg)

    def log_progress(self, current: int, total: int, message: Optional[str] = None) -> None:
        """Log progress through a batch of items."""
        progress = f"Processing {current}/{total}"
        if message:
            progress += f": {message}"
        self.logger.info(progress)

    # =========================================================================
    # Output Path Utilities
    # =========================================================================

    def get_output_path(self, filename: str) -> str:
        """Get a path in the output directory for a given filename."""
        if not self.output_dir:
            raise ValueError("Output directory not set")
        return os.path.join(self.output_dir, filename)

    def ensure_output_dir(self, subdir: Optional[str] = None) -> str:
        """Ensure the output directory (or a subdirectory) exists."""
        if not self.output_dir:
            raise ValueError("Output directory not set")

        path = self.output_dir
        if subdir:
            path = os.path.join(self.output_dir, subdir)

        os.makedirs(path, exist_ok=True)
        return path

    # =========================================================================
    # Abstract Methods
    # =========================================================================

    @abstractmethod
    def process(self, items: List[T]) -> List[T]:
        """
        Process the input items and return the results.

        This is the main method that subclasses must implement with
        stage-specific processing logic.

        Args:
            items: List of items to process.

        Returns:
            List of processed items.
        """
        pass

    # =========================================================================
    # Main Execution
    # =========================================================================

    def run(self) -> Optional[List[T]]:
        """
        Execute the stage pipeline.

        Returns:
            List of processed items, or None if validation failed.
        """
        self.log_start()

        # Validate prerequisites
        if not self.validate_input_file():
            return None

        if self.api_key_env_var and not self.get_api_key(required=True):
            return None

        # Load input data (if this stage requires input)
        if self.requires_input and self.input_file:
            items = self.load_input()
        else:
            items = []

        # Process items (stage-specific logic)
        processed_items = self.process(items)

        # Save output
        if processed_items is not None and self.output_file:
            self.save_output(processed_items)

        self.log_complete(len(processed_items) if processed_items else 0)

        return processed_items


class BatchProcessingMixin:
    """
    Mixin class providing batch processing capabilities.
    """

    batch_size: int = 5

    def process_in_batches(
        self,
        items: List[Dict[str, Any]],
        batch_processor,
        rate_limit_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Process items in batches with rate limiting between batches.

        Args:
            items: List of items to process.
            batch_processor: Callable that processes a batch and returns results.
            rate_limit_seconds: Seconds to sleep between batches.

        Returns:
            Combined list of all processed items.
        """
        results = []
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1

            if hasattr(self, 'logger'):
                self.logger.info(f"Processing batch {batch_num}/{total_batches}")

            processed_batch = batch_processor(batch)
            results.extend(processed_batch)

            # Rate limit between batches (not after the last one)
            if i + self.batch_size < len(items):
                time.sleep(rate_limit_seconds)

        return results


class JSONCleanupMixin:
    """
    Mixin class providing JSON response cleanup utilities.
    """

    @staticmethod
    def clean_json_response(content: str) -> str:
        """Clean JSON content that may be wrapped in markdown code blocks."""
        return clean_llm_json_response(content)

    def safe_parse_json(
        self,
        content: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Safely parse JSON with cleanup and error handling."""
        data, error = safe_json_parse(content, default)
        if error and hasattr(self, 'logger'):
            self.logger.warning(f"JSON parse error: {error}")
        return data if data is not None else (default or {})


@dataclass
class Stage6Output:
    """
    Structured output for Stage 6 multi-output handling.

    Stage 6 produces both JSON data and file artifacts.
    """
    manifest_entries: List[Dict] = field(default_factory=list)
    markdown_files: List[str] = field(default_factory=list)
    image_files: List[str] = field(default_factory=list)
    session_dir: str = ""
    timestamp: str = ""
