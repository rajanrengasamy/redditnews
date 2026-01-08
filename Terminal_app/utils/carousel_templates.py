"""
Carousel HTML Templates - McKinsey-Style Slide Generation

Creates professional editorial-style carousel slides for Instagram/Threads:
- Dark theme with accent colors
- Clean sans-serif typography
- Geometric layout with generous whitespace
- 1080x1350px portrait (4:5 aspect ratio)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class AccentColor(Enum):
    """Accent colors for carousel slides."""
    LIME = "#a3e635"
    CYAN = "#22d3ee"
    AMBER = "#fbbf24"
    CORAL = "#f87171"
    VIOLET = "#a78bfa"
    EMERALD = "#34d399"
    ROSE = "#fb7185"
    SKY = "#38bdf8"


# Map story angle to accent color
ANGLE_COLOR_MAP = {
    "outrage": AccentColor.CORAL,
    "awe": AccentColor.CYAN,
    "debate": AccentColor.AMBER,
    "utility": AccentColor.EMERALD,
    "meme": AccentColor.VIOLET,
}


@dataclass
class SlideContent:
    """Content for a single carousel slide."""
    slide_number: int
    total_slides: int
    slide_type: str  # 'title', 'content', 'cta'
    title: Optional[str] = None
    subtitle: Optional[str] = None
    points: Optional[List[str]] = None
    accent_color: str = AccentColor.LIME.value
    # AI-generated assets (nano-banana integration)
    background_image_data: Optional[str] = None  # Base64 data URL for background
    icon_image_data: Optional[str] = None  # Base64 data URL for icon


def get_base_styles(
    accent_color: str = AccentColor.LIME.value,
    background_image_data: Optional[str] = None,
) -> str:
    """
    Generate base CSS styles for carousel slides.

    McKinsey-style design principles:
    - Dark backgrounds with subtle gradients (or AI-generated images)
    - High contrast text for readability
    - Generous padding and whitespace
    - Clean geometric elements

    Args:
        accent_color: Hex color for accent elements
        background_image_data: Optional base64 data URL for AI background
    """
    # Use AI background if provided, otherwise fallback to gradient
    if background_image_data:
        background_css = f"""
            background-image: url({background_image_data});
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        """
    else:
        background_css = "background: linear-gradient(180deg, #1a1a1a 0%, #0d0d0d 100%);"

    return f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            width: 1080px;
            height: 1350px;
            {background_css}
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            color: #ffffff;
            padding: 60px;
            display: flex;
            flex-direction: column;
        }}

        .slide-indicator {{
            position: absolute;
            bottom: 40px;
            right: 60px;
            font-size: 16px;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 500;
            letter-spacing: 2px;
        }}

        .accent-line {{
            width: 80px;
            height: 4px;
            background: {accent_color};
            margin-bottom: 32px;
        }}

        .accent-dot {{
            width: 12px;
            height: 12px;
            background: {accent_color};
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .title {{
            font-size: 56px;
            font-weight: 700;
            line-height: 1.15;
            letter-spacing: -1px;
            margin-bottom: 24px;
        }}

        .subtitle {{
            font-size: 26px;
            font-weight: 400;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.75);
            max-width: 800px;
        }}

        .content-title {{
            font-size: 42px;
            font-weight: 600;
            line-height: 1.2;
            margin-bottom: 48px;
            color: rgba(255, 255, 255, 0.95);
        }}

        .point {{
            display: flex;
            align-items: flex-start;
            gap: 24px;
            margin-bottom: 48px;
        }}

        .point-text {{
            font-size: 32px;
            font-weight: 400;
            line-height: 1.6;
            color: rgba(255, 255, 255, 0.95);
            white-space: pre-line;
        }}

        .cta-title {{
            font-size: 48px;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 32px;
            text-align: center;
        }}

        .cta-subtitle {{
            font-size: 24px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.7);
            text-align: center;
        }}

        .cta-accent {{
            color: {accent_color};
        }}

        .footer {{
            position: absolute;
            bottom: 40px;
            left: 60px;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.4);
            letter-spacing: 1px;
        }}
    """


def generate_title_slide(content: SlideContent) -> str:
    """
    Generate HTML for the title/hook slide (Slide 1).

    Structure:
    - Accent line at top
    - Large bold title
    - Subtitle/hook below
    - Slide indicator at bottom
    """
    styles = get_base_styles(content.accent_color, content.background_image_data)

    # Escape HTML entities in text
    title = (content.title or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    subtitle = (content.subtitle or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{styles}</style>
</head>
<body>
    <div class="accent-line"></div>
    <h1 class="title">{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <div class="slide-indicator">{content.slide_number}/{content.total_slides}</div>
</body>
</html>"""


def generate_content_slide(content: SlideContent) -> str:
    """
    Generate HTML for content slides (Slides 2-N-1).

    Structure:
    - Section title (extracted from first line if starts with caps)
    - Key points with proper spacing
    - Slide indicator
    """
    styles = get_base_styles(content.accent_color, content.background_image_data)

    # Process points - split by newlines if text contains line breaks
    all_points = []
    for point in (content.points or []):
        # Split by double newlines or single newlines
        lines = [l.strip() for l in point.split('\n') if l.strip()]
        all_points.extend(lines)

    # Extract title if first line is all caps or ends with colon
    title_html = ""
    display_points = all_points
    if all_points:
        first_line = all_points[0]
        # Check if first line looks like a header (all caps, ends with colon, or short uppercase)
        if (first_line.isupper() or
            first_line.endswith(':') or
            (len(first_line) < 30 and first_line.replace(' ', '').replace('-', '').isupper())):
            title_text = first_line.rstrip(':')
            escaped_title = title_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            title_html = f'<h2 class="content-title">{escaped_title}</h2>'
            display_points = all_points[1:]  # Remove title from points

    # Build points HTML with proper spacing
    points_html = ""
    for point in display_points:
        if point:  # Skip empty lines
            escaped_point = point.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            points_html += f"""
        <div class="point">
            <div class="accent-dot"></div>
            <p class="point-text">{escaped_point}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{styles}</style>
</head>
<body>
    <div class="accent-line"></div>
    {title_html}
    <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; padding-top: 40px;">
        {points_html}
    </div>
    <div class="slide-indicator">{content.slide_number}/{content.total_slides}</div>
</body>
</html>"""


def generate_cta_slide(content: SlideContent) -> str:
    """
    Generate HTML for the CTA/closing slide (Final Slide).

    Structure:
    - Centered layout
    - Summary/CTA text
    - Follow prompt
    - Slide indicator
    """
    styles = get_base_styles(content.accent_color, content.background_image_data)

    title = (content.title or "Follow for more").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    subtitle = (content.subtitle or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{styles}</style>
</head>
<body style="justify-content: center; align-items: center;">
    <div class="accent-line" style="margin-bottom: 48px;"></div>
    <h1 class="cta-title">{title}</h1>
    <p class="cta-subtitle">{subtitle}</p>
    <div class="slide-indicator">{content.slide_number}/{content.total_slides}</div>
    <div class="footer">SWIPE FOR MORE</div>
</body>
</html>"""


def generate_slide_html(content: SlideContent) -> str:
    """
    Route to appropriate template based on slide type.
    """
    if content.slide_type == 'title':
        return generate_title_slide(content)
    elif content.slide_type == 'cta':
        return generate_cta_slide(content)
    else:
        return generate_content_slide(content)
