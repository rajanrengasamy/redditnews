"""
API Client Factory Module for Reddit News Pipeline

Provides centralized API key management and lazy-initialized client factories
for all external AI services used in the pipeline.
"""

import os
import logging
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

import requests
from openai import OpenAI
from anthropic import Anthropic
from google import genai

logger = logging.getLogger(__name__)


class APIKeyError(Exception):
    """Raised when a required API key is missing or invalid."""

    def __init__(self, key_name: str, message: Optional[str] = None):
        self.key_name = key_name
        self.message = message or f"Required API key '{key_name}' not found in environment."
        super().__init__(self.message)


class ServiceName(str, Enum):
    """Enumeration of supported API services."""
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class APIKeyConfig:
    """Configuration for an API key with optional fallbacks."""
    primary_key: str
    fallback_keys: Tuple[str, ...] = ()
    required: bool = True

    def get_value(self) -> Optional[str]:
        """Retrieve the API key value, checking primary then fallbacks."""
        value = os.getenv(self.primary_key)
        if value:
            return value
        for fallback in self.fallback_keys:
            value = os.getenv(fallback)
            if value:
                logger.debug(f"Using fallback key '{fallback}' for '{self.primary_key}'")
                return value
        return None


# Registry of all API key configurations
API_KEY_CONFIGS: Dict[ServiceName, APIKeyConfig] = {
    ServiceName.PERPLEXITY: APIKeyConfig(
        primary_key="PERPLEXITY_API_KEY",
        required=True
    ),
    ServiceName.GEMINI: APIKeyConfig(
        primary_key="GOOGLE_API_KEY",
        fallback_keys=("GOOGLE_AI_API_KEY",),
        required=True
    ),
    ServiceName.OPENAI: APIKeyConfig(
        primary_key="OPENAI_API_KEY",
        required=True
    ),
    ServiceName.ANTHROPIC: APIKeyConfig(
        primary_key="ANTHROPIC_API_KEY",
        required=True
    ),
}


def get_api_key(service: ServiceName, raise_on_missing: bool = True) -> Optional[str]:
    """
    Retrieve an API key for the specified service.

    Args:
        service: The service to get the API key for.
        raise_on_missing: If True, raises APIKeyError when key is missing.

    Returns:
        The API key string, or None if not found and raise_on_missing is False.

    Raises:
        APIKeyError: If key is missing and raise_on_missing is True.
    """
    config = API_KEY_CONFIGS.get(service)
    if not config:
        raise ValueError(f"Unknown service: {service}")

    value = config.get_value()

    if value is None and raise_on_missing:
        fallback_msg = ""
        if config.fallback_keys:
            fallback_msg = f" (also checked: {', '.join(config.fallback_keys)})"
        raise APIKeyError(
            config.primary_key,
            f"Required API key '{config.primary_key}' not found in environment{fallback_msg}."
        )

    return value


def validate_required_keys(keys: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all specified API keys are present in the environment.

    Args:
        keys: List of environment variable names to check.

    Returns:
        Tuple of (all_valid: bool, missing_keys: List[str])
    """
    missing_keys = []

    for key in keys:
        # Check if it's a service name first
        try:
            service = ServiceName(key.lower())
            if get_api_key(service, raise_on_missing=False) is None:
                config = API_KEY_CONFIGS[service]
                missing_keys.append(config.primary_key)
        except ValueError:
            # It's a raw key name, check directly
            if not os.getenv(key):
                missing_keys.append(key)

    return (len(missing_keys) == 0, missing_keys)


# Client cache for lazy initialization
_client_cache: Dict[str, Any] = {}


def _clear_client_cache() -> None:
    """Clear all cached clients. Useful for testing or key rotation."""
    global _client_cache
    _client_cache.clear()
    logger.debug("Client cache cleared")


# -----------------------------------------------------------------------------
# Perplexity Client (requests-based)
# -----------------------------------------------------------------------------

@dataclass
class PerplexityClient:
    """A simple HTTP client wrapper for Perplexity API."""
    session: requests.Session
    api_key: str
    base_url: str = "https://api.perplexity.ai"

    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """Send a chat completion request to Perplexity."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        response = self.session.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()


def get_perplexity_client(raise_on_missing: bool = True) -> Optional[PerplexityClient]:
    """Get a configured Perplexity API client (cached)."""
    cache_key = "perplexity"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    api_key = get_api_key(ServiceName.PERPLEXITY, raise_on_missing=raise_on_missing)

    if api_key is None:
        return None

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })

    client = PerplexityClient(session=session, api_key=api_key)
    _client_cache[cache_key] = client

    logger.debug("Perplexity client initialized")
    return client


def get_gemini_client(raise_on_missing: bool = True) -> Optional[genai.Client]:
    """Get a configured Google Gemini client (cached)."""
    cache_key = "gemini"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    api_key = get_api_key(ServiceName.GEMINI, raise_on_missing=raise_on_missing)

    if api_key is None:
        return None

    client = genai.Client(api_key=api_key)
    _client_cache[cache_key] = client

    logger.debug("Gemini client initialized")
    return client


def get_openai_client(raise_on_missing: bool = True) -> Optional[OpenAI]:
    """Get a configured OpenAI client (cached)."""
    cache_key = "openai"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    api_key = get_api_key(ServiceName.OPENAI, raise_on_missing=raise_on_missing)

    if api_key is None:
        return None

    client = OpenAI(api_key=api_key)
    _client_cache[cache_key] = client

    logger.debug("OpenAI client initialized")
    return client


def get_anthropic_client(raise_on_missing: bool = True) -> Optional[Anthropic]:
    """Get a configured Anthropic client (cached)."""
    cache_key = "anthropic"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    api_key = get_api_key(ServiceName.ANTHROPIC, raise_on_missing=raise_on_missing)

    if api_key is None:
        return None

    client = Anthropic(api_key=api_key)
    _client_cache[cache_key] = client

    logger.debug("Anthropic client initialized")
    return client


def get_all_configured_services() -> Dict[ServiceName, bool]:
    """Check which services have API keys configured."""
    return {
        service: get_api_key(service, raise_on_missing=False) is not None
        for service in ServiceName
    }


def validate_pipeline_keys(stages: Optional[List[int]] = None) -> Tuple[bool, Dict[int, str]]:
    """
    Validate that all required API keys for specified pipeline stages are present.

    Args:
        stages: List of stage numbers (2-7) to validate. If None, validates all.

    Returns:
        Tuple of (all_valid: bool, missing: Dict[stage_number, key_name])
    """
    stage_requirements = {
        2: ServiceName.PERPLEXITY,
        3: ServiceName.GEMINI,
        4: ServiceName.OPENAI,
        5: ServiceName.ANTHROPIC,
        6: ServiceName.GEMINI,
        7: ServiceName.GEMINI,  # nano-banana (Gemini 2.5 Flash Image) for AI backgrounds
    }

    if stages is None:
        stages = list(stage_requirements.keys())

    missing = {}
    for stage in stages:
        if stage not in stage_requirements:
            continue
        service = stage_requirements[stage]
        if get_api_key(service, raise_on_missing=False) is None:
            config = API_KEY_CONFIGS[service]
            missing[stage] = config.primary_key

    return (len(missing) == 0, missing)
