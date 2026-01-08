"""
Prompt Template System for TrendFlow LLM Pipeline

Provides reusable, type-safe prompt templates with:
- System/user prompt separation for Claude, GPT, Perplexity
- Combined prompts for Gemini and other APIs
- JSON schema enforcement
- Context validation

Usage:
    from utils.prompt_templates import ViralityPromptTemplate

    template = ViralityPromptTemplate()
    result = template.render({"title": "Breaking News", "subreddit": "technology"})

    # For APIs with system prompt support
    system_msg = result.system
    user_msg = result.user

    # For APIs without system prompt support
    combined = result.combined
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from string import Template
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Core Types
# =============================================================================

@dataclass(frozen=True)
class PromptResult:
    """
    Immutable result of rendering a prompt template.

    Provides both separated and combined formats to support
    different API requirements.
    """
    system: Optional[str]
    user: str

    @property
    def combined(self) -> str:
        """Combined prompt for APIs that don't support system prompts (Gemini)."""
        if self.system:
            return f"{self.system}\n\n---\n\n{self.user}"
        return self.user

    def as_messages(self) -> List[Dict[str, str]]:
        """Format as OpenAI/Anthropic messages array."""
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": self.user})
        return messages

    def as_perplexity_messages(self) -> List[Dict[str, str]]:
        """Format for Perplexity API (system + user roles)."""
        return self.as_messages()

    def as_anthropic_params(self) -> Dict[str, Any]:
        """Format for Anthropic API (separate system param)."""
        params = {"messages": [{"role": "user", "content": self.user}]}
        if self.system:
            params["system"] = self.system
        return params


# =============================================================================
# Base Template Class
# =============================================================================

class PromptTemplate(ABC):
    """
    Abstract base class for LLM prompt templates.

    Subclasses define the prompt structure and required context variables.
    Templates use Python's string.Template for safe variable substitution.

    Example:
        class MyTemplate(PromptTemplate):
            _system_template = "You are a ${role}."
            _user_template = "Analyze this: ${content}"
            _required_vars = {"role", "content"}
            _json_schema = {"result": "<analysis>"}
    """

    # Subclasses override these
    _system_template: Optional[str] = None
    _user_template: str = ""
    _required_vars: Set[str] = set()
    _json_schema: Dict[str, Any] = {}
    _json_format_instruction: str = "Return ONLY valid JSON. Do not wrap in markdown code blocks."

    def __init__(self, include_json_instruction: bool = True):
        """
        Args:
            include_json_instruction: If True, append JSON schema instruction
                to the user prompt. Set False for non-JSON responses.
        """
        self.include_json_instruction = include_json_instruction

    @property
    def system_prompt(self) -> Optional[str]:
        """Raw system prompt template (may contain ${variables})."""
        return self._system_template

    @property
    def user_prompt(self) -> str:
        """Raw user prompt template (may contain ${variables})."""
        return self._user_template

    @property
    def json_schema(self) -> Dict[str, Any]:
        """Expected JSON output schema."""
        return self._json_schema

    @property
    def required_variables(self) -> Set[str]:
        """Set of variable names required in context."""
        return self._required_vars

    def get_schema_instruction(self) -> str:
        """Get JSON format instruction with schema embedded."""
        if not self._json_schema:
            return ""
        schema_str = json.dumps(self._json_schema, indent=2)
        return f"\n\n{self._json_format_instruction}\nExpected format:\n{schema_str}"

    def validate_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Validate that context contains all required variables.

        Returns:
            List of missing variable names (empty if valid)
        """
        missing = [var for var in self._required_vars if var not in context]
        return missing

    def render(self, context: Dict[str, Any]) -> PromptResult:
        """
        Render the template with the given context.

        Args:
            context: Dictionary of variable values

        Returns:
            PromptResult with rendered system/user prompts

        Raises:
            ValueError: If required variables are missing
        """
        missing = self.validate_context(context)
        if missing:
            raise ValueError(f"Missing required context variables: {missing}")

        # Render system prompt
        system = None
        if self._system_template:
            system = Template(self._system_template).safe_substitute(context)

        # Render user prompt
        user = Template(self._user_template).safe_substitute(context)

        # Append JSON instruction if enabled
        if self.include_json_instruction and self._json_schema:
            user = user + self.get_schema_instruction()

        return PromptResult(system=system, user=user)


# =============================================================================
# Prompt Builder Utility
# =============================================================================

class PromptBuilder:
    """
    Utility class for building prompts with additional features.

    Provides:
    - Batch context preparation
    - Debug logging
    - Context validation
    """

    def __init__(self, debug: bool = False):
        """
        Args:
            debug: If True, store rendered prompts for inspection
        """
        self.debug = debug
        self._last_rendered: Optional[PromptResult] = None

    @staticmethod
    def validate(template: PromptTemplate, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate context without rendering.

        Returns:
            Tuple of (is_valid, missing_variables)
        """
        missing = template.validate_context(context)
        return (len(missing) == 0, missing)

    def build(
        self,
        template: PromptTemplate,
        context: Dict[str, Any]
    ) -> PromptResult:
        """
        Build a prompt from template and context.

        Args:
            template: The prompt template to use
            context: Dictionary of variable values

        Returns:
            PromptResult with rendered prompts
        """
        result = template.render(context)
        if self.debug:
            self._last_rendered = result
            logger.debug(f"Rendered prompt - System: {len(result.system or '')} chars, User: {len(result.user)} chars")
        return result

    def build_batch_context(
        self,
        items: List[Dict[str, Any]],
        item_formatter: Callable[[Dict[str, Any], int], str],
        separator: str = "\n"
    ) -> str:
        """
        Format a list of items into a single context string.

        Useful for batch processing prompts like Stage 2.

        Args:
            items: List of item dictionaries
            item_formatter: Function(item, index) -> str
            separator: String to join formatted items

        Returns:
            Formatted string of all items
        """
        formatted = [item_formatter(item, idx) for idx, item in enumerate(items)]
        return separator.join(formatted)

    @staticmethod
    def format_items_simple(
        items: List[Dict[str, Any]],
        fields: List[str] = None,
        one_indexed: bool = True
    ) -> str:
        """
        Simple item formatter for common use cases.

        Args:
            items: List of items
            fields: Fields to include (default: title, url)
            one_indexed: Use 1-based indexing (default True for LLM clarity)

        Returns:
            Formatted string
        """
        fields = fields or ["title", "url"]
        lines = []
        for idx, item in enumerate(items):
            item_num = idx + 1 if one_indexed else idx
            parts = [f"Item {item_num}:"]
            for field in fields:
                value = item.get(field, "N/A")
                parts.append(f"{field.title()}: {value}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    @property
    def last_rendered(self) -> Optional[PromptResult]:
        """Get the last rendered prompt (debug mode only)."""
        return self._last_rendered


# =============================================================================
# Stage-Specific Templates
# =============================================================================

class ValidationPromptTemplate(PromptTemplate):
    """
    Stage 2: Fact-checking validation with Perplexity.

    Required context:
        - items_text: Formatted string of items to validate
    """

    _system_template = """You are a strict Fact-Checking Agent. Your job is to verify news items found on Reddit.

Verification Rules:
1. Check if items are based on real events, announcements, or research
2. Flag rumors, hallucinations, or misleading titles
3. Provide citations from authoritative sources (NOT Reddit)
4. Mark as 'unverifiable' if only Reddit sources are available

For each item, return a JSON object keyed by Item Number (e.g., 'Item 1')."""

    _user_template = """Verify these items:
${items_text}"""

    _required_vars = {"items_text"}

    _json_schema = {
        "Item 1": {
            "validation_status": "verified | debunked | unverifiable",
            "reason": "<explanation of verification result>",
            "citations": ["<url1>", "<url2>"]
        }
    }


class ViralityPromptTemplate(PromptTemplate):
    """
    Stage 3: Virality scoring with Gemini.

    Required context:
        - title: Post title
        - subreddit: Source subreddit
    """

    # Gemini uses combined prompt (no system message support)
    _system_template = None

    _user_template = """Analyze the virality potential of this Reddit post:
Title: ${title}
Subreddit: ${subreddit}

Factors to consider:
1. Hook strength - Does the title grab attention immediately?
2. Emotional engagement - Does it evoke curiosity, outrage, joy, or surprise?
3. Broad appeal vs niche - Will it resonate beyond the subreddit?

Provide a specific score and concrete reasoning."""

    _required_vars = {"title", "subreddit"}

    _json_schema = {
        "virality_score": "<int 0-100>",
        "reasoning": "<2-3 sentences with specific references to the title>"
    }


class CurationPromptTemplate(PromptTemplate):
    """
    Stage 4: Strategic curation with OpenAI GPT.

    Required context:
        - candidates_text: Formatted candidate stories
        - top_n: Number of stories to select
    """

    _system_template = """You are a Strategic Content Director. Select the top ${top_n} stories with the highest viral potential for social media (X, Instagram, Threads).

Selection Criteria:
- Strong emotional hooks that drive engagement
- Topic diversity (avoid selecting multiple stories about the same subject)
- Broad audience appeal across demographics
- Credible sources when available

For each selection, explain specifically why it will go viral."""

    _user_template = """Here are the top trending candidates:
${candidates_text}

Select exactly ${top_n} stories. Reference their candidate numbers."""

    _required_vars = {"candidates_text", "top_n"}

    _json_schema = {
        "selected_stories": [
            {
                "original_index": "<int - 1-based candidate number>",
                "rationale": "<specific reason this story will go viral>"
            }
        ]
    }


class SynthesisPromptTemplate(PromptTemplate):
    """
    Stage 5: Social content generation with Claude.

    Required context:
        - title: Story title
        - rationale: Why it will go viral
        - url: Source URL

    Optional context:
        - sources_text: Formatted source citations
    """

    _system_template = """You are an expert Social Media Manager creating engaging content for viral stories.

Content Guidelines:
- X/Threads: Punchy hooks under 280 chars, create urgency or curiosity
- Instagram: Visual-first, storytelling through carousel slides
- A/B Testing: Provide distinct tonal variations (e.g., provocative vs informative)
- Sources: Reference credible sources when available in the final slide"""

    _user_template = """Create social media content for this story:
Title: "${title}"
Rationale for Virality: "${rationale}"
URL: ${url}
${sources_text}

Requirements:
1. **X/Threads Post**: Two distinct tonal variations for A/B testing
2. **Instagram Carousel**: 5-7 slides following Hook → Narrative → CTA structure
3. **Instagram Caption**: Include relevant hashtags"""

    _required_vars = {"title", "rationale", "url"}

    _json_schema = {
        "x_post_a": "<variation A text, max 280 chars>",
        "x_post_b": "<variation B text, max 280 chars>",
        "x_tone_a": "<tone description, e.g., 'provocative'>",
        "x_tone_b": "<tone description, e.g., 'informative'>",
        "carousel_slides": [
            {"slide_number": 1, "text": "<hook slide>"},
            {"slide_number": 2, "text": "<narrative content>"},
            {"slide_number": 3, "text": "<call to action>"}
        ],
        "instagram_caption": "<caption with #hashtags>"
    }

    def render(self, context: Dict[str, Any]) -> PromptResult:
        """Override to handle optional sources_text."""
        if "sources_text" not in context:
            context = {**context, "sources_text": ""}
        return super().render(context)


class ImageGenerationPromptTemplate(PromptTemplate):
    """
    Stage 6: Hero image generation with Gemini Image.

    This template produces non-JSON output (image prompt).

    Required context:
        - story_summary: 1-2 sentence story context
        - scene_brief: Subject, setting, emotion description

    Optional context:
        - accent_color: Color accent for the image (default: contextual)
    """

    # Gemini combined prompt
    _system_template = None

    _user_template = """Create a professional hero image for this story.

Story: ${story_summary}

Scene: ${scene_brief}

Style Direction:
- Photorealistic editorial photography style
- Cinematic lighting with professional color grade
- Portrait orientation 4:5 aspect ratio (1080x1350)
- Modern editorial aesthetic with natural contrast
- Leave clean negative space in upper or lower third for text overlay
- Strong focal subject with clear narrative beat
${accent_instruction}

AVOID: cartoon, flat vector, isometric, comic outlines, infographic layout, stickers, watermarks, logos, embedded text, childish proportions, neon gaming aesthetics"""

    _required_vars = {"story_summary", "scene_brief"}
    _json_schema = {}  # No JSON output for image generation

    def __init__(self):
        # Disable JSON instruction for image prompts
        super().__init__(include_json_instruction=False)

    def render(self, context: Dict[str, Any]) -> PromptResult:
        """Override to handle optional accent_color."""
        accent = context.get("accent_color")
        if accent:
            context = {**context, "accent_instruction": f"- Color palette: neutral base with {accent} as accent"}
        else:
            context = {**context, "accent_instruction": ""}
        return super().render(context)


# =============================================================================
# Template Registry
# =============================================================================

class TemplateRegistry:
    """
    Registry for looking up templates by stage number.

    Usage:
        template = TemplateRegistry.get(stage=2)
        result = template.render(context)
    """

    _templates: Dict[int, type] = {
        2: ValidationPromptTemplate,
        3: ViralityPromptTemplate,
        4: CurationPromptTemplate,
        5: SynthesisPromptTemplate,
        6: ImageGenerationPromptTemplate,
    }

    @classmethod
    def get(cls, stage: int) -> Optional[PromptTemplate]:
        """Get template instance for a stage number."""
        template_class = cls._templates.get(stage)
        if template_class:
            return template_class()
        return None

    @classmethod
    def register(cls, stage: int, template_class: type) -> None:
        """Register a custom template for a stage."""
        cls._templates[stage] = template_class

    @classmethod
    def list_stages(cls) -> List[int]:
        """List all registered stage numbers."""
        return sorted(cls._templates.keys())


# =============================================================================
# Integration Mixin for StageBase
# =============================================================================

class PromptTemplateMixin:
    """
    Mixin for integrating prompt templates with StageBase.

    Provides:
    - Template-based prompt building
    - Context building helpers
    - Debug prompt storage

    Usage:
        class Stage2FactCheck(StageBase, PromptTemplateMixin, JSONCleanupMixin):
            prompt_template = ValidationPromptTemplate()
    """

    # Override in subclass
    prompt_template: Optional[PromptTemplate] = None
    debug_prompts: bool = False

    _prompt_builder: Optional[PromptBuilder] = None

    def _get_prompt_builder(self) -> PromptBuilder:
        """Lazy initialization of prompt builder."""
        if self._prompt_builder is None:
            self._prompt_builder = PromptBuilder(debug=self.debug_prompts)
        return self._prompt_builder

    def build_prompt(self, context: Dict[str, Any]) -> PromptResult:
        """
        Build prompt using the stage's template.

        Args:
            context: Variables for template substitution

        Returns:
            PromptResult with rendered prompts

        Raises:
            ValueError: If no template defined or missing context vars
        """
        if not self.prompt_template:
            raise ValueError(f"No prompt_template defined for {self.__class__.__name__}")

        return self._get_prompt_builder().build(self.prompt_template, context)

    def format_items_for_prompt(
        self,
        items: List[Dict[str, Any]],
        fields: List[str] = None
    ) -> str:
        """
        Format a list of items for inclusion in a prompt.

        Args:
            items: List of item dictionaries
            fields: Fields to include (default: title, url)

        Returns:
            Formatted string with one item per line
        """
        return PromptBuilder.format_items_simple(items, fields)

    def format_candidates_for_prompt(
        self,
        candidates: List[Dict[str, Any]],
        include_score: bool = True
    ) -> str:
        """
        Format candidates for curation prompt.

        Args:
            candidates: List of candidate items
            include_score: Include virality score if available

        Returns:
            Formatted candidate list
        """
        lines = []
        for idx, item in enumerate(candidates):
            parts = [f"Candidate {idx + 1}: {item.get('title', 'N/A')}"]
            parts.append(f"(Sub: {item.get('subreddit', 'unknown')}")
            if include_score and 'virality_score' in item:
                parts.append(f"Virality: {item.get('virality_score')}")
            parts[-1] += ")"
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def format_sources_for_prompt(
        self,
        sources: List[Dict[str, Any]],
        max_sources: int = 3
    ) -> str:
        """
        Format source citations for inclusion in prompt.

        Args:
            sources: List of source dictionaries with url, publisher, etc.
            max_sources: Maximum sources to include

        Returns:
            Formatted sources string or empty string if no sources
        """
        if not sources:
            return ""

        lines = ["Sources:"]
        for src in sources[:max_sources]:
            publisher = src.get('publisher', 'Unknown')
            url = src.get('url', '')
            lines.append(f"- {publisher}: {url}")
        return "\n".join(lines)

    def get_debug_prompt(self) -> Optional[PromptResult]:
        """Get last rendered prompt (if debug_prompts enabled)."""
        builder = self._get_prompt_builder()
        return builder.last_rendered
