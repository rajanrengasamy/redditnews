"""
Branding Book Package

Nano Banana Pro brand specifications for Stage 6 visual generation.
"""

from .brand_loader import (
    BrandBook,
    BrandTemplate,
    AccentColor,
    StyleVariant,
    load_brand_book,
    get_brand_book,
    get_accent_for_theme,
    detect_style_variant,
    build_brand_compliant_prompt_section,
)

__all__ = [
    "BrandBook",
    "BrandTemplate", 
    "AccentColor",
    "StyleVariant",
    "load_brand_book",
    "get_brand_book",
    "get_accent_for_theme",
    "detect_style_variant",
    "build_brand_compliant_prompt_section",
]
