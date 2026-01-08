"""
Source Validation Utilities

Provides utilities for:
- Building Perplexity search URLs for citation revisiting
- Extracting Reddit outbound URLs from posts
- Deduplicating and normalizing source citations
- Domain extraction for human-readable references
"""

import logging
import re
from typing import TypedDict, Optional, List
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, quote_plus

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class StructuredSource(TypedDict, total=False):
    """Structured source object as required by Stage 2 output schema."""
    url: str
    title: Optional[str]
    publisher: Optional[str]
    published_at: Optional[str]
    source_type: str  # 'primary' or 'secondary'
    evidence: Optional[str]


# =============================================================================
# Perplexity Search URL Generation (S2-04)
# =============================================================================

def build_perplexity_search_url(query: str) -> str:
    """
    Build a deterministic Perplexity search URL from a query string.

    Since Perplexity API doesn't return share links, we construct a
    search URL that approximates the query for browser revisiting.

    Args:
        query: The search query used for validation

    Returns:
        Perplexity search URL that can be opened in a browser

    Example:
        >>> build_perplexity_search_url("OpenAI GPT-5 announcement 2024")
        'https://www.perplexity.ai/search?q=OpenAI+GPT-5+announcement+2024'
    """
    if not query or not query.strip():
        return ""

    # Clean and encode the query
    clean_query = query.strip()

    # Perplexity uses standard URL encoding for search
    encoded_query = quote_plus(clean_query)

    return f"https://www.perplexity.ai/search?q={encoded_query}"


def extract_validation_query(title: str, subreddit: Optional[str] = None) -> str:
    """
    Generate a concise validation query from a Reddit post title.

    Strips common Reddit prefixes and suffixes, extracts key phrases.

    Args:
        title: Reddit post title
        subreddit: Optional subreddit for context

    Returns:
        Clean query string for validation
    """
    # Remove common Reddit patterns
    query = title

    # Remove [tag] prefixes
    query = re.sub(r'^\s*\[[^\]]+\]\s*', '', query)

    # Remove (tag) prefixes
    query = re.sub(r'^\s*\([^)]+\)\s*', '', query)

    # Remove trailing punctuation noise
    query = re.sub(r'[!?]+$', '', query)

    # Truncate if too long (keep first 100 chars for search efficiency)
    if len(query) > 100:
        # Try to break at a word boundary
        query = query[:100].rsplit(' ', 1)[0]

    # Add subreddit context for tech topics if helpful
    if subreddit and subreddit.lower() in ('technology', 'science', 'worldnews'):
        query = f"{query} news"

    return query.strip()


# =============================================================================
# Reddit Outbound URL Extraction (S2-05)
# =============================================================================

# Known Reddit domains that should NOT be treated as outbound
REDDIT_DOMAINS = {
    'reddit.com',
    'www.reddit.com',
    'old.reddit.com',
    'new.reddit.com',
    'redd.it',
    'i.redd.it',
    'v.redd.it',
    'preview.redd.it',
    'external-preview.redd.it',
}


def is_reddit_url(url: str) -> bool:
    """
    Check if a URL is a Reddit domain.

    Args:
        url: URL to check

    Returns:
        True if URL is a Reddit domain, False otherwise
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check against known Reddit domains
        if domain in REDDIT_DOMAINS:
            return True

        # Also check for reddit.com suffix (catches subdomains)
        if domain.endswith('.reddit.com') or domain.endswith('.redd.it'):
            return True

        return False
    except Exception:
        return False


def extract_reddit_outbound_url(item: dict) -> Optional[str]:
    """
    Extract the external URL that a Reddit post links to (if any).

    Reddit link posts contain an external URL; self-posts do not.
    This function attempts to identify if the post links to external content.

    Args:
        item: Item dict from Stage 1 output

    Returns:
        External URL if it's a link post, None for self-posts

    Note:
        This is a heuristic approach. The Reddit RSS feed doesn't explicitly
        distinguish link posts from self-posts. We check if the item URL
        redirects to or contains a non-Reddit outbound link.
    """
    # The 'url' field from RSS is always the Reddit discussion URL
    # For link posts, the actual linked content is in the post body
    # We return None here - actual extraction happens via API or page scraping

    # For now, return None as the RSS feed doesn't include outbound URLs
    # This field will be populated by Perplexity's source extraction
    return None


def extract_domain(url: str, strip_www: bool = True) -> str:
    """
    Extract clean domain from URL for human-readable references.

    Args:
        url: Full URL
        strip_www: Whether to remove 'www.' prefix

    Returns:
        Clean domain string (e.g., 'techcrunch.com')

    Example:
        >>> extract_domain("https://www.techcrunch.com/2024/01/article?utm_source=x")
        'techcrunch.com'
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if strip_www and domain.startswith('www.'):
            domain = domain[4:]

        return domain
    except Exception:
        return ""


# =============================================================================
# Sources Deduplication & Normalization (S2-06)
# =============================================================================

# URL parameters to strip for normalization
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'ref', 'source', 'fbclid', 'gclid', 'msclkid',
    'mc_cid', 'mc_eid', '_ga', '_gl',
    'affiliate', 'partner', 'campaign',
}


def normalize_url(url: str) -> str:
    """
    Normalize a URL by removing tracking parameters.

    Args:
        url: Raw URL

    Returns:
        Cleaned URL without tracking parameters
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)

        # Parse query parameters
        params = parse_qs(parsed.query)

        # Filter out tracking parameters
        clean_params = {
            k: v for k, v in params.items()
            if k.lower() not in TRACKING_PARAMS
        }

        # Rebuild query string
        clean_query = urlencode(clean_params, doseq=True) if clean_params else ""

        # Rebuild URL
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),  # Normalize trailing slash
            parsed.params,
            clean_query,
            ""  # Remove fragment
        ))

        return clean_url

    except Exception:
        return url


def deduplicate_sources(
    raw_citations: List[str],
    structured_sources: Optional[List[StructuredSource]] = None
) -> List[StructuredSource]:
    """
    Deduplicate and normalize sources from Perplexity citations.

    Combines raw citation URLs with any structured source data,
    removes duplicates, filters Reddit URLs, and normalizes.

    Args:
        raw_citations: Flat list of citation URLs from Perplexity
        structured_sources: Optional structured source objects

    Returns:
        Deduplicated list of StructuredSource objects
    """
    seen_domains: dict[str, StructuredSource] = {}
    seen_urls: set[str] = set()

    # First, process structured sources (higher quality)
    if structured_sources:
        for source in structured_sources:
            url = source.get('url', '')
            if not url or is_reddit_url(url):
                continue

            normalized = normalize_url(url)
            if normalized in seen_urls:
                continue

            seen_urls.add(normalized)
            domain = extract_domain(normalized)

            # Keep the best source per domain
            if domain not in seen_domains:
                source_copy = dict(source)
                source_copy['url'] = normalized
                seen_domains[domain] = source_copy
            elif source.get('source_type') == 'primary':
                # Primary sources override secondary
                source_copy = dict(source)
                source_copy['url'] = normalized
                seen_domains[domain] = source_copy

    # Then, add any raw citations not already covered
    for url in raw_citations:
        if not url or is_reddit_url(url):
            continue

        normalized = normalize_url(url)
        if normalized in seen_urls:
            continue

        seen_urls.add(normalized)
        domain = extract_domain(normalized)

        if domain not in seen_domains:
            # Create minimal structured source from raw URL
            seen_domains[domain] = StructuredSource(
                url=normalized,
                title=None,
                publisher=domain,
                source_type='secondary',
                evidence=None
            )

    return list(seen_domains.values())


def filter_non_reddit_sources(sources: List[StructuredSource]) -> List[StructuredSource]:
    """
    Filter to keep only non-Reddit sources.

    Args:
        sources: List of structured sources

    Returns:
        Filtered list with Reddit URLs removed
    """
    return [s for s in sources if not is_reddit_url(s.get('url', ''))]


def has_valid_external_source(sources: List[StructuredSource]) -> bool:
    """
    Check if there is at least one valid non-Reddit source.

    This is part of the verification acceptance criteria.

    Args:
        sources: List of structured sources

    Returns:
        True if at least one non-Reddit source exists
    """
    non_reddit = filter_non_reddit_sources(sources)
    return len(non_reddit) > 0
