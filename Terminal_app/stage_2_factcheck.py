"""
Stage 2: Fact-Check & Validation

Validates facts using Perplexity API with comprehensive source extraction:
- Validates Reddit post accessibility
- Extracts structured external sources (non-Reddit citations)
- Stores Perplexity search URL for citation revisiting
- Applies verification acceptance criteria
"""

import logging
import os
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from utils.stage_base import StageBase, BatchProcessingMixin, JSONCleanupMixin
from utils.reddit_link_checker import check_reddit_link, is_link_valid_for_verification
from utils.source_utils import (
    build_perplexity_search_url,
    extract_validation_query,
    deduplicate_sources,
    has_valid_external_source,
    is_reddit_url,
    StructuredSource,
)

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"  # Cheapest option for validation


# =============================================================================
# Prompt Templates for Structured Source Extraction
# =============================================================================

SYSTEM_PROMPT = """You are a strict fact-checking and source-attribution agent.

Task:
- For each Reddit-discovered item, determine whether it contains a verifiable real-world claim.
- If it is a question/how-to/discussion/opinion (not a factual claim), classify it and mark it unverifiable.

Hard rules (non-negotiable):
1) NEVER treat Reddit (reddit.com, redd.it) as a verification source.
2) NEVER invent URLs, publishers, quotes, numbers, or dates.
3) "verified" requires at least ONE credible non-Reddit source that DIRECTLY substantiates the claim.
4) Prefer primary sources: official announcements, filings, .gov/.edu, company blogs, peer-reviewed papers.
5) If sources are only tangential OR you can't find any non-Reddit sources → "unverifiable".

For EACH item, return a JSON object with these EXACT fields:
{
  "Item N": {
    "validation_status": "verified | debunked | unverifiable",
    "item_type": "news | discussion | question | opinion",
    "claim_summary": "one-sentence claim being validated (or null if not a claim)",
    "reason": "2-4 sentences, specific and evidence-based",
    "sources": [
      {
        "url": "https://example.com/article",
        "title": "Article title if available",
        "publisher": "Publisher name",
        "source_type": "primary | secondary",
        "evidence": "1 sentence on what this source confirms"
      }
    ],
    "citations": ["https://source1.com", "https://source2.com"],
    "key_entities": ["entity1", "entity2"],
    "time_relevance": "breaking | recent | evergreen | unclear",
    "confidence": 0.0
  }
}

Output:
- Return ONLY valid JSON matching the required schema.
- Keys must be "Item 1", "Item 2", etc., matching the input numbering."""


USER_PROMPT_TEMPLATE = """Validate each item below. For each item:
- Extract the claim being made (if any).
- Classify item_type.
- Decide validation_status.
- Provide 1–5 non-Reddit sources with 1-sentence evidence notes.

Items:
{items_text}"""


def build_validation_prompt(items: List[Dict]) -> tuple:
    """
    Build system and user prompts for Perplexity validation.

    Args:
        items: Batch of items to validate

    Returns:
        Tuple of (system_prompt, user_prompt, query_string)
    """
    item_texts = []
    for idx, item in enumerate(items):
        title = item.get('title', 'Unknown title')
        url = item.get('url', item.get('reddit_post_url', 'No URL'))
        subreddit = item.get('subreddit', '')

        item_texts.append(
            f"Item {idx + 1}:\n"
            f"  Title: \"{title}\"\n"
            f"  Subreddit: r/{subreddit}\n"
            f"  Reddit URL: {url}"
        )

    items_text = "\n\n".join(item_texts)
    user_prompt = USER_PROMPT_TEMPLATE.format(items_text=items_text)

    # Build query for search URL generation (use first item's title)
    query = extract_validation_query(
        items[0].get('title', ''),
        items[0].get('subreddit')
    ) if items else ""

    return SYSTEM_PROMPT, user_prompt, query


# =============================================================================
# Stage 2 Implementation
# =============================================================================

class Stage2FactCheck(StageBase, BatchProcessingMixin, JSONCleanupMixin):
    """
    Stage 2: Validate facts using Perplexity API with source extraction.

    New in v2.0:
    - Validates Reddit post accessibility before Perplexity call
    - Extracts structured sources with source_type classification
    - Stores perplexity_query and perplexity_search_url for citation
    - Applies verification acceptance criteria
    - Distinguishes reddit_post_url from sources
    """

    stage_number = 2
    stage_name = "Fact-Check & Validation"
    output_filename = "2_validated_facts.json"
    default_rate_limit = 1.0
    api_key_env_var = "PERPLEXITY_API_KEY"
    batch_size = 5

    # Schema version for migration tracking
    SCHEMA_VERSION = "2.0"

    # Configuration flags
    check_reddit_links: bool = True
    strict_verification: bool = True  # Require non-Reddit sources for verified

    def __init__(
        self,
        input_file: str,
        keep_statuses: Optional[List[str]] = None,
        drop_inaccessible: bool = True
    ):
        """
        Args:
            input_file: Path to Stage 1 output (1_raw_feed.json)
            keep_statuses: Validation statuses to keep. Default: ['verified']
            drop_inaccessible: If True, drop items where Reddit link is not_found/forbidden
        """
        super().__init__(input_file)
        self.keep_statuses = keep_statuses or ['verified']
        self.drop_inaccessible = drop_inaccessible

    # =========================================================================
    # Reddit Link Validation
    # =========================================================================

    def _check_reddit_link(self, item: Dict) -> Dict:
        """
        Check if the Reddit post URL is accessible.

        Adds reddit_link_check field to item.
        """
        url = item.get('url', '')
        if not url:
            item['reddit_link_check'] = {
                'status': 'error',
                'http_status': None,
                'final_url': None,
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'error_message': 'No URL provided'
            }
            return item

        result = check_reddit_link(url)
        item['reddit_link_check'] = dict(result)
        return item

    # =========================================================================
    # Perplexity API Validation
    # =========================================================================

    def _merge_validation_results(
        self,
        items: List[Dict],
        validation_data: Dict,
        perplexity_query: str
    ) -> List[Dict]:
        """
        Merge Perplexity API validation results back into items.

        Adds new schema fields:
        - reddit_post_url (canonical)
        - sources[] (structured)
        - perplexity_query
        - perplexity_search_url
        - perplexity_reason
        - perplexity_citations (flat list for compatibility)
        - item_type
        """
        perplexity_search_url = build_perplexity_search_url(perplexity_query)

        for idx, item in enumerate(items):
            key = f"Item {idx + 1}"

            # Set canonical reddit_post_url (keep 'url' as alias for backward compat)
            if 'url' in item:
                item['reddit_post_url'] = item['url']

            # reddit_outbound_url placeholder (populated by Perplexity if found)
            if 'reddit_outbound_url' not in item:
                item['reddit_outbound_url'] = None

            # Store query and search URL
            item['perplexity_query'] = perplexity_query
            item['perplexity_search_url'] = perplexity_search_url

            if key in validation_data:
                val = validation_data[key]

                # Core validation fields
                item['validation_status'] = val.get('validation_status', 'unknown')
                item['item_type'] = val.get('item_type', 'news')
                item['perplexity_reason'] = val.get('reason', '')
                
                # New fields from improved prompt
                item['claim_summary'] = val.get('claim_summary')
                item['key_entities'] = val.get('key_entities', [])
                item['time_relevance'] = val.get('time_relevance', 'unclear')
                item['validation_confidence'] = val.get('confidence', 0.0)

                # Process sources - filter out Reddit URLs
                raw_sources = val.get('sources', [])
                raw_citations = val.get('citations', [])

                # Convert to StructuredSource format and dedupe
                structured_sources = []
                for src in raw_sources:
                    if isinstance(src, dict) and src.get('url'):
                        structured_sources.append(StructuredSource(
                            url=src.get('url', ''),
                            title=src.get('title'),
                            publisher=src.get('publisher'),
                            source_type=src.get('source_type', 'secondary'),
                            evidence=src.get('evidence')
                        ))

                # Deduplicate and filter Reddit URLs
                item['sources'] = deduplicate_sources(raw_citations, structured_sources)

                # Keep flat citations list for backward compatibility
                item['perplexity_citations'] = [
                    url for url in raw_citations
                    if url and not is_reddit_url(url)
                ]

            else:
                item['validation_status'] = 'missing_in_response'
                item['item_type'] = 'unknown'
                item['perplexity_reason'] = ''
                item['sources'] = []
                item['perplexity_citations'] = []

        return items

    def _validate_batch(self, items: List[Dict]) -> List[Dict]:
        """
        Send a batch to Perplexity API for validation.

        Args:
            items: Batch of items to validate

        Returns:
            Items with validation fields added
        """
        if not items:
            return []

        # Build prompts
        system_prompt, user_prompt, query = build_validation_prompt(items)

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers=headers,
                timeout=60
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Perplexity API Error: {response.status_code} - {response.text}"
                )
                for item in items:
                    item['validation_status'] = 'api_error'
                    item['sources'] = []
                    item['perplexity_citations'] = []
                return items

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Use mixin method for JSON cleanup
            validation_data = self.safe_parse_json(content)
            if not validation_data or 'error' in validation_data:
                self.logger.error(
                    f"Failed to parse JSON from Perplexity response: {content[:200]}..."
                )
                for item in items:
                    item['validation_status'] = 'parse_error'
                    item['sources'] = []
                    item['perplexity_citations'] = []
                return items

            return self._merge_validation_results(items, validation_data, query)

        except Exception as e:
            self.logger.exception(f"Exception during Perplexity validation: {e}")
            for item in items:
                item['validation_status'] = 'exception'
                item['sources'] = []
                item['perplexity_citations'] = []

        return items

    # =========================================================================
    # Verification Acceptance Criteria (S2-08)
    # =========================================================================

    def _validate_acceptance_criteria(self, item: Dict) -> Dict:
        """
        Apply verification acceptance criteria.

        A story can only be marked 'verified' if:
        1. Reddit link check is 'ok' or 'redirect'
        2. At least one non-Reddit source exists
        3. The perplexity_reason is substantive (not "it's a discussion")

        Items failing criteria are downgraded to 'unverifiable'.
        """
        current_status = item.get('validation_status', 'unknown')

        # Only check items that Perplexity marked as verified
        if current_status != 'verified':
            return item

        # Criterion 1: Reddit link must be accessible
        link_check = item.get('reddit_link_check', {})
        link_status = link_check.get('status', 'error')

        if link_status not in ('ok', 'redirect'):
            self.logger.debug(
                f"Downgrading '{item.get('title', '')[:50]}': "
                f"Reddit link status is {link_status}"
            )
            item['validation_status'] = 'unverifiable'
            item['_downgrade_reason'] = f'reddit_link_{link_status}'
            return item

        # Criterion 2: Must have at least one non-Reddit source
        if self.strict_verification:
            sources = item.get('sources', [])
            if not has_valid_external_source(sources):
                self.logger.debug(
                    f"Downgrading '{item.get('title', '')[:50]}': "
                    f"No non-Reddit sources found"
                )
                item['validation_status'] = 'unverifiable'
                item['_downgrade_reason'] = 'no_external_sources'
                return item

        # Criterion 3: Reason must be substantive
        reason = item.get('perplexity_reason', '').lower()
        vague_patterns = [
            'trending on reddit',
            'discussion on reddit',
            'unable to verify',
            'cannot confirm',
            'no sources found'
        ]

        if any(pattern in reason for pattern in vague_patterns):
            self.logger.debug(
                f"Downgrading '{item.get('title', '')[:50]}': "
                f"Vague verification reason"
            )
            item['validation_status'] = 'unverifiable'
            item['_downgrade_reason'] = 'vague_reason'
            return item

        return item

    # =========================================================================
    # Main Processing
    # =========================================================================

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: validate items with comprehensive source extraction.

        Pipeline:
        1. Check Reddit link accessibility for each item
        2. Filter out inaccessible items (if configured)
        3. Validate in batches via Perplexity API
        4. Apply verification acceptance criteria
        5. Filter by status

        Args:
            items: List of raw feed items from Stage 1

        Returns:
            List of validated items (filtered to keep_statuses)
        """
        self.logger.info(f"Processing {len(items)} items")

        # Step 1: Check Reddit links
        if self.check_reddit_links:
            self.logger.info("Checking Reddit link accessibility...")
            for idx, item in enumerate(items):
                self._check_reddit_link(item)
                if idx < len(items) - 1:
                    self.rate_limit(0.5)  # Light rate limiting for HEAD requests

        # Step 2: Filter inaccessible items
        if self.drop_inaccessible:
            before_count = len(items)
            items = [
                item for item in items
                if item.get('reddit_link_check', {}).get('status') not in ('not_found', 'forbidden')
            ]
            dropped = before_count - len(items)
            if dropped > 0:
                self.logger.info(f"Dropped {dropped} inaccessible Reddit posts")

        if not items:
            self.logger.warning("No items remaining after link check filtering")
            return []

        # Step 3: Validate via Perplexity API
        self.logger.info(f"Validating {len(items)} items in batches of {self.batch_size}")
        validated_items = self.process_in_batches(
            items,
            self._validate_batch,
            rate_limit_seconds=self.default_rate_limit
        )

        # Step 4: Apply acceptance criteria
        self.logger.info("Applying verification acceptance criteria...")
        for item in validated_items:
            self._validate_acceptance_criteria(item)

        # Log downgrade stats
        downgrades = [i for i in validated_items if '_downgrade_reason' in i]
        if downgrades:
            reasons = {}
            for item in downgrades:
                reason = item.get('_downgrade_reason', 'unknown')
                reasons[reason] = reasons.get(reason, 0) + 1
            self.logger.info(f"Downgraded {len(downgrades)} items: {reasons}")

        # Step 5: Filter to keep only specified statuses
        final_list = [
            item for item in validated_items
            if item.get('validation_status') in self.keep_statuses
        ]

        self.logger.info(
            f"Validation complete. Kept {len(final_list)}/{len(validated_items)} items "
            f"with status in {self.keep_statuses}"
        )

        return final_list


def run_stage_2(input_file: str) -> None:
    """
    Execute Stage 2 fact-checking pipeline.

    Args:
        input_file: Path to Stage 1 output (1_raw_feed.json)
    """
    stage = Stage2FactCheck(input_file)
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
