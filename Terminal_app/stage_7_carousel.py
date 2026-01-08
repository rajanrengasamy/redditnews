"""
Stage 7: Carousel Image Generation

Generates McKinsey-style carousel images from Stage 5 social_drafts:
- Renders carousel_slides text to professional PNG images
- 1080x1350px portrait format (4:5 aspect ratio for Instagram)
- Dark theme with accent colors based on story angle
- Outputs to session folder alongside Stage 6 assets
- Supports AI-generated backgrounds via nano-banana (Gemini 2.5 Flash Image)
"""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Load environment variables from .env files
from dotenv import load_dotenv

# Load from project root .env first, then Terminal_app specific
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")
load_dotenv(Path(__file__).parent / "projects.env")

from utils.stage_base import StageBase
from utils.carousel_templates import (
    SlideContent,
    AccentColor,
    ANGLE_COLOR_MAP,
    generate_slide_html,
)
from utils.carousel_renderer import render_all_slides, CarouselConfig
from utils.carousel_assets import (
    CarouselAssetGenerator,
    bytes_to_base64_data_url,
)

logger = logging.getLogger(__name__)


class Stage7Carousel(StageBase):
    """
    Stage 7: Carousel Image Generation

    Takes carousel_slides from Stage 5 social_drafts and renders them
    as professional McKinsey-style PNG images for Instagram/Threads.

    Features:
    - 1080x1350px portrait (4:5 ratio)
    - Dark theme with story-appropriate accent colors
    - Title slide, content slides, CTA slide structure
    - High quality 2x rendering for Retina displays
    """

    stage_number = 7
    stage_name = "Carousel Image Generation"
    output_filename = "7_carousel_manifest.json"
    default_rate_limit = 1.0  # Rate limit for Gemini API calls
    # API key is set conditionally in __init__ based on use_ai_backgrounds
    api_key_env_var = None
    api_key_fallback = None

    def __init__(
        self,
        input_file: str,
        session_dir: Optional[str] = None,
        use_ai_backgrounds: bool = True,
    ):
        """
        Args:
            input_file: Path to Stage 5 output (5_social_drafts.json)
            session_dir: Optional path to existing session folder (for --session mode)
            use_ai_backgrounds: If True, generate AI backgrounds using nano-banana
        """
        # Set API key requirement BEFORE calling super().__init__
        if use_ai_backgrounds:
            self.api_key_env_var = "GOOGLE_API_KEY"
            self.api_key_fallback = "GOOGLE_AI_API_KEY"

        super().__init__(input_file)
        self.session_dir = session_dir
        self.carousels_dir: Optional[str] = None
        self.timestamp: str = ""
        self.config = CarouselConfig()
        self.use_ai_backgrounds = use_ai_backgrounds
        self.asset_generator: Optional[CarouselAssetGenerator] = None

    def _setup_directories(self) -> str:
        """Create or locate carousel output directory."""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # If session_dir provided, use it; otherwise create new session folder
        if self.session_dir:
            # Validate session folder exists
            if not os.path.isdir(self.session_dir):
                raise ValueError(f"Session directory not found: {self.session_dir}")
            self.carousels_dir = os.path.join(self.session_dir, "carousels")
        else:
            # Create new session folder
            self.session_dir = os.path.join(self.output_dir, f"session_{self.timestamp}")
            self.carousels_dir = os.path.join(self.session_dir, "carousels")

        os.makedirs(self.carousels_dir, exist_ok=True)
        self.logger.info(f"Carousel output directory: {self.carousels_dir}")
        return self.timestamp

    @staticmethod
    def _sanitize_filename(title: str, max_length: int = 30) -> str:
        """Convert title to safe filename."""
        clean = re.sub(r'[^\w\s-]', '', title)
        clean = re.sub(r'\s+', '_', clean)
        return clean[:max_length].rstrip('_').lower()

    def _get_accent_color(self, item: Dict) -> str:
        """Determine accent color based on story angle."""
        angle = item.get('angle', '').lower()
        color_enum = ANGLE_COLOR_MAP.get(angle, AccentColor.LIME)
        return color_enum.value

    def _get_asset_generator(self) -> CarouselAssetGenerator:
        """Lazy initialization of the asset generator."""
        if self.asset_generator is None:
            self.asset_generator = CarouselAssetGenerator()
        return self.asset_generator

    def _generate_ai_assets(
        self,
        item: Dict,
        accent_color: str,
        slide_types: List[str],
    ) -> Dict[str, Optional[str]]:
        """
        Generate AI assets for a story using nano-banana.

        Args:
            item: Story item with title and angle
            accent_color: Hex color for accent
            slide_types: List of slide types needing backgrounds

        Returns:
            Dict mapping slide types to base64 data URLs
        """
        if not self.use_ai_backgrounds:
            return {}

        title = item.get('title', 'Untitled')
        angle = item.get('angle', 'default').lower()

        try:
            generator = self._get_asset_generator()
            raw_assets = generator.generate_assets_for_story(
                title=title,
                angle=angle,
                accent_color=accent_color,
                slide_types=slide_types,
            )

            # Convert bytes to base64 data URLs
            assets = {}
            for key, image_bytes in raw_assets.items():
                if image_bytes:
                    assets[key] = bytes_to_base64_data_url(image_bytes)
                else:
                    assets[key] = None

            return assets

        except Exception as e:
            self.logger.warning(f"AI asset generation failed, using fallback: {e}")
            return {}

    def _distribute_slides(
        self,
        carousel_slides: List[Dict],
        title: str,
        accent_color: str,
        ai_assets: Optional[Dict[str, Optional[str]]] = None,
    ) -> List[SlideContent]:
        """
        Convert raw carousel_slides to SlideContent objects with proper types.

        Structure:
        - Slide 1: Title (hook from slide 1 text)
        - Slides 2 to N-1: Content (2-3 points per slide)
        - Slide N: CTA (from last slide text)

        Args:
            carousel_slides: Raw slide data from Stage 5
            title: Story title
            accent_color: Hex color for accents
            ai_assets: Optional dict of AI-generated assets (bg_title, bg_content, bg_cta, icon)
        """
        if not carousel_slides:
            return []

        ai_assets = ai_assets or {}
        total_slides = len(carousel_slides)
        distributed: List[SlideContent] = []

        for idx, slide in enumerate(carousel_slides):
            slide_num = idx + 1
            slide_text = slide.get('text', '')

            if slide_num == 1:
                # Title slide: use text as hook/subtitle
                distributed.append(SlideContent(
                    slide_number=slide_num,
                    total_slides=total_slides,
                    slide_type='title',
                    title=title[:100] if len(title) > 100 else title,  # Truncate long titles
                    subtitle=slide_text,
                    accent_color=accent_color,
                    background_image_data=ai_assets.get('bg_title'),
                    icon_image_data=ai_assets.get('icon'),
                ))
            elif slide_num == total_slides:
                # CTA slide
                distributed.append(SlideContent(
                    slide_number=slide_num,
                    total_slides=total_slides,
                    slide_type='cta',
                    title=slide_text if len(slide_text) < 80 else "Follow for more",
                    subtitle="Tap to see more stories like this",
                    accent_color=accent_color,
                    background_image_data=ai_assets.get('bg_cta'),
                ))
            else:
                # Content slide: wrap text as a single point
                distributed.append(SlideContent(
                    slide_number=slide_num,
                    total_slides=total_slides,
                    slide_type='content',
                    points=[slide_text],
                    accent_color=accent_color,
                    background_image_data=ai_assets.get('bg_content'),
                ))

        return distributed

    def _generate_carousel_for_item(
        self,
        item: Dict,
        idx: int
    ) -> Optional[Dict]:
        """
        Generate carousel images for a single item.

        Args:
            item: Item with social_drafts containing carousel_slides
            idx: Item index for filename generation

        Returns:
            Manifest entry with carousel metadata, or None on failure
        """
        item_id = item.get('id', f'item_{idx}')
        title = item.get('title', 'Untitled')
        social_drafts = item.get('social_drafts', {})
        carousel_slides = social_drafts.get('carousel_slides', [])

        if not carousel_slides:
            self.logger.warning(f"No carousel_slides for {item_id}, skipping")
            return None

        # Get accent color based on story angle
        accent_color = self._get_accent_color(item)

        # Determine slide types for AI asset generation
        total_slides = len(carousel_slides)
        slide_types = []
        for i in range(total_slides):
            if i == 0:
                slide_types.append('title')
            elif i == total_slides - 1:
                slide_types.append('cta')
            else:
                slide_types.append('content')

        # Generate AI assets using nano-banana (if enabled)
        ai_assets = self._generate_ai_assets(item, accent_color, slide_types)
        if ai_assets:
            self.logger.info(f"Generated {len([v for v in ai_assets.values() if v])} AI assets for {item_id}")

        # Convert to SlideContent objects with AI assets
        slide_contents = self._distribute_slides(carousel_slides, title, accent_color, ai_assets)

        if not slide_contents:
            self.logger.warning(f"No slides generated for {item_id}")
            return None

        # Generate HTML for each slide
        html_slides = [generate_slide_html(sc) for sc in slide_contents]

        # Render all slides to PNG
        self.logger.info(f"Rendering {len(html_slides)} slides for {item_id}...")

        try:
            png_buffers = render_all_slides(html_slides, self.config)
        except Exception as e:
            self.logger.error(f"Rendering failed for {item_id}: {e}")
            return None

        # Create subfolder for this item's carousel
        safe_title = self._sanitize_filename(title)
        item_carousel_dir = os.path.join(self.carousels_dir, f"{idx+1:02d}_{item_id}")
        os.makedirs(item_carousel_dir, exist_ok=True)

        # Save each slide PNG
        saved_paths = []
        for slide_idx, png_bytes in enumerate(png_buffers):
            filename = f"slide_{slide_idx+1:02d}.png"
            filepath = os.path.join(item_carousel_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(png_bytes)

            saved_paths.append(filepath)
            self.logger.debug(f"Saved: {filepath}")

        self.logger.info(f"Generated {len(saved_paths)} carousel images for {item_id}")

        # Return manifest entry
        ai_asset_count = len([v for v in ai_assets.values() if v]) if ai_assets else 0
        return {
            "item_id": item_id,
            "title": title,
            "carousel_dir": item_carousel_dir,
            "slide_count": len(saved_paths),
            "slide_paths": saved_paths,
            "dimensions": f"{self.config.width}x{self.config.height}",
            "aspect_ratio": "4:5",
            "accent_color": accent_color,
            "ai_backgrounds": ai_asset_count > 0,
            "ai_asset_count": ai_asset_count,
        }

    def _update_session_readme(self, manifest_entries: List[Dict]) -> None:
        """Update or create README.md in session folder with carousel info."""
        readme_path = os.path.join(self.session_dir, "README.md")

        # Read existing README if present
        existing_content = ""
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

        # Check if AI backgrounds were used
        has_ai_backgrounds = any(e.get('ai_backgrounds', False) for e in manifest_entries)

        # Build carousel section
        carousel_section = [
            "",
            "## Carousel Images (Stage 7)",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "McKinsey-style carousel slides for Instagram/Threads:",
            "- **Dimensions:** 1080x1350px (4:5 portrait)",
            "- **Quality:** 2x Retina resolution",
        ]

        if has_ai_backgrounds:
            carousel_section.append("- **Backgrounds:** AI-generated using Gemini 2.5 Flash Image (nano-banana)")

        carousel_section.append("")
        carousel_section.extend([
            "### Stories",
            "",
        ])

        for entry in manifest_entries:
            title = entry.get('title', 'Untitled')
            slide_count = entry.get('slide_count', 0)
            item_id = entry.get('item_id', '')
            carousel_section.append(f"- **{title}** — {slide_count} slides (`carousels/{item_id}/`)")

        carousel_section.extend([
            "",
            "---",
            "",
        ])

        # Append carousel section to existing README or create new
        if existing_content:
            # Check if carousel section already exists
            if "## Carousel Images (Stage 7)" in existing_content:
                # Replace existing section (find start and end markers)
                import re
                pattern = r"## Carousel Images \(Stage 7\).*?(?=\n## |\Z)"
                replacement = "\n".join(carousel_section[1:])  # Skip leading empty line
                updated_content = re.sub(pattern, replacement, existing_content, flags=re.DOTALL)
            else:
                # Append to end
                updated_content = existing_content.rstrip() + "\n" + "\n".join(carousel_section)
        else:
            # Create new README
            updated_content = f"""# Session: {os.path.basename(self.session_dir)}

Generated by Reddit News Pipeline

{chr(10).join(carousel_section)}"""

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        self.logger.info(f"Updated README: {readme_path}")

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: generate carousel images for each item.

        Args:
            items: List of items from Stage 5 with social_drafts

        Returns:
            List of carousel manifest entries
        """
        # Setup directories
        self._setup_directories()

        self.logger.info(f"Processing {len(items)} items for carousel generation")

        manifest_entries = []

        for idx, item in enumerate(items):
            self.log_progress(idx + 1, len(items), f"Generating carousel...")

            entry = self._generate_carousel_for_item(item, idx)

            if entry:
                manifest_entries.append(entry)

        # Update session README
        if manifest_entries:
            self._update_session_readme(manifest_entries)

        # Also save manifest in session folder
        if self.session_dir:
            session_manifest = os.path.join(self.session_dir, '7_carousel_manifest.json')
            self.save_output(manifest_entries, session_manifest)

        # Log summary
        self.logger.info("Stage 7 Complete.")
        self.logger.info(f"Carousels generated: {len(manifest_entries)}")
        total_slides = sum(e.get('slide_count', 0) for e in manifest_entries)
        self.logger.info(f"Total slides: {total_slides}")

        return manifest_entries


def run_stage_7(
    input_file: str,
    session_dir: Optional[str] = None,
    use_ai_backgrounds: bool = True,
) -> None:
    """
    Execute Stage 7 carousel generation pipeline.

    Args:
        input_file: Path to Stage 5 output (5_social_drafts.json)
        session_dir: Optional existing session folder path
        use_ai_backgrounds: If True, generate AI backgrounds using nano-banana
    """
    stage = Stage7Carousel(
        input_file,
        session_dir=session_dir,
        use_ai_backgrounds=use_ai_backgrounds,
    )
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
