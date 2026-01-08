"""
Design DNA Configuration Module v3.0

Editorial Infographic System for news visualization:
- Clean professional infographic style (NOT photorealistic, NOT cartoony)
- Geometric icons, flowcharts, arrows for storytelling
- Bold headlines with supporting visual elements
- Structured layouts: comparison, flow, hierarchy
- Muted professional palette with accent colors
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Import branding book for locked brand template
try:
    from branding_book import (
        get_brand_book,
        build_brand_compliant_prompt_section,
        get_accent_for_theme,
        detect_style_variant,
    )
    BRAND_BOOK_AVAILABLE = True
except ImportError:
    BRAND_BOOK_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Design DNA Constants v3.0 - Editorial Infographic Style
# =============================================================================

class VisualStyle(Enum):
    """Supported visual styles for image generation."""
    INFOGRAPHIC = "infographic"
    EDITORIAL = "editorial"
    DIAGRAM = "diagram"


class InfographicLayout(Enum):
    """Common infographic layout patterns."""
    COMPARISON = "comparison"      # Side-by-side A vs B
    FLOW = "flow"                  # Left-to-right or top-to-bottom progression
    HIERARCHY = "hierarchy"        # Importance/impact pyramid
    TIMELINE = "timeline"          # Sequential events
    HUB_SPOKE = "hub_spoke"        # Central concept with related items


@dataclass(frozen=True)
class CompositionSettings:
    """Image composition configuration for Instagram."""
    aspect_ratio: str = "4:5"
    width: int = 1080
    height: int = 1350
    framing: str = "portrait"
    header_zone: str = "top 20%"
    content_zone: str = "middle 60%"
    footer_zone: str = "bottom 20%"


@dataclass(frozen=True)
class InfographicStyle:
    """Core infographic style settings."""
    primary_style: str = "professional editorial infographic"
    icon_style: str = "clean geometric line icons"
    typography: str = "bold sans-serif headlines, clean body text"
    color_approach: str = "dark background with light text and color accents"
    layout: str = "structured sections with clear visual hierarchy"
    connectors: str = "clean arrows and flow lines connecting concepts"


# Default configuration instances
DEFAULT_COMPOSITION = CompositionSettings()
DEFAULT_STYLE = InfographicStyle()


# Color palettes for different themes
THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "tech_ai": {
        "background": "deep navy (#0a1628)",
        "primary_text": "white",
        "accent": "electric blue (#00d4ff)",
        "secondary": "soft cyan",
    },
    "biotech": {
        "background": "dark teal (#0d2b2b)",
        "primary_text": "white",
        "accent": "emerald green (#00ff88)",
        "secondary": "soft mint",
    },
    "space": {
        "background": "deep purple-black (#120a2a)",
        "primary_text": "white",
        "accent": "violet (#8b5cf6)",
        "secondary": "soft lavender",
    },
    "controversy": {
        "background": "dark slate (#1a1a2e)",
        "primary_text": "white",
        "accent": "amber orange (#ff9f1c)",
        "secondary": "warm yellow",
    },
    "education": {
        "background": "dark blue-gray (#1e2a3a)",
        "primary_text": "white",
        "accent": "bright teal (#14b8a6)",
        "secondary": "soft sky blue",
    },
    "default": {
        "background": "dark slate blue (#1a1f3c)",
        "primary_text": "white",
        "accent": "professional blue (#3b82f6)",
        "secondary": "soft gray-blue",
    },
}


# AVOID LIST - things that make infographics look unprofessional
AVOID_LIST: Tuple[str, ...] = (
    # Cartoon elements
    "cartoon characters",
    "cartoon faces",
    "smiling faces",
    "emoji-style icons",
    "childish illustrations",
    "bubbly rounded shapes",
    "comic book style",
    "mascot characters",
    # Photo elements
    "photorealistic",
    "photographs",
    "stock photos",
    "real human faces",
    # Unprofessional elements
    "neon colors",
    "gradient overload",
    "3D rendered objects",
    "glossy effects",
    "drop shadows",
    "bevels",
    "lens flares",
    "watermarks",
    "fake brand logos",
    # Layout issues
    "cluttered layout",
    "too much text",
    "illegible typography",
    "inconsistent icon styles",
)


# =============================================================================
# Story Analysis for Infographic Design
# =============================================================================

@dataclass
class StoryStructure:
    """Analyzed story structure for infographic layout."""
    headline: str
    key_entities: List[str]  # Companies, people, technologies
    main_concept: str
    supporting_points: List[str]
    layout_type: InfographicLayout
    theme: str
    visual_elements: List[str]  # Suggested icons/visuals


# Keywords for detecting story type and layout
LAYOUT_PATTERNS: Dict[InfographicLayout, List[str]] = {
    InfographicLayout.COMPARISON: [
        "vs", "versus", "compared to", "better than", "beat",
        "alternative", "difference between", "pros and cons",
    ],
    InfographicLayout.FLOW: [
        "process", "how", "steps", "leads to", "results in",
        "causes", "enables", "transforms", "evolution",
    ],
    InfographicLayout.TIMELINE: [
        "years", "after", "before", "history", "since",
        "timeline", "evolution", "progress", "journey",
    ],
    InfographicLayout.HUB_SPOKE: [
        "partnership", "collaboration", "combines", "integrates",
        "connects", "brings together", "merger", "alliance",
    ],
    InfographicLayout.HIERARCHY: [
        "most important", "key", "top", "critical", "impact",
        "significance", "implications", "what this means",
    ],
}

THEME_KEYWORDS: Dict[str, List[str]] = {
    # Check more specific themes FIRST (order matters in _detect_theme)
    "controversy": ["lawsuit", "scandal", "controversy", "debate", "concern",
                    "risk", "warning", "problem", "crisis", "ethical", "ban",
                    "regulation", "safety", "dangerous", "threat", "fear"],
    "space": ["nasa", "space", "rocket", "mars", "moon", "asteroid",
              "satellite", "orbit", "astronaut", "telescope", "cosmic",
              "galaxy", "neowise", "spacex", "starship", "webb"],
    "education": ["school", "university", "classroom", "learning", "student",
                  "teacher", "education", "tutor", "academic", "harvard", 
                  "study", "research", "professor", "college", "taught"],
    "biotech": ["gene", "crispr", "dna", "embryo", "medical", "health",
                "biotech", "genomics", "therapy", "treatment", "vaccine",
                "disease", "clinical", "patient", "drug", "pharma"],
    # tech_ai is the fallback for general tech stories
    "tech_ai": ["ai", "artificial intelligence", "robot", "machine learning",
                "neural", "gpt", "llm", "claude", "deepmind", "openai",
                "chatgpt", "gemini", "automation", "algorithm"],
}

VISUAL_ELEMENT_KEYWORDS: Dict[str, List[str]] = {
    "robot icon": ["robot", "robotics", "humanoid", "boston dynamics"],
    "brain/AI icon": ["ai", "intelligence", "neural", "thinking", "deepmind"],
    "DNA helix": ["gene", "dna", "crispr", "genomics", "embryo"],
    "graduation cap": ["education", "university", "academic", "student"],
    "rocket icon": ["space", "nasa", "launch", "rocket"],
    "star icon": ["discover", "stars", "astronomy", "telescope"],
    "handshake icon": ["partnership", "collaboration", "alliance", "merger"],
    "chart/graph icon": ["study", "research", "proves", "data", "statistics"],
    "warning triangle": ["risk", "concern", "warning", "danger", "ethical"],
    "lightbulb icon": ["innovation", "breakthrough", "idea", "invention"],
    "globe icon": ["global", "world", "international", "worldwide"],
    "clock icon": ["time", "years", "after", "since", "timeline"],
}


def _detect_layout(text: str) -> InfographicLayout:
    """Detect best infographic layout based on story content."""
    text_lower = text.lower()

    scores = {}
    for layout, keywords in LAYOUT_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[layout] = score

    # Default to hub_spoke for partnership/announcement stories
    best_layout = max(scores, key=scores.get) if max(scores.values()) > 0 else InfographicLayout.HUB_SPOKE
    return best_layout


def _detect_theme(text: str) -> str:
    """Detect story theme for color palette selection based on keyword scoring."""
    text_lower = text.lower()

    # Score each theme by counting keyword matches
    scores = {}
    for theme, keywords in THEME_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[theme] = score
    
    # Return theme with highest score (if any matches)
    if max(scores.values(), default=0) > 0:
        return max(scores, key=scores.get)

    return "default"


def _extract_visual_elements(text: str) -> List[str]:
    """Extract suggested visual elements based on story content."""
    text_lower = text.lower()
    elements = []

    for element, keywords in VISUAL_ELEMENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            elements.append(element)

    # Always include at least one element
    if not elements:
        elements = ["abstract geometric shapes"]

    return elements[:5]  # Limit to 5 elements


def _extract_entities(title: str) -> List[str]:
    """Extract key entities (companies, technologies) from title."""
    # Common tech entities to look for
    known_entities = [
        "Google", "DeepMind", "Boston Dynamics", "OpenAI", "Microsoft",
        "Apple", "Meta", "Amazon", "Tesla", "SpaceX", "NASA", "Harvard",
        "AI", "GPT", "ChatGPT", "Claude", "Gemini", "CRISPR",
    ]

    entities = []
    for entity in known_entities:
        if entity.lower() in title.lower():
            entities.append(entity)

    return entities[:4]  # Limit to 4 main entities


def analyze_story_for_infographic(
    title: str,
    carousel_slides: Optional[List[Dict]] = None
) -> StoryStructure:
    """
    Analyze story content to determine optimal infographic structure.

    Args:
        title: Story headline
        carousel_slides: Social media carousel content (for supporting points)

    Returns:
        StoryStructure with layout recommendation and visual elements
    """
    # Combine title with carousel content for analysis
    combined_text = title
    supporting_points = []

    if carousel_slides:
        for slide in carousel_slides[1:4]:  # Skip first slide (usually just title)
            slide_text = slide.get('text', '')
            combined_text += " " + slide_text
            # Extract key points from slides
            if slide_text and len(slide_text) > 10:
                # Get first line or sentence as a point
                point = slide_text.split('\n')[0].strip()
                if point and not point.startswith('•'):
                    supporting_points.append(point[:80])

    # Detect optimal layout
    layout = _detect_layout(combined_text)

    # Detect theme for color palette
    theme = _detect_theme(combined_text)

    # Extract visual elements
    visual_elements = _extract_visual_elements(combined_text)

    # Extract key entities
    entities = _extract_entities(title)

    # Clean headline
    headline = title
    headline = re.sub(r'^\s*\[[^\]]+\]\s*', '', headline)  # Remove [tags]
    headline = re.sub(r'\s*\|.*$', '', headline)  # Remove | suffix
    if len(headline) > 80:
        headline = headline[:77] + "..."

    # Determine main concept
    main_concept = f"explaining {entities[0] if entities else 'the story'}"

    return StoryStructure(
        headline=headline,
        key_entities=entities,
        main_concept=main_concept,
        supporting_points=supporting_points[:3],
        layout_type=layout,
        theme=theme,
        visual_elements=visual_elements,
    )


# =============================================================================
# Infographic Prompt Builder v3.0
# =============================================================================

@dataclass
class InfographicPromptBuilder:
    """
    Builder for professional editorial infographic prompts.

    Creates prompts that generate clean, story-driven infographics
    with flowcharts, icons, and text - NOT photorealistic images.
    """
    style: InfographicStyle = field(default_factory=lambda: DEFAULT_STYLE)
    composition: CompositionSettings = field(default_factory=lambda: DEFAULT_COMPOSITION)
    avoid_list: Tuple[str, ...] = AVOID_LIST

    def build_prompt(self, story: StoryStructure) -> str:
        """
        Build infographic generation prompt from analyzed story.

        Now includes locked brand template from branding_book for
        consistent Nano Banana Pro styling.

        Args:
            story: Analyzed story structure

        Returns:
            Complete prompt for infographic generation
        """
        palette = THEME_PALETTES.get(story.theme, THEME_PALETTES["default"])

        # Build the prompt in sections
        prompt_parts = [
            self._build_style_directive(),
        ]
        
        # Add locked brand template from branding book (if available)
        if BRAND_BOOK_AVAILABLE:
            prompt_parts.append(build_brand_compliant_prompt_section())
        
        prompt_parts.extend([
            self._build_layout_directive(story),
            self._build_content_directive(story),
            self._build_visual_elements_directive(story),
            self._build_color_directive(palette, story.theme),
            self._build_composition_directive(),
            self._build_avoid_directive(),
        ])

        return "\n\n".join(prompt_parts)

    def _build_style_directive(self) -> str:
        """Core style instructions."""
        return f"""Create a {self.style.primary_style} that explains a news story visually.

STYLE REQUIREMENTS:
- {self.style.icon_style} (NOT cartoon characters, NOT photorealistic)
- {self.style.typography}
- {self.style.connectors}
- Clean, modern, professional aesthetic like a McKinsey or business consulting presentation
- Flat design with subtle depth, no 3D effects"""

    def _build_layout_directive(self, story: StoryStructure) -> str:
        """Layout structure based on story type."""
        layout_instructions = {
            InfographicLayout.COMPARISON: """LAYOUT: Split comparison view
- Divide into two clear sections (left vs right or top vs bottom)
- Use contrasting but harmonious colors for each side
- Include VS or comparison symbol in center
- Show clear winner/difference with visual emphasis""",

            InfographicLayout.FLOW: """LAYOUT: Flow diagram
- Show progression from left-to-right or top-to-bottom
- Use arrows connecting each step/stage
- Each stage has an icon and brief label
- Clear start and end points""",

            InfographicLayout.TIMELINE: """LAYOUT: Timeline progression
- Horizontal or vertical timeline with marked points
- Key dates/milestones clearly labeled
- Icons representing each event
- Connected with a flowing line""",

            InfographicLayout.HUB_SPOKE: """LAYOUT: Hub and spoke diagram
- Central icon/concept in the middle
- Related concepts radiating outward
- Connecting lines showing relationships
- Partnership/collaboration visual (like handshake or merger symbol)""",

            InfographicLayout.HIERARCHY: """LAYOUT: Impact hierarchy
- Most important point at top, largest
- Supporting points below, progressively smaller
- Visual emphasis on key takeaway
- Clear top-to-bottom reading flow""",
        }

        return layout_instructions.get(story.layout_type, layout_instructions[InfographicLayout.HUB_SPOKE])

    def _build_content_directive(self, story: StoryStructure) -> str:
        """Content to include in the infographic."""
        entities_str = ", ".join(story.key_entities) if story.key_entities else "the main subject"

        content = f"""CONTENT TO VISUALIZE:
- HEADLINE: "{story.headline}"
- KEY ENTITIES: {entities_str}
- Show the relationship/story between these entities using icons and arrows"""

        if story.supporting_points:
            points_str = "\n".join(f"  • {p}" for p in story.supporting_points)
            content += f"\n- KEY POINTS to represent visually:\n{points_str}"

        return content

    def _build_visual_elements_directive(self, story: StoryStructure) -> str:
        """Specific visual elements to include."""
        elements_str = ", ".join(story.visual_elements)

        return f"""VISUAL ELEMENTS:
- Include these icon types: {elements_str}
- Use clean geometric line icons (single color, simple shapes)
- Icons should be consistent style throughout
- Add subtle connecting arrows or lines between related concepts
- Include a clear visual focal point"""

    def _build_color_directive(self, palette: Dict[str, str], theme: str = "default") -> str:
        """Color scheme instructions with AI-selected accent based on story context."""
        # Build available accents list from branding book
        accent_options = ""
        suggested_accent = palette.get('accent', 'cyan (#22d3ee)')
        
        if BRAND_BOOK_AVAILABLE:
            try:
                brand_book = get_brand_book()
                accent_list = []
                for key, color in brand_book.accent_palette.items():
                    usage = ", ".join(color.best_for[:2]) if color.best_for else ""
                    accent_list.append(f"  • {color.name} ({color.hex}) — best for: {usage}")
                accent_options = "\n".join(accent_list)
                
                # Get suggested accent for this theme
                brand_accent = get_accent_for_theme(theme)
                suggested_accent = f"{brand_accent.name} ({brand_accent.hex})"
            except Exception:
                pass
        
        return f"""COLOR PALETTE (Brand-Compliant):
- Background: dark charcoal (#1e1e1e to #252525) - SOLID, no gradients
- Primary text: white
- Body text must remain white

ACCENT COLOR SELECTION (choose ONE based on story context):
{accent_options if accent_options else '''  • Lime (#a3e635) — best for: tech, growth
  • Cyan (#22d3ee) — best for: AI, digital
  • Coral (#fb7185) — best for: health, biotech
  • Amber (#fbbf24) — best for: warning, controversy
  • Violet (#a78bfa) — best for: space, science
  • Sky (#38bdf8) — best for: education, trust
  • Emerald (#34d399) — best for: environment, finance'''}

Suggested for this story: {suggested_accent}

IMPORTANT: Choose the accent color that BEST MATCHES the story's emotional tone and subject matter.
Do NOT default to cyan/teal for every infographic. Use the full palette for visual variety.
Use accent color ONLY for headers, icons, and callouts. Never use multiple accent colors."""

    def _build_composition_directive(self) -> str:
        """Composition and framing."""
        return f"""COMPOSITION:
- Aspect ratio: {self.composition.aspect_ratio} (portrait, Instagram-optimized)
- {self.composition.header_zone}: Bold headline text
- {self.composition.content_zone}: Main infographic content (icons, flowchart, diagram)
- {self.composition.footer_zone}: Key takeaway or call-to-action area
- Leave clean margins, don't crowd the edges"""

    def _build_avoid_directive(self) -> str:
        """Things to avoid."""
        avoid_str = ", ".join(self.avoid_list[:12])
        return f"""AVOID:
{avoid_str}

DO NOT include any cartoon characters, human faces, or photorealistic elements.
This should look like a professional business infographic, not a children's illustration."""

    def get_aspect_ratio(self) -> str:
        """Get aspect ratio string."""
        return self.composition.aspect_ratio

    def get_dimensions(self) -> Tuple[int, int]:
        """Get target dimensions (width, height)."""
        return (self.composition.width, self.composition.height)


# =============================================================================
# Convenience Functions
# =============================================================================

def build_infographic_prompt_from_item(item: Dict) -> str:
    """
    Build infographic prompt from a Stage 5 item.

    Main entry point for Stage 6 visual generation.

    Args:
        item: Item dict from Stage 5 with social_drafts

    Returns:
        Complete infographic prompt
    """
    title = item.get('title', '')

    # Get carousel slides for context
    social_drafts = item.get('social_drafts', {})
    carousel_slides = social_drafts.get('carousel_slides', [])

    # Analyze story structure
    story = analyze_story_for_infographic(title, carousel_slides)

    # Build prompt
    builder = InfographicPromptBuilder()
    return builder.build_prompt(story)


# Legacy compatibility - redirect old function to new one
def build_image_prompt_from_item(item: Dict) -> str:
    """Legacy function - redirects to infographic prompt builder."""
    return build_infographic_prompt_from_item(item)


# =============================================================================
# Legacy Compatibility Exports
# =============================================================================

# Legacy dataclass for backward compatibility
@dataclass
class SceneElements:
    """Legacy scene elements - maintained for backward compatibility."""
    subject: str
    setting: str
    emotion: str
    action: Optional[str] = None
    visual_metaphor: Optional[str] = None


# Legacy style class alias
@dataclass(frozen=True)
class StyleDNA:
    """Legacy style DNA - maintained for backward compatibility."""
    primary_style: str = "professional editorial infographic"
    lighting: str = "clean flat lighting"
    color_grade: str = "professional muted palette"
    detail_level: str = "clean geometric"
    texture: str = "flat design"
    mood: str = "professional informative"


# Keep old names for backward compatibility with stage_6_visuals.py
DesignDNAPromptBuilder = InfographicPromptBuilder
default_prompt_builder = InfographicPromptBuilder()


def summarize_story_context(title: str, rationale: Optional[str] = None,
                            carousel_slides: Optional[List[Dict]] = None) -> str:
    """Legacy function - now part of story analysis."""
    story = analyze_story_for_infographic(title, carousel_slides)
    return story.headline


def infer_scene_elements(title: str, rationale: Optional[str] = None,
                         carousel_text: Optional[str] = None) -> SceneElements:
    """Legacy function - replaced by story analysis."""
    story = analyze_story_for_infographic(title, None)
    return SceneElements(
        subject=story.key_entities[0] if story.key_entities else "subject",
        setting="infographic",
        emotion="professional",
        action=None
    )


def get_accent_color(title: str) -> str:
    """Get accent color based on story theme."""
    theme = _detect_theme(title)
    palette = THEME_PALETTES.get(theme, THEME_PALETTES["default"])
    return palette["accent"]
