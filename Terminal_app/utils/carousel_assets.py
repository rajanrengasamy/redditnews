"""
Carousel Asset Generation - Nano-Banana (Gemini 2.5 Flash Image) Integration

Generates AI-powered visual assets for carousel slides:
- Background images/patterns themed to story context
- Story-specific icons and illustrations
- Maintains McKinsey-style dark aesthetic with accent colors
"""

import base64
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from functools import lru_cache

from google import genai
from google.genai import types

from utils.api_clients import get_api_key, ServiceName

logger = logging.getLogger(__name__)

# Model ID for Gemini 2.5 Flash Image (nano-banana)
GEMINI_FLASH_IMAGE_MODEL = "gemini-2.5-flash-image"


@dataclass
class AssetConfig:
    """Configuration for carousel asset generation."""
    width: int = 1080
    height: int = 1350
    style: str = "editorial_dark"


# Prompt templates for consistent visual style
BACKGROUND_PROMPT_TEMPLATE = """Create a professional business presentation background for a story about: {topic}

CRITICAL RULES:
- NO text, words, letters, labels, or watermarks anywhere
- NO faces or human figures
- NO logos or brand marks

DESIGN REQUIREMENTS:
- Dark background (#0a0a0a to #1a1a1a)
- Subtle {accent_color} accent elements
- Clean, corporate aesthetic like McKinsey or Bloomberg presentations
- Portrait orientation (1080x1350)

VISUAL STYLE based on topic:
- For TECH/AI stories: clean circuit patterns, neural network nodes, subtle grid lines
- For SCIENCE stories: molecular structures, DNA helixes, abstract data visualizations
- For BUSINESS stories: elegant geometric shapes, subtle chart-like elements
- For HEALTH stories: organic flowing curves, cellular patterns
- For SPACE stories: subtle star fields, orbital paths, cosmic gradients

Create a sophisticated, minimal background that looks like a premium consulting firm's slide deck. The design should enhance readability of white text that will be overlaid."""


ICON_PROMPT_TEMPLATE = """Create a single geometric icon/illustration for a news story.

REQUIREMENTS:
- Style: Clean geometric line icon, editorial/professional
- Color: {accent_color} on transparent or very dark background
- Size: Suitable for 200x200 pixel display area
- Design: Abstract representation of the topic
- NO text, NO photorealistic elements, NO cartoon style

TOPIC: {topic}
ANGLE: {angle}

Create a simple, elegant icon that could appear in a professional infographic."""


# Mood mapping based on story angle
ANGLE_MOOD_MAP = {
    "outrage": "intense, urgent, attention-grabbing",
    "awe": "inspiring, expansive, wonder-inducing",
    "debate": "balanced, thought-provoking, nuanced",
    "utility": "practical, clean, informative",
    "meme": "playful, dynamic, energetic",
}

# Accent color names for prompts (matching carousel_templates.py AccentColor enum)
ACCENT_COLOR_NAMES = {
    "#a3e635": "lime green",
    "#22d3ee": "cyan blue",
    "#fbbf24": "amber yellow",
    "#f87171": "coral red",
    "#a78bfa": "violet purple",
    "#34d399": "emerald green",
    "#fb7185": "rose pink",
    "#38bdf8": "sky blue",
}


def _get_color_name(hex_color: str) -> str:
    """Get a descriptive color name from hex code."""
    return ACCENT_COLOR_NAMES.get(hex_color, "accent color")


def _get_mood(angle: str) -> str:
    """Get mood description from story angle."""
    return ANGLE_MOOD_MAP.get(angle.lower(), "professional, informative")


class CarouselAssetGenerator:
    """
    Generates AI-powered visual assets for carousel slides using Gemini 2.5 Flash Image.

    Features:
    - Background generation for slide types (title, content, CTA)
    - Icon generation for story themes
    - Caching to reduce API calls
    - Graceful fallback on failure
    """

    def __init__(self, config: Optional[AssetConfig] = None):
        """
        Initialize the asset generator.

        Args:
            config: Optional configuration for asset generation
        """
        self.config = config or AssetConfig()
        self._client: Optional[genai.Client] = None
        self._background_cache: Dict[str, bytes] = {}
        self._icon_cache: Dict[str, bytes] = {}

    @property
    def client(self) -> genai.Client:
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            api_key = get_api_key(ServiceName.GEMINI)
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate an image using Gemini 2.5 Flash Image.

        Args:
            prompt: The generation prompt

        Returns:
            PNG bytes if successful, None on failure
        """
        try:
            response = self.client.models.generate_content(
                model=GEMINI_FLASH_IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"],
                )
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return part.inline_data.data

            logger.warning("No image data in Gemini response")
            return None

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None

    def generate_background(
        self,
        topic: str,
        angle: str,
        accent_color: str,
        slide_type: str,
    ) -> Optional[bytes]:
        """
        Generate a themed background image for a carousel slide.

        Args:
            topic: Story topic/title
            angle: Story angle (outrage, awe, debate, utility, meme)
            accent_color: Hex color code for accent
            slide_type: Type of slide (title, content, cta)

        Returns:
            PNG bytes if successful, None on failure
        """
        # Check cache first (keyed by angle + slide_type for reuse)
        cache_key = f"{angle}_{slide_type}_{accent_color}"
        if cache_key in self._background_cache:
            logger.debug(f"Using cached background for {cache_key}")
            return self._background_cache[cache_key]

        # Build prompt
        prompt = BACKGROUND_PROMPT_TEMPLATE.format(
            accent_color=_get_color_name(accent_color),
            mood=_get_mood(angle),
            topic=topic[:100],  # Truncate long titles
            angle=angle,
            slide_type=slide_type,
        )

        logger.info(f"Generating background for {slide_type} slide (angle: {angle})")
        image_bytes = self._generate_image(prompt)

        if image_bytes:
            self._background_cache[cache_key] = image_bytes
            logger.info(f"Generated and cached background ({len(image_bytes)} bytes)")

        return image_bytes

    def generate_icon(
        self,
        topic: str,
        angle: str,
        accent_color: str,
    ) -> Optional[bytes]:
        """
        Generate a themed icon for a story.

        Args:
            topic: Story topic/title
            angle: Story angle
            accent_color: Hex color code for accent

        Returns:
            PNG bytes if successful, None on failure
        """
        # Check cache (keyed by angle for broad reuse)
        cache_key = f"icon_{angle}_{accent_color}"
        if cache_key in self._icon_cache:
            logger.debug(f"Using cached icon for {cache_key}")
            return self._icon_cache[cache_key]

        # Build prompt
        prompt = ICON_PROMPT_TEMPLATE.format(
            accent_color=_get_color_name(accent_color),
            topic=topic[:100],
            angle=angle,
        )

        logger.info(f"Generating icon for story (angle: {angle})")
        image_bytes = self._generate_image(prompt)

        if image_bytes:
            self._icon_cache[cache_key] = image_bytes
            logger.info(f"Generated and cached icon ({len(image_bytes)} bytes)")

        return image_bytes

    def generate_assets_for_story(
        self,
        title: str,
        angle: str,
        accent_color: str,
        slide_types: list[str],
    ) -> Dict[str, Optional[bytes]]:
        """
        Generate all assets for a single story's carousel.

        Args:
            title: Story title
            angle: Story angle
            accent_color: Hex color for accent
            slide_types: List of slide types to generate backgrounds for

        Returns:
            Dict mapping asset keys to PNG bytes (or None on failure)
        """
        assets = {}

        # Generate background for each unique slide type
        unique_types = set(slide_types)
        for slide_type in unique_types:
            key = f"bg_{slide_type}"
            assets[key] = self.generate_background(
                topic=title,
                angle=angle,
                accent_color=accent_color,
                slide_type=slide_type,
            )

        # Generate one icon per story
        assets["icon"] = self.generate_icon(
            topic=title,
            angle=angle,
            accent_color=accent_color,
        )

        return assets

    def clear_cache(self) -> None:
        """Clear all cached assets."""
        self._background_cache.clear()
        self._icon_cache.clear()
        logger.debug("Asset cache cleared")


def bytes_to_base64_data_url(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """
    Convert image bytes to a base64 data URL for embedding in HTML.

    Args:
        image_bytes: Raw image bytes
        mime_type: MIME type of the image

    Returns:
        Data URL string (e.g., "data:image/png;base64,...")
    """
    b64_data = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{mime_type};base64,{b64_data}"
