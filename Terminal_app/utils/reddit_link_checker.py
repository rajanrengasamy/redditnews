"""
Reddit Link Checker Utility

Validates Reddit post URLs to confirm they exist and are accessible.
Returns structured status information for verification decisions.
"""

import logging
import requests
from datetime import datetime, timezone
from typing import TypedDict, Literal, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Reuse the same User-Agent from Stage 1 for consistency
DEFAULT_USER_AGENT = "mac:com.antigravity.redditnewspipeline:v1.0 (by /u/antigravity_agent)"

# Status codes for link check results
LinkStatus = Literal["ok", "redirect", "not_found", "forbidden", "rate_limited", "error"]


class RedditLinkCheckResult(TypedDict):
    """Structured result from Reddit link check."""
    status: LinkStatus
    http_status: Optional[int]
    final_url: Optional[str]
    checked_at: str
    error_message: Optional[str]


def check_reddit_link(
    url: str,
    timeout: float = 10.0,
    user_agent: str = DEFAULT_USER_AGENT
) -> RedditLinkCheckResult:
    """
    Check if a Reddit post URL is valid and accessible.

    Uses HEAD request with redirects to efficiently check URL status
    without downloading full content.

    Args:
        url: Reddit post URL to check
        timeout: Request timeout in seconds
        user_agent: User-Agent header for Reddit API compliance

    Returns:
        RedditLinkCheckResult with status, http_status, final_url, and timestamp

    Example:
        >>> result = check_reddit_link("https://www.reddit.com/r/technology/comments/abc123/")
        >>> if result['status'] in ('ok', 'redirect'):
        ...     print("Link is valid")
    """
    checked_at = datetime.now(timezone.utc).isoformat()

    # Validate URL is actually a Reddit URL
    parsed = urlparse(url)
    if not parsed.netloc.endswith(('reddit.com', 'redd.it')):
        return RedditLinkCheckResult(
            status="error",
            http_status=None,
            final_url=None,
            checked_at=checked_at,
            error_message=f"Not a Reddit URL: {parsed.netloc}"
        )

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml"
    }

    try:
        # Use HEAD request for efficiency (no body download)
        response = requests.head(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )

        http_status = response.status_code
        final_url = response.url

        # Determine status based on HTTP code
        if http_status == 200:
            # Check if redirected to a different domain (usually error page)
            if final_url != url and not urlparse(final_url).netloc.endswith(('reddit.com', 'redd.it')):
                status: LinkStatus = "redirect"
            else:
                status = "ok"
        elif http_status == 301 or http_status == 302 or http_status == 307:
            status = "redirect"
        elif http_status == 404:
            status = "not_found"
        elif http_status == 403:
            status = "forbidden"
        elif http_status == 429:
            status = "rate_limited"
        else:
            status = "error"

        return RedditLinkCheckResult(
            status=status,
            http_status=http_status,
            final_url=final_url,
            checked_at=checked_at,
            error_message=None
        )

    except requests.exceptions.Timeout:
        return RedditLinkCheckResult(
            status="error",
            http_status=None,
            final_url=None,
            checked_at=checked_at,
            error_message="Request timed out"
        )
    except requests.exceptions.ConnectionError as e:
        return RedditLinkCheckResult(
            status="error",
            http_status=None,
            final_url=None,
            checked_at=checked_at,
            error_message=f"Connection error: {str(e)[:100]}"
        )
    except requests.exceptions.RequestException as e:
        return RedditLinkCheckResult(
            status="error",
            http_status=None,
            final_url=None,
            checked_at=checked_at,
            error_message=f"Request error: {str(e)[:100]}"
        )


def is_link_valid_for_verification(result: RedditLinkCheckResult) -> bool:
    """
    Determine if a link check result allows verification to proceed.

    According to requirements:
    - ok/redirect: Can proceed with verification
    - not_found/forbidden: Should drop or mark unverifiable
    - rate_limited: Preserve but don't claim verified without sources
    - error: Preserve but don't claim verified without sources

    Args:
        result: Link check result from check_reddit_link()

    Returns:
        True if status is 'ok' or 'redirect', False otherwise
    """
    return result['status'] in ('ok', 'redirect')


def check_reddit_links_batch(
    urls: list[str],
    timeout: float = 10.0,
    user_agent: str = DEFAULT_USER_AGENT,
    delay_seconds: float = 0.5
) -> dict[str, RedditLinkCheckResult]:
    """
    Check multiple Reddit URLs with rate limiting.

    Args:
        urls: List of Reddit URLs to check
        timeout: Request timeout per URL
        user_agent: User-Agent header
        delay_seconds: Delay between requests to avoid rate limiting

    Returns:
        Dictionary mapping URL to its check result
    """
    import time

    results = {}
    for i, url in enumerate(urls):
        results[url] = check_reddit_link(url, timeout, user_agent)

        # Rate limit between requests (not after last)
        if i < len(urls) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)

    return results
