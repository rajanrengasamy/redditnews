"""
JSON utility functions for handling LLM responses and file operations.

Provides standardized JSON parsing, cleanup, and file I/O with graceful
error handling for the Reddit News Pipeline.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def clean_llm_json_response(content: str) -> str:
    """
    Extract JSON from LLM responses that may be wrapped in markdown code blocks.

    Handles common LLM response formats:
    - Raw JSON
    - JSON wrapped in ```json ... ```
    - JSON wrapped in ``` ... ```
    - JSON with leading/trailing whitespace or text

    Args:
        content: Raw LLM response string that may contain JSON

    Returns:
        Cleaned string with markdown wrapping removed, ready for JSON parsing.
        Returns empty string if input is None or empty.
    """
    if not content:
        return ""

    content = content.strip()

    # Try ```json ... ``` first (most specific)
    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try generic ``` ... ``` blocks
    match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        # Verify it looks like JSON (starts with { or [)
        if extracted and extracted[0] in '{[':
            return extracted

    # Fallback: simple replacement for partial markdown markers
    cleaned = content.replace("```json", "").replace("```", "").strip()

    return cleaned


def safe_json_parse(
    content: str,
    default: Any = None
) -> Tuple[Any, Optional[str]]:
    """
    Safely parse JSON content with automatic LLM response cleanup.

    Combines clean_llm_json_response() with json.loads() and comprehensive
    error handling. Returns a tuple of (parsed_data, error_message) for
    graceful degradation.

    Args:
        content: Raw string that may contain JSON (possibly wrapped in markdown)
        default: Value to return if parsing fails (default: None)

    Returns:
        Tuple of (parsed_data, error_message):
        - On success: (parsed_json_data, None)
        - On failure: (default, error_description_string)
    """
    if content is None:
        return default, "Content is None"

    if not isinstance(content, str):
        return default, f"Expected string, got {type(content).__name__}"

    if not content.strip():
        return default, "Content is empty"

    # Clean up LLM response formatting
    cleaned = clean_llm_json_response(content)

    if not cleaned:
        return default, "No JSON content found after cleanup"

    try:
        parsed = json.loads(cleaned)
        return parsed, None
    except json.JSONDecodeError as e:
        error_position = f"line {e.lineno}, column {e.colno}"
        preview = cleaned[:100] + "..." if len(cleaned) > 100 else cleaned
        error_msg = f"JSON decode error at {error_position}: {e.msg}. Content preview: {preview}"
        logger.debug(f"JSON parse failed: {error_msg}")
        return default, error_msg
    except Exception as e:
        error_msg = f"Unexpected error parsing JSON: {type(e).__name__}: {str(e)}"
        logger.debug(error_msg)
        return default, error_msg


def load_json_file(
    path: str
) -> Tuple[Union[List[Dict], Dict, None], Optional[str]]:
    """
    Load and parse a JSON file with comprehensive error handling.

    Args:
        path: File path to the JSON file

    Returns:
        Tuple of (data, error_message):
        - On success: (parsed_json_data, None)
        - On failure: (None, error_description_string)
    """
    if not path:
        return None, "File path is empty"

    if not os.path.exists(path):
        return None, f"File not found: {path}"

    if not os.path.isfile(path):
        return None, f"Path is not a file: {path}"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in {path}: {e.msg} at line {e.lineno}, column {e.colno}"
        logger.debug(error_msg)
        return None, error_msg
    except PermissionError:
        error_msg = f"Permission denied reading file: {path}"
        logger.debug(error_msg)
        return None, error_msg
    except UnicodeDecodeError as e:
        error_msg = f"Unicode decode error in {path}: {str(e)}"
        logger.debug(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error reading {path}: {type(e).__name__}: {str(e)}"
        logger.debug(error_msg)
        return None, error_msg


def save_json_file(
    path: str,
    data: Union[List, Dict],
    ensure_ascii: bool = False,
    indent: int = 2
) -> Optional[str]:
    """
    Save data to a JSON file with error handling.

    Args:
        path: Destination file path
        data: Data to serialize (typically List[Dict] or Dict)
        ensure_ascii: If False (default), allow non-ASCII characters.
        indent: JSON indentation level (default: 2)

    Returns:
        None on success, error message string on failure
    """
    if not path:
        return "File path is empty"

    if data is None:
        return "Data is None"

    # Ensure parent directory exists
    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except Exception as e:
            return f"Failed to create directory {parent_dir}: {type(e).__name__}: {str(e)}"

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        return None
    except TypeError as e:
        return f"Data is not JSON serializable: {str(e)}"
    except PermissionError:
        return f"Permission denied writing to: {path}"
    except Exception as e:
        return f"Error writing {path}: {type(e).__name__}: {str(e)}"


# Convenience alias
parse_llm_json = safe_json_parse
