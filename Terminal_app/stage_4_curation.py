"""
Stage 4: Strategic Curation

Selects top 5 stories using OpenAI GPT-5.2 with rationale generation.
"""

import logging
from typing import List, Dict
from openai import OpenAI

from utils.stage_base import StageBase, JSONCleanupMixin

logger = logging.getLogger(__name__)

MODEL_NAME = "gpt-5.2"


class Stage4Curation(StageBase, JSONCleanupMixin):
    """
    Stage 4: Strategic Curation

    Selects top 5 stories from top 10 candidates using OpenAI GPT-5.2.
    Adds rationale explaining why each story will go viral.
    """

    stage_number = 4
    stage_name = "Strategic Curation"
    output_filename = "4_curated_top5.json"
    api_key_env_var = "OPENAI_API_KEY"

    def __init__(self, input_file: str, top_n: int = 5):
        """
        Args:
            input_file: Path to Stage 3 output (3_ranked_trends.json)
            top_n: Number of stories to select (default: 5)
        """
        super().__init__(input_file)
        self.top_n = top_n
        self.client = None

    def _init_client(self) -> bool:
        """Initialize OpenAI client with API key."""
        api_key = self.get_api_key()
        if not api_key:
            return False

        self.client = OpenAI(api_key=api_key)
        return True

    def _build_candidate_prompt(self, candidates: List[Dict]) -> str:
        """Build prompt content from candidate items."""
        prompt_content = "Here are the top trending candidates:\n"
        for i, item in enumerate(candidates):
            google_trends = item.get('google_trends_score', 0)
            trends_info = f", Trends: {google_trends}" if google_trends > 0 else ""
            prompt_content += (
                f"Candidate {i+1}: {item.get('title')} "
                f"(Sub: {item.get('subreddit')}, "
                f"Virality: {item.get('virality_score')}{trends_info})\n"
            )
        return prompt_content

    def _get_system_instruction(self) -> str:
        """Return the system instruction for curation."""
        return f"""You are a Strategic Content Director selecting stories for maximum viral engagement on X, Instagram, and Threads.

Selection rules:
1) Select exactly {self.top_n} stories.
2) Optimize for: strong hook, emotional pull, shareability, and broad appeal.
3) Enforce topic diversity: avoid picking multiple stories with the same core topic unless clearly distinct.
4) Prefer stories with credible external verification signals when available.

Output:
- Return ONLY valid JSON.
- Provide 'selected_stories' as a list of {self.top_n} objects with:
  - original_index (1-based candidate number)
  - rationale (2–4 sentences, specific about why it will perform)
  - angle (short label like "outrage", "awe", "debate", "utility", "meme")"""

    def _elaborate_rationale(self, candidates: List[Dict]) -> List[Dict]:
        """
        Call OpenAI to select top stories and generate rationale.

        Args:
            candidates: Top candidates to choose from

        Returns:
            List of selected items with rationale added
        """
        prompt_content = self._build_candidate_prompt(candidates)
        system_instruction = self._get_system_instruction()

        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=0.5,  # Lower temp for more consistent selection
            )

            content = response.choices[0].message.content

            # Use mixin for JSON cleanup
            data = self.safe_parse_json(content, default={})

            selected_stories = []
            for selection in data.get('selected_stories', []):
                idx = selection.get('original_index', 0) - 1  # 1-based to 0-based
                if 0 <= idx < len(candidates):
                    story = candidates[idx].copy()
                    story['rationale'] = selection.get('rationale', '')
                    story['angle'] = selection.get('angle', '')  # New field
                    selected_stories.append(story)

            return selected_stories if selected_stories else candidates[:self.top_n]

        except Exception as e:
            self.logger.error(f"OpenAI Curation failed: {e}")
            # Fallback: return top N without rationale
            return candidates[:self.top_n]

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: select top stories with rationale.

        Args:
            items: List of ranked items from Stage 3

        Returns:
            List of top curated items with rationale
        """
        # Ensure sorted by virality score
        items_sorted = sorted(
            items,
            key=lambda x: x.get('virality_score', 0),
            reverse=True
        )

        # Take top 10 as candidates for selection (2x buffer)
        candidates = items_sorted[:self.top_n * 2]

        self.logger.info(f"Selecting top {self.top_n} from {len(candidates)} candidates...")

        # Initialize client
        if not self._init_client():
            self.logger.warning("OpenAI client not available. Using fallback selection.")
            return candidates[:self.top_n]

        # Get curated selection with rationale
        curated_items = self._elaborate_rationale(candidates)

        self.logger.info(f"Selected {len(curated_items)} items for synthesis.")
        return curated_items


def run_stage_4(input_file: str) -> None:
    """
    Execute Stage 4 curation pipeline.

    Args:
        input_file: Path to Stage 3 output (3_ranked_trends.json)
    """
    stage = Stage4Curation(input_file)
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
