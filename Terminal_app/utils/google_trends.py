"""
Google Trends Utility

Fetches Google Trends data for keywords to assess real-world search interest.
Uses pytrends library with rate limiting and error handling.
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy import to avoid loading pytrends if not needed
_pytrends_available = None
_TrendReq = None


def _ensure_pytrends():
    """Lazy load pytrends to avoid import errors if not installed."""
    global _pytrends_available, _TrendReq
    if _pytrends_available is None:
        try:
            from pytrends.request import TrendReq
            _TrendReq = TrendReq
            _pytrends_available = True
        except ImportError:
            _pytrends_available = False
            logger.warning("pytrends not installed. Google Trends scoring disabled.")
    return _pytrends_available


def extract_keywords(title: str, max_keywords: int = 3) -> List[str]:
    """
    Extract search-worthy keywords from a title.
    
    Args:
        title: The post title
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords suitable for Google Trends search
    """
    if not title:
        return []
    
    # Remove common stop words and noise
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again',
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
        'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while',
        'about', 'against', 'this', 'that', 'these', 'those', 'what', 'which',
        'who', 'whom', 'its', 'it', 'they', 'them', 'their', 'he', 'she',
        'his', 'her', 'my', 'your', 'our', 'we', 'you', 'i', 'me', 'him',
        'says', 'said', 'new', 'now', 'breaking', 'just', 'report', 'reports',
        'according', 'update', 'updates', 'via', 'per', 'says'
    }
    
    # Clean title
    title_clean = re.sub(r'[^\w\s]', ' ', title.lower())
    words = title_clean.split()
    
    # Filter and score words
    keywords = []
    for word in words:
        if len(word) >= 3 and word not in stop_words:
            keywords.append(word)
    
    # Prioritize proper nouns (capitalized in original)
    original_words = title.split()
    proper_nouns = []
    for word in original_words:
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word and clean_word[0].isupper() and clean_word.lower() not in stop_words:
            proper_nouns.append(clean_word.lower())
    
    # Combine: proper nouns first, then other keywords
    result = []
    seen = set()
    for word in proper_nouns + keywords:
        if word not in seen and len(word) >= 3:
            result.append(word)
            seen.add(word)
            if len(result) >= max_keywords:
                break
    
    return result


def get_trends_score(
    keywords: List[str],
    timeframe: str = 'now 7-d',
    geo: str = 'US',
    timeout: float = 10.0
) -> Dict:
    """
    Query Google Trends for keyword interest.
    
    Args:
        keywords: List of keywords to query (max 5 per API rule)
        timeframe: Trends timeframe (default: last 7 days)
        geo: Geographic region (default: US)
        timeout: Request timeout in seconds
        
    Returns:
        Dict with:
            - google_trends_score: Normalized 0-100 score (max interest across keywords)
            - trends_data: Raw data for each keyword
            - trends_available: Whether data was successfully fetched
            - trends_error: Error message if any
    """
    result = {
        'google_trends_score': 0,
        'trends_data': {},
        'trends_available': False,
        'trends_error': None
    }
    
    if not keywords:
        result['trends_error'] = 'No keywords provided'
        return result
    
    if not _ensure_pytrends():
        result['trends_error'] = 'pytrends not available'
        return result
    
    # Limit to 5 keywords (API limit)
    keywords = keywords[:5]
    
    try:
        # Initialize pytrends with timeout
        pytrends = _TrendReq(
            hl='en-US',
            tz=360,
            timeout=(timeout, timeout),
            retries=2,
            backoff_factor=0.5
        )
        
        # Build payload
        pytrends.build_payload(
            keywords,
            cat=0,
            timeframe=timeframe,
            geo=geo,
            gprop=''
        )
        
        # Get interest over time
        interest_df = pytrends.interest_over_time()
        
        if interest_df.empty:
            result['trends_error'] = 'No trends data returned'
            return result
        
        # Calculate scores
        trends_data = {}
        max_score = 0
        
        for keyword in keywords:
            if keyword in interest_df.columns:
                values = interest_df[keyword].values
                avg_interest = float(values.mean())
                max_interest = float(values.max())
                recent_interest = float(values[-1]) if len(values) > 0 else 0
                
                trends_data[keyword] = {
                    'average': round(avg_interest, 1),
                    'max': round(max_interest, 1),
                    'recent': round(recent_interest, 1)
                }
                
                # Use recent interest as primary signal
                max_score = max(max_score, recent_interest)
        
        result['google_trends_score'] = round(max_score, 1)
        result['trends_data'] = trends_data
        result['trends_available'] = True
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        # Check for rate limiting
        if 'rate' in error_msg.lower() or '429' in error_msg:
            result['trends_error'] = 'Rate limited by Google'
        elif 'timeout' in error_msg.lower():
            result['trends_error'] = 'Request timed out'
        else:
            result['trends_error'] = f'Trends API error: {error_msg[:100]}'
        
        logger.warning(f"Google Trends query failed: {result['trends_error']}")
        return result


def score_item_with_trends(
    title: str,
    rate_limit_seconds: float = 1.0
) -> Tuple[int, Dict]:
    """
    Convenience function to score a single item's Google Trends interest.
    
    Args:
        title: The post title
        rate_limit_seconds: Delay after API call to avoid rate limits
        
    Returns:
        Tuple of (score 0-100, full trends data dict)
    """
    keywords = extract_keywords(title)
    
    if not keywords:
        return 0, {'trends_available': False, 'trends_error': 'No keywords extracted'}
    
    result = get_trends_score(keywords)
    
    # Add keywords to result for debugging
    result['keywords_used'] = keywords
    
    # Rate limit
    if result.get('trends_available'):
        time.sleep(rate_limit_seconds)
    
    return result.get('google_trends_score', 0), result
