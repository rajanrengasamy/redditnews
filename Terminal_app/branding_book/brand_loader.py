"""
Brand Loader Module

Loads the Nano Banana Pro branding book specifications for Stage 6 visual generation.
Provides consistent brand enforcement across all generated assets.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Path to branding book directory
BRANDING_BOOK_DIR = Path(__file__).parent


@dataclass
class BrandTemplate:
    """Core brand template specifications."""
    background_color: str
    background_color_range: Tuple[str, str]
    frame_border_width: Tuple[int, int]
    frame_border_opacity: Tuple[float, float]
    frame_radius: Tuple[int, int]
    font_family: List[str]
    max_font_sizes: int
    title_position: str
    safe_zone_margin: int
    negative_space_range: Tuple[int, int]
    aspect_ratio: str
    width: int
    height: int


@dataclass
class AccentColor:
    """Single accent color specification."""
    hex: str
    name: str
    rgb: Tuple[int, int, int]
    best_for: List[str]


@dataclass
class StyleVariant:
    """Style variant for different content types."""
    name: str
    description: str
    prompt_instructions: List[str]
    best_for: List[str]


@dataclass
class BrandBook:
    """Complete brand book with all specifications."""
    template: BrandTemplate
    accent_palette: Dict[str, AccentColor]
    theme_mapping: Dict[str, str]
    style_variants: Dict[str, StyleVariant]
    variant_keywords: Dict[str, List[str]]
    negative_prompts: List[str]
    prompt_suffix: str


def _load_json_file(filename: str) -> Dict:
    """Load a JSON file from the branding book directory."""
    filepath = BRANDING_BOOK_DIR / filename
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Brand file not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}


def load_brand_template() -> BrandTemplate:
    """Load the core brand template specifications."""
    data = _load_json_file("brand_template.json")
    
    if not data:
        # Return defaults if file missing
        return BrandTemplate(
            background_color="#1e1e1e",
            background_color_range=("#1e1e1e", "#252525"),
            frame_border_width=(1, 2),
            frame_border_opacity=(0.15, 0.20),
            frame_radius=(20, 30),
            font_family=["Inter", "SF Pro", "Outfit"],
            max_font_sizes=3,
            title_position="centered in top 15-25%",
            safe_zone_margin=8,
            negative_space_range=(30, 40),
            aspect_ratio="4:5",
            width=1080,
            height=1350,
        )
    
    bg = data.get("background", {})
    frame = data.get("frame", {})
    typo = data.get("typography", {})
    spacing = data.get("spacing", {})
    comp = data.get("composition", {})
    
    return BrandTemplate(
        background_color=bg.get("color_range", ["#1e1e1e"])[0],
        background_color_range=tuple(bg.get("color_range", ["#1e1e1e", "#252525"])),
        frame_border_width=tuple(frame.get("border_width_px", [1, 2])),
        frame_border_opacity=tuple(frame.get("border_opacity_range", [0.15, 0.20])),
        frame_radius=tuple(frame.get("border_radius_px", [20, 30])),
        font_family=typo.get("font_family", ["Inter", "SF Pro", "Outfit"]),
        max_font_sizes=typo.get("max_sizes", 3),
        title_position=typo.get("title", {}).get("zone", "top_15_25_percent"),
        safe_zone_margin=spacing.get("safe_zone_margin_percent", 8),
        negative_space_range=tuple(spacing.get("negative_space_percent", [30, 40])),
        aspect_ratio=comp.get("aspect_ratio", "4:5"),
        width=comp.get("width_px", 1080),
        height=comp.get("height_px", 1350),
    )


def load_accent_palette() -> Tuple[Dict[str, AccentColor], Dict[str, str]]:
    """Load accent color palette and theme mapping."""
    data = _load_json_file("accent_palette.json")
    
    palette = {}
    for key, color_data in data.get("palette", {}).items():
        palette[key] = AccentColor(
            hex=color_data.get("hex", "#22d3ee"),
            name=color_data.get("name", key),
            rgb=tuple(color_data.get("rgb", [34, 211, 238])),
            best_for=color_data.get("best_for", []),
        )
    
    # Default palette if empty
    if not palette:
        palette = {
            "cyan": AccentColor("#22d3ee", "Electric Cyan", (34, 211, 238), ["default"]),
            "lime": AccentColor("#a3e635", "Lime Green", (163, 230, 53), ["tech"]),
            "amber": AccentColor("#fbbf24", "Warm Amber", (251, 191, 36), ["warning"]),
        }
    
    theme_mapping = data.get("theme_mapping", {"default": "cyan"})
    
    return palette, theme_mapping


def load_style_variants() -> Tuple[Dict[str, StyleVariant], Dict[str, List[str]]]:
    """Load style variants and their keyword triggers."""
    data = _load_json_file("style_variants.json")
    
    variants = {}
    for key, variant_data in data.get("variants", {}).items():
        variants[key] = StyleVariant(
            name=variant_data.get("name", key),
            description=variant_data.get("description", ""),
            prompt_instructions=variant_data.get("prompt_instructions", []),
            best_for=variant_data.get("best_for", []),
        )
    
    # Default variants if empty
    if not variants:
        variants = {
            "minimal": StyleVariant("Minimal", "Typography-first", [], []),
            "data_heavy": StyleVariant("Data-Heavy", "One hero viz", [], []),
            "quote_focused": StyleVariant("Quote-Focused", "Quote dominates", [], []),
        }
    
    keywords = data.get("variant_selection_keywords", {})
    
    return variants, keywords


def load_restrictions() -> Tuple[List[str], str]:
    """Load negative prompts and restrictions."""
    data = _load_json_file("restrictions.json")
    
    negative_prompts = []
    for category, items in data.get("negative_prompts", {}).items():
        if isinstance(items, list):
            negative_prompts.extend(items)
    
    prompt_suffix = data.get("prompt_suffix", "")
    
    # Default if empty
    if not negative_prompts:
        negative_prompts = [
            "light backgrounds", "gradients", "filled icons", "stock photos",
            "clutter", "tiny text", "logos", "watermarks"
        ]
    
    if not prompt_suffix:
        prompt_suffix = "AVOID: " + ", ".join(negative_prompts[:8]) + "."
    
    return negative_prompts, prompt_suffix


def load_brand_book() -> BrandBook:
    """
    Load the complete brand book with all specifications.
    
    This is the main entry point for Stage 6 to get brand compliance.
    
    Returns:
        BrandBook with all loaded specifications
    """
    template = load_brand_template()
    palette, theme_mapping = load_accent_palette()
    variants, variant_keywords = load_style_variants()
    negative_prompts, prompt_suffix = load_restrictions()
    
    return BrandBook(
        template=template,
        accent_palette=palette,
        theme_mapping=theme_mapping,
        style_variants=variants,
        variant_keywords=variant_keywords,
        negative_prompts=negative_prompts,
        prompt_suffix=prompt_suffix,
    )


def get_accent_for_theme(theme: str) -> AccentColor:
    """
    Get the accent color for a given theme.
    
    Args:
        theme: Theme key (e.g., 'tech_ai', 'biotech', 'controversy')
        
    Returns:
        AccentColor for the theme
    """
    palette, theme_mapping = load_accent_palette()
    color_key = theme_mapping.get(theme, theme_mapping.get("default", "cyan"))
    return palette.get(color_key, list(palette.values())[0])


def detect_style_variant(text: str) -> str:
    """
    Detect the best style variant based on content keywords.
    
    Args:
        text: Title or content to analyze
        
    Returns:
        Style variant key ('minimal', 'data_heavy', 'quote_focused')
    """
    _, keywords = load_style_variants()
    text_lower = text.lower()
    
    scores = {}
    for variant, kw_list in keywords.items():
        score = sum(1 for kw in kw_list if kw in text_lower)
        scores[variant] = score
    
    if max(scores.values(), default=0) > 0:
        return max(scores, key=scores.get)
    
    return "minimal"  # Default to minimal


def build_brand_compliant_prompt_section() -> str:
    """
    Build the brand compliance section for image prompts.
    
    Returns:
        String with brand template requirements for prompt insertion
    """
    template = load_brand_template()
    _, prompt_suffix = load_restrictions()
    
    return f"""BRAND TEMPLATE (LOCKED - MUST FOLLOW):
- Background: solid dark charcoal ({template.background_color} to {template.background_color_range[1]}) - NO gradients, NO patterns
- Frame: rounded rectangle border, {template.frame_border_width[0]}-{template.frame_border_width[1]}px at {int(template.frame_border_opacity[0]*100)}-{int(template.frame_border_opacity[1]*100)}% white opacity, radius {template.frame_radius[0]}-{template.frame_radius[1]}px
- Typography: geometric sans ({', '.join(template.font_family)}), max {template.max_font_sizes} sizes; title bold; WCAG AA 4.5:1 min contrast
- Icons: line-art only, stroke 2-3px, NO fills; use accent color
- Spacing: min {template.safe_zone_margin}% safe-zone margins; {template.negative_space_range[0]}-{template.negative_space_range[1]}% negative space; title centered in top 15-25%
- Must be readable at 100px thumbnail

{prompt_suffix}"""


# Singleton cache to avoid repeated file reads
_cached_brand_book: Optional[BrandBook] = None


def get_brand_book() -> BrandBook:
    """Get cached brand book (loads once per session)."""
    global _cached_brand_book
    if _cached_brand_book is None:
        _cached_brand_book = load_brand_book()
    return _cached_brand_book
