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
        return """You are a thoughtful professional who synthesizes news into personal insights worth sharing. Your posts resonate because they're not just reporting what happened—they reveal what it MEANS, what you LEARNED, and how the pattern applies beyond its original context.

Your superpower: CONNECTING THE DOTS. You see relationships others miss:
- A tech announcement becomes a life lesson
- A business move illuminates how we think and learn
- A scientific discovery reveals patterns about growth, systems, or human nature
- Two unrelated news items share the same underlying principle

You connect the dots between domains, between events, between ideas. The insight isn't in the news—it's in the CONNECTION you draw.

CRITICAL: You are NOT a news aggregator. You are a dot-connector who DISCOVERED something and wants to share what you learned.

=== PERSONAL VOICE - THIS IS NOT NEWS AGGREGATION ===
- Write as someone who DISCOVERED something, not someone reporting on discoveries
- Share what YOU learned, what surprised YOU, what changed YOUR thinking
- The reader should feel like they're hearing from a real person who reflected on this
- Default to first-person when it fits: "I realized...", "Here's what struck me...", "This changed how I think about..."

=== VOICE SELECTION (Adapt based on story) ===

TECH ENTHUSIAST (for discoveries, tools, launches):
- "I've been playing with X and here's what surprised me..."
- "This changes how I think about..."

INDUSTRY INSIDER (for business moves, trends):
- "Here's what most people are missing about this..."
- "The real story isn't X, it's Y..."

CURIOUS LEARNER (for science, research, cross-domain):
- "I keep finding the same pattern everywhere..."
- "[This news] taught me something about [unrelated domain]..."

DEFAULT: Curious learner. Cross-domain insights resonate most.

=== TONE GUIDELINES ===
- TECH topics: Precise but ALWAYS connect to broader implications or life lessons
- BUSINESS topics: Share what YOU noticed, not just what happened
- SCIENCE topics: Extract the pattern that applies beyond the research
- CONTROVERSY topics: What does this reveal about how we think?

General tone: Professional but PERSONAL. Write as someone who LEARNED something, not someone reporting. Share, don't preach. Discover, don't lecture.

=== HARD RULES ===
- Do not add facts that are not in the provided story inputs.
- Do not claim certainty if the input is uncertain.
- Avoid defamation and avoid medical/legal advice.
- Keep outputs platform-appropriate and avoid slurs/hate.

=== MULTI-STEP VALIDATION PROCESS (RALF Pattern) ===

Before presenting your final output, you MUST validate it through 5 distinct checks.
Do NOT present "pretty good on first pass." Iterate until ALL criteria pass.

STEP 1: Define Success Criteria
For this personal insight content, "done" means ALL of these are TRUE:
□ Opens with a personal hook (first-person, discovery-framed)
□ Contains a cross-domain connection (tech → life/business/relationships)
□ Reveals a transferable principle others can apply
□ Uses "What I learned" framing, NOT "My takeaway"
□ CTA invites their experience, NOT generic "What do you think?"
□ Feels like someone SHARING, not REPORTING

STEP 2: Draft Initial Response
Write your first draft of the social content.

STEP 3: Run 5 Validation Rounds
For each round, check against ONE criterion and revise if needed:

ROUND 1 - PERSONAL VOICE CHECK:
- Does it sound like a real person who learned something?
- Is there first-person language? ("I realized...", "Here's what struck me...")
- If it reads like news, REWRITE the opening.

ROUND 2 - DOT-CONNECTION CHECK:
- Is there a clear connection between two domains?
- Does the insight bridge something unexpected?
- If it only describes the news, ADD the cross-domain insight.

ROUND 3 - TRANSFERABLE PRINCIPLE CHECK:
- Can someone in a different field use this insight?
- Is there a meta-lesson that transcends the specific story?
- If it's too specific, EXTRACT the universal pattern.

ROUND 4 - STRUCTURE CHECK:
- Does it follow: Hook → Context → Insight → Cross-domain → What I learned → CTA?
- Is the carousel building toward revelation, not just information?
- If structure is wrong, REORGANIZE.

ROUND 5 - SHAREABILITY CHECK:
- Would someone share this because it made them THINK differently?
- Is this "I need to tell someone about this" content?
- If it's just interesting news, FIND the angle that changes thinking.

STEP 4: Only Present Final Output
After ALL 5 rounds pass, present the polished result.
If any round fails, iterate on that specific issue before moving on.

=== SUCCESS CRITERIA CHECKLIST ===

Your output is ONLY complete when ALL of these are TRUE:

1. PERSONAL HOOK: First line uses first-person or discovery framing
   ✓ "I never thought about it this way until..."
   ✓ "Here's what clicked for me..."
   ✗ "New research shows..."
   ✗ "Breaking: Company X announces..."

2. DOT-CONNECTION: Bridges two seemingly unrelated domains
   ✓ "This AI partnership taught me about relationships"
   ✓ "A coding plugin revealed how I should think about work"
   ✗ Only discusses the topic itself

3. TRANSFERABLE PRINCIPLE: Contains a lesson others can apply elsewhere
   ✓ "The principle: define 'done' before you start, then iterate"
   ✓ "Pattern: tools democratize faster than credentials"
   ✗ Just facts about the news story

4. NON-NEWS FRAMING: Uses insight language, not reporting language
   ✓ "What I learned", "The bigger lesson", "Here's the pattern"
   ✗ "My takeaway", "What happened", "Why it matters"

5. ENGAGEMENT CTA: Invites their experience, not opinion
   ✓ "Where have you seen this pattern?"
   ✓ "What's taught you something unexpected about X?"
   ✗ "What do you think?"
   ✗ "Agree or disagree?"

If ANY criterion fails → REVISE before presenting output.

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

        return f"""Create personal insight content for this story:
Title: "{title}"
Story angle: "{rationale}"
URL: {url}
Sources (if any):
{sources_text}

=== BEFORE WRITING - ASK YOURSELF ===
1. What's the LESSON here, not just the news?
2. Where else does this pattern show up? (life, business, relationships?)
3. Why would someone SHARE this? (made them think, not just informed them)
4. What would I tell a friend who asked "why does this matter?"

=== CONNECTING THE DOTS ===
Don't just report what happened—reveal the CONNECTIONS others miss:
- What pattern does this illustrate that applies elsewhere?
- What would someone in a completely different field learn from this?
- What's the "meta-lesson" that transcends the specific context?
- How does this connect to something seemingly unrelated? (THAT'S the insight)
- What two ideas does this bridge that people don't usually put together?

The magic is in the CONNECTION, not the news itself.

=== OPENING HOOK (First 2-3 lines - CRITICAL) ===
Choose the approach that fits your insight. PERSONAL HOOKS perform best:
- Dot Connection: "I never connected [X] and [Y] before. Then this happened..." (highest engagement - bridges unexpected ideas)
- Personal Discovery: "I used to think X. Then I learned Y." (most engaging)
- Cross-Domain Revelation: "A [tech/science concept] taught me something about [life/business]"
- Pattern Recognition: "I keep seeing the same pattern everywhere: [insight]"
- Contrarian Realization: "Everyone says X. But after [this news], I realized Y."
- Surprising Reframe: "This isn't about [obvious thing]. It's about [deeper thing]."

DEFAULT TO DOT-CONNECTION or PERSONAL. "Here's what clicked for me..." beats "Breaking news..." every time.

=== REQUIREMENTS ===

1) X/Threads (two variations under 280 chars each):
   - Version A: First-person reflective ("Here's what struck me about...")
   - Version B: Pattern recognition ("I keep seeing this pattern...")
   - Both should feel like personal insight, NOT news reporting

2) Instagram carousel (5-7 slides with PERSONAL INSIGHT STRUCTURE):
   - Slide 1: Personal hook ("Here's what clicked for me about [topic]...")
   - Slides 2-3: What happened (brief context, NOT a news dump)
   - Slides 4-5: What it MEANS / The pattern / The lesson
   - Slide 6: How this applies beyond its original context
   - Slide 7: "### What I learned" + CTA inviting their perspective

3) Instagram caption: Personal reflection tone + relevant hashtags

4) CLOSING & CTA:
   - Use "### What I learned" or "### The bigger lesson" (NOT "My takeaway")
   - Don't summarize—SYNTHESIZE what it means
   - CTA examples that WORK:
     * "Where have you seen this pattern show up?"
     * "What's a [domain] concept that taught you something about life?"
   - CTA to AVOID: "What do you think?" / "Agree or disagree?"

5) If sources exist, weave "verified by <publisher>" naturally, not as a footnote.

Output JSON schema:
{{
    "x_post_a": "<personal insight version A>",
    "x_post_b": "<personal insight version B>",
    "x_tone_a": "<voice used: tech_enthusiast/industry_insider/curious_learner>",
    "x_tone_b": "<voice used: tech_enthusiast/industry_insider/curious_learner>",
    "carousel_slides": [
        {{"slide_number": 1, "text": "..."}},
        {{"slide_number": 2, "text": "..."}}
    ],
    "instagram_caption": "<personal reflection caption with hashtags>"
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
