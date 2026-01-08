"""
Stage 5: Content Synthesis

Generates social media copy using Claude Sonnet 4.5.
"""

import logging
from typing import List, Dict
from anthropic import Anthropic

from utils.stage_base import StageBase, JSONCleanupMixin

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-5-20250929"


class Stage5Synthesis(StageBase, JSONCleanupMixin):
    """
    Stage 5: Content Synthesis

    Generates social media copy for X, Threads, Instagram using Claude.
    Includes single posts, carousel slides, and A/B test variations.
    """

    stage_number = 5
    stage_name = "Content Synthesis"
    output_filename = "5_social_drafts.json"
    default_rate_limit = 1.0
    api_key_env_var = "ANTHROPIC_API_KEY"

    def __init__(self, input_file: str):
        """
        Args:
            input_file: Path to Stage 4 output (4_curated_top5.json)
        """
        super().__init__(input_file)
        self.client = None

    def _init_client(self) -> bool:
        """Initialize Anthropic client with API key."""
        api_key = self.get_api_key()
        if not api_key:
            return False

        self.client = Anthropic(api_key=api_key)
        return True

    def _get_system_prompt(self) -> str:
        """Return the system prompt for content synthesis."""
        return """You are an expert Social Media Manager writing high-performing, non-misleading social content from provided inputs.

Hard rules:
- Do not add facts that are not in the provided story inputs.
- Do not claim certainty if the input is uncertain.
- Avoid defamation and avoid medical/legal advice.
- Keep outputs platform-appropriate and avoid slurs/hate.

Style:
- Prioritize clarity, punch, and curiosity.
- Use plain language; avoid jargon.
- Ensure the hook is in the first line.

Output must be ONLY valid JSON and match the schema exactly."""

    def _build_user_prompt(self, item: Dict) -> str:
        """Build user prompt for social copy generation."""
        title = item.get('title', '')
        rationale = item.get('rationale', '')
        url = item.get('url', '')
        
        # Build sources text if available
        sources = item.get('sources', [])
        if sources:
            sources_lines = []
            for src in sources[:3]:  # Limit to top 3 sources
                if isinstance(src, dict):
                    pub = src.get('publisher', src.get('url', 'Unknown'))
                    sources_lines.append(f"- {pub}")
            sources_text = "\n".join(sources_lines) if sources_lines else "None provided"
        else:
            sources_text = "None provided"

        return f"""Create social media content for this story:
Title: "{title}"
Rationale for virality: "{rationale}"
URL: {url}
Sources (if any):
{sources_text}

Requirements:
1) X/Threads: two distinct tonal variations (A/B) under 280 chars each.
2) Instagram carousel: 5–7 slides (Slide 1 hook, Slides 2–N value/narrative, last slide CTA).
3) Instagram caption: include relevant hashtags.
4) If sources exist, reference "verified by <publisher/domain>" on the last slide without adding new claims.

Output JSON schema:
{{
    "x_post_a": "<text for option A>",
    "x_post_b": "<text for option B>",
    "x_tone_a": "<tone description>",
    "x_tone_b": "<tone description>",
    "carousel_slides": [
        {{"slide_number": 1, "text": "..."}},
        {{"slide_number": 2, "text": "..."}}
    ],
    "instagram_caption": "<caption with hashtags>"
}}"""

    def _generate_social_copy(self, item: Dict) -> Dict:
        """
        Generate social copy for a single item.

        Args:
            item: Curated item with title, rationale, url

        Returns:
            Item with 'social_drafts' field added
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(item)

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=2048,  # Increased for 7 slides + caption
                system=system_prompt,  # Proper system parameter
                messages=[{
                    "role": "user",
                    "content": user_prompt
                }],
                temperature=0.8,  # Creative but controlled
            )

            content = response.content[0].text

            # Use mixin for JSON cleanup
            data = self.safe_parse_json(
                content,
                default={"error": "json_parse_error", "raw_content": content}
            )

            item['social_drafts'] = data
            return item

        except Exception as e:
            self.logger.error(f"Claude generation failed for {item.get('id')}: {e}")
            item['social_drafts'] = {"error": str(e)}
            return item

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: generate social copy for each item.

        Args:
            items: List of curated items from Stage 4

        Returns:
            List of items with social_drafts added
        """
        # Initialize client
        if not self._init_client():
            self.logger.error("Anthropic client not available.")
            return items

        processed_items = []

        for idx, item in enumerate(items):
            self.log_progress(idx + 1, len(items), f"Generating content...")

            processed_item = self._generate_social_copy(item)
            processed_items.append(processed_item)

            # Rate limiting between API calls (skip last)
            if idx < len(items) - 1:
                self.rate_limit()

        return processed_items


def run_stage_5(input_file: str) -> None:
    """
    Execute Stage 5 synthesis pipeline.

    Args:
        input_file: Path to Stage 4 output (4_curated_top5.json)
    """
    stage = Stage5Synthesis(input_file)
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
