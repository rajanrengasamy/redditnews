"""
Stage 3: Trend Scoring

Analyzes virality potential using Google Gemini AI + Google Trends data.
"""

import logging
from typing import List, Dict

from google import genai
from google.genai import types

from utils.stage_base import StageBase, JSONCleanupMixin
from utils.google_trends import score_item_with_trends

logger = logging.getLogger(__name__)

GEMINI_MODEL_NAME = "gemini-3-flash-preview"


class Stage3TrendScoring(StageBase, JSONCleanupMixin):
    """
    Stage 3: Analyze virality potential using Gemini AI.

    Scores each verified item for virality potential and ranks results.
    """

    stage_number = 3
    stage_name = "Trend Scoring"
    output_filename = "3_ranked_trends.json"
    default_rate_limit = 1.0
    api_key_env_var = "GOOGLE_API_KEY"
    api_key_fallback = "GOOGLE_AI_API_KEY"

    THINKING_BUDGET = 1024

    def __init__(self, input_file: str, filter_verified_only: bool = True):
        """
        Args:
            input_file: Path to Stage 2 output (2_validated_facts.json)
            filter_verified_only: If True, only process items with 'verified' status
        """
        super().__init__(input_file)
        self.filter_verified_only = filter_verified_only
        self.client = None

    def _init_client(self) -> bool:
        """Initialize Gemini client with API key."""
        api_key = self.get_api_key()
        if not api_key:
            self.logger.warning("Google API key not found. Trend analysis will use default scores.")
            return False

        self.client = genai.Client(api_key=api_key)
        return True

    def _fetch_google_trends(self, item: Dict) -> Dict:
        """
        Fetch Google Trends data for an item.
        
        Returns:
            Dict with google_trends_score and trends metadata
        """
        title = item.get('title', '')
        try:
            score, trends_data = score_item_with_trends(title, rate_limit_seconds=0.5)
            return {
                'google_trends_score': score,
                'google_trends_data': trends_data
            }
        except Exception as e:
            self.logger.warning(f"Google Trends fetch failed: {e}")
            return {
                'google_trends_score': 0,
                'google_trends_data': {'trends_available': False, 'trends_error': str(e)}
            }

    def _build_virality_prompt(self, item: Dict, google_trends_score: int = 0) -> str:
        """Build prompt for virality analysis with explicit scoring rubric."""
        title = item.get('title', '')
        subreddit = item.get('subreddit', '')
        
        # Include Google Trends context if available
        trends_context = ""
        if google_trends_score > 0:
            trends_context = f"\nGoogle Trends Interest: {google_trends_score}/100 (real-time search interest signal)"
        
        return f"""You are a virality scoring analyst for social platforms (X, Instagram, Threads).
Score the post's viral potential from 0–100 using the rubric below.

Rubric (must follow):
- Hook Strength (0–40): curiosity, novelty, immediacy, contradiction, strong framing
- Emotion/Engagement (0–30): surprise, outrage, awe, humor, relatability
- Shareability (0–20): can it be summarized, memed, or debated quickly?
- Broad vs Niche (0–10): understandable outside the subreddit

Constraints:
- Do not invent facts beyond the title/subreddit.
- Consider Google Trends data as a signal of real-world interest if provided.
- Return ONLY valid JSON. No markdown.

Input:
Title: "{title}"
Subreddit: "{subreddit}"{trends_context}

Output JSON schema:
{{
  "virality_score": 0,
  "score_breakdown": {{
    "hook": 0,
    "emotion": 0,
    "shareability": 0,
    "breadth": 0
  }},
  "reasoning": "2–4 sentences grounded in the title wording",
  "confidence": 0.0,
  "risks": ["optional array of short risk notes (e.g., too niche, unclear claim)"]
}}"""

    def _analyze_virality(self, item: Dict, google_trends_score: int = 0) -> Dict:
        """
        Analyze virality for a single item using Gemini.

        Args:
            item: Item to analyze
            google_trends_score: Google Trends interest score (0-100)

        Returns:
            Dict with virality_score and reasoning
        """
        if not self.client:
            return {"virality_score": 0, "reasoning": "No API Key"}

        prompt = self._build_virality_prompt(item, google_trends_score)

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=self.THINKING_BUDGET
                    )
                )
            )

            # Use mixin for JSON cleanup
            return self.safe_parse_json(
                response.text,
                default={"virality_score": 0, "reasoning": "Parse error"}
            )

        except Exception as e:
            self.logger.warning(f"Gemini analysis failed for {item.get('id')}: {e}")
            return {"virality_score": 0, "reasoning": f"Error: {str(e)}"}

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: analyze virality for each item and rank results.

        Args:
            items: List of validated items from Stage 2

        Returns:
            List of items with virality scores, sorted by score descending
        """
        # Initialize client
        has_api = self._init_client()

        # Filter to verified items if configured
        if self.filter_verified_only:
            items_to_process = [i for i in items if i.get('validation_status') == 'verified']
            self.logger.info(f"Processing {len(items_to_process)} verified items (others skipped).")
        else:
            items_to_process = items
            self.logger.info(f"Processing all {len(items_to_process)} items.")

        processed_items = []

        for idx, item in enumerate(items_to_process):
            self.log_progress(idx + 1, len(items_to_process), item.get('title', '')[:30] + "...")

            # Fetch Google Trends data first
            trends_result = self._fetch_google_trends(item)
            google_trends_score = trends_result.get('google_trends_score', 0)
            item['google_trends_score'] = google_trends_score
            item['google_trends_data'] = trends_result.get('google_trends_data', {})

            # Analyze virality with trends context
            gemini_data = self._analyze_virality(item, google_trends_score)
            item['virality_score'] = gemini_data.get('virality_score', 0)
            item['virality_reasoning'] = gemini_data.get('reasoning', '')
            # New fields from improved prompt
            item['score_breakdown'] = gemini_data.get('score_breakdown', {})
            item['virality_confidence'] = gemini_data.get('confidence', 0.0)
            item['virality_risks'] = gemini_data.get('risks', [])


            processed_items.append(item)

            # Rate limit (only if we have API and not last item)
            if has_api and idx < len(items_to_process) - 1:
                self.rate_limit()

        # Sort by virality score descending
        processed_items.sort(key=lambda x: x.get('virality_score', 0), reverse=True)

        self.logger.info(f"Processed {len(processed_items)} items.")
        return processed_items


def run_stage_3(input_file: str) -> None:
    """
    Execute Stage 3 trend scoring pipeline.

    Args:
        input_file: Path to Stage 2 output (2_validated_facts.json)
    """
    stage = Stage3TrendScoring(input_file)
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
