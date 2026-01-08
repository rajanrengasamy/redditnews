"""
Stage 6: Visual Asset Generation + Markdown Export

Generates hero images using Google Gemini 3 Pro Image with Design DNA v3.0:
- Professional editorial infographic style (NOT photorealistic, NOT cartoony)
- Geometric icons, flowcharts, arrows for storytelling
- 4:5 portrait aspect ratio for Instagram
- Sources section in markdown export
"""

import logging
import os
import re
import shutil
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Optional

from google import genai
from google.genai import types
from PIL import Image

from utils.stage_base import StageBase, Stage6Output
from utils.design_dna import (
    build_infographic_prompt_from_item,
    InfographicPromptBuilder,
    DEFAULT_COMPOSITION,
    analyze_story_for_infographic,
)
from utils.source_utils import extract_domain

logger = logging.getLogger(__name__)

IMAGE_MODEL = "gemini-3-pro-image-preview"

# Schema version for tracking
SCHEMA_VERSION = "3.0"


class Stage6Visuals(StageBase):
    """
    Stage 6: Visual Asset Generation + Markdown Export

    v3.0 Features:
    - Design DNA v3.0 system for editorial infographics
    - Professional style: geometric icons, flowcharts, arrows
    - NOT photorealistic, NOT cartoony
    - 4:5 portrait aspect ratio for Instagram
    - Story analysis for optimal layout selection
    - Sources section in markdown export
    """

    stage_number = 6
    stage_name = "Visual Asset Generation"
    output_filename = "6_manifest.json"
    default_rate_limit = 2.0
    api_key_env_var = "GOOGLE_API_KEY"
    api_key_fallback = "GOOGLE_AI_API_KEY"

    def __init__(self, input_file: str, debug_prompts: bool = False):
        """
        Args:
            input_file: Path to Stage 5 output (5_social_drafts.json)
            debug_prompts: If True, store prompts in manifest for debugging
        """
        super().__init__(input_file)
        self.session_dir: Optional[str] = None
        self.images_dir: Optional[str] = None
        self.assets_dir: Optional[str] = None
        self.timestamp: str = ""
        self.debug_prompts = debug_prompts

        # Initialize infographic prompt builder
        self.prompt_builder = InfographicPromptBuilder()

    def _setup_directories(self) -> str:
        """Create session and asset directories."""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Session folder with timestamp
        self.session_dir = os.path.join(self.output_dir, f"session_{self.timestamp}")
        self.images_dir = os.path.join(self.session_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)

        # Flat assets folder for backward compatibility
        self.assets_dir = os.path.join(self.output_dir, '6_final_assets')
        os.makedirs(self.assets_dir, exist_ok=True)

        self.logger.info(f"Session folder: {self.session_dir}")
        return self.timestamp

    @staticmethod
    def _sanitize_filename(title: str, max_length: int = 50) -> str:
        """Convert title to safe filename."""
        clean = re.sub(r'[^\w\s-]', '', title)
        clean = re.sub(r'\s+', '_', clean)
        return clean[:max_length].rstrip('_')

    # =========================================================================
    # Sources Section Builder (SP-06)
    # =========================================================================

    def _build_sources_section(self, item: Dict) -> List[str]:
        """
        Build Sources section for markdown.

        Includes:
        - 1-3 source URLs with titles/publishers
        - Perplexity validation link
        - Reddit discovery link
        """
        lines = [
            "---",
            "",
            "## Sources",
            "",
        ]

        # Add structured sources (up to 3)
        sources = item.get('sources', [])
        if sources:
            lines.append("### Cited Sources")
            lines.append("")
            for source in sources[:3]:
                url = source.get('url', '')
                title = source.get('title') or extract_domain(url)
                publisher = source.get('publisher', '')
                source_type = source.get('source_type', 'secondary')

                if publisher:
                    lines.append(f"- [{title}]({url}) — *{publisher}* ({source_type})")
                else:
                    lines.append(f"- [{title}]({url}) ({source_type})")
            lines.append("")

        # Add Perplexity validation link
        perplexity_url = item.get('perplexity_search_url', '')
        if perplexity_url:
            lines.extend([
                "### Validation",
                "",
                f"- [Perplexity Search]({perplexity_url}) — AI-powered fact verification",
                "",
            ])

        # Add Reddit discovery link
        reddit_url = item.get('reddit_post_url', item.get('url', ''))
        if reddit_url:
            subreddit = item.get('subreddit', '')
            reddit_label = f"r/{subreddit}" if subreddit else "Reddit Discussion"
            lines.extend([
                "### Discovery",
                "",
                f"- [{reddit_label}]({reddit_url}) — Original discussion",
                "",
            ])

        return lines

    # =========================================================================
    # Markdown Builder (Enhanced)
    # =========================================================================

    def _build_markdown_content(self, item: Dict, idx: int) -> str:
        """Build markdown content for a single story with sources."""
        item_id = item.get('id', f'item_{idx}')
        title = item.get('title', 'Untitled')
        url = item.get('reddit_post_url', item.get('url', ''))
        social_drafts = item.get('social_drafts', {})

        md_lines = [
            f"# {title}",
            "",
            f"**Discovery:** [{url}]({url})",
            f"**Item ID:** `{item_id}`",
            "",
        ]

        # Add source domains if available
        sources = item.get('sources', [])
        if sources:
            source_domains = [extract_domain(s.get('url', '')) for s in sources[:3]]
            source_domains = [d for d in source_domains if d]
            if source_domains:
                md_lines.append(f"**Verified by:** {', '.join(source_domains)}")
                md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## Single Post Options (A/B Test)",
            "",
            "### Option A",
            f"**Tone:** {social_drafts.get('x_tone_a', 'N/A')}",
            "",
            "```",
            social_drafts.get('x_post_a', 'N/A'),
            "```",
            "",
            "### Option B",
            f"**Tone:** {social_drafts.get('x_tone_b', 'N/A')}",
            "",
            "```",
            social_drafts.get('x_post_b', 'N/A'),
            "```",
            "",
            "---",
            "",
            "## Carousel Slides",
            "",
        ])

        # Add carousel slides
        slides = social_drafts.get('carousel_slides', [])
        for slide in slides:
            slide_num = slide.get('slide_number', '?')
            slide_text = slide.get('text', '')
            md_lines.extend([
                f"### Slide {slide_num}",
                "",
                "```",
                slide_text,
                "```",
                "",
            ])

        # Add Instagram caption
        md_lines.extend([
            "---",
            "",
            "## Instagram Caption",
            "",
            "```",
            social_drafts.get('instagram_caption', 'N/A'),
            "```",
            "",
            "---",
            "",
            "## Hero Image",
            "",
            f"![Hero Image](./images/{item_id}_hero.png)",
            "",
            "**Visual Style:** Editorial infographic with geometric icons and flowcharts",
            "",
        ])

        # Add Sources section (SP-06)
        md_lines.extend(self._build_sources_section(item))

        return '\n'.join(md_lines)

    def _generate_markdown_file(self, item: Dict, idx: int) -> str:
        """Generate markdown file for a single story."""
        item_id = item.get('id', f'item_{idx}')
        title = item.get('title', 'Untitled')

        safe_title = self._sanitize_filename(title)
        filename = f"{idx+1:02d}_{item_id}_{safe_title}.md"
        filepath = os.path.join(self.session_dir, filename)

        content = self._build_markdown_content(item, idx)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Created Markdown: {filename}")
        return filepath

    # =========================================================================
    # Image Generation with Design DNA (D-03, D-04)
    # =========================================================================

    def _build_image_prompt(self, item: Dict) -> str:
        """
        Build prompt for infographic generation using Design DNA v3.0.

        Creates professional editorial infographics with:
        - Geometric icons and flowcharts
        - Clean typography and arrows
        - Story-driven layout selection
        """
        return build_infographic_prompt_from_item(item)

    def _resize_to_instagram(self, image_bytes: bytes) -> bytes:
        """
        Resize image to exact Instagram dimensions (1080x1350, 4:5 portrait).

        Uses high-quality Lanczos resampling and maintains aspect ratio
        by cropping if needed.
        """
        target_width, target_height = self.prompt_builder.get_dimensions()

        # Open image from bytes
        img = Image.open(BytesIO(image_bytes))
        orig_width, orig_height = img.size

        # Calculate aspect ratios
        target_ratio = target_width / target_height
        orig_ratio = orig_width / orig_height

        # Resize strategy: scale to fill, then crop to exact dimensions
        if orig_ratio > target_ratio:
            # Image is wider - scale by height, crop width
            new_height = target_height
            new_width = int(orig_width * (target_height / orig_height))
        else:
            # Image is taller - scale by width, crop height
            new_width = target_width
            new_height = int(orig_height * (target_width / orig_width))

        # Resize with high-quality resampling
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Crop to exact target dimensions (center crop)
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        img_cropped = img_resized.crop((left, top, right, bottom))

        # Convert back to bytes
        output_buffer = BytesIO()
        img_cropped.save(output_buffer, format='PNG', optimize=True)
        return output_buffer.getvalue()

    def _generate_image(self, prompt: str, output_path: str) -> bool:
        """
        Generate image using Gemini 3 Pro Image with Design DNA settings.

        Includes:
        - 4:5 portrait aspect ratio for Instagram (1080x1350)
        - High quality settings
        - Post-processing resize to exact Instagram dimensions
        """
        try:
            api_key = self._api_key
            client = genai.Client(api_key=api_key)

            # Get target dimensions from Design DNA
            width, height = self.prompt_builder.get_dimensions()

            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["image", "text"],
                )
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_bytes = part.inline_data.data

                    # Resize to exact Instagram dimensions
                    resized_bytes = self._resize_to_instagram(image_bytes)

                    with open(output_path, 'wb') as f:
                        f.write(resized_bytes)

                    self.logger.info(f"Saved image to {output_path} ({width}x{height})")
                    return True

            self.logger.warning(f"No image generated for prompt: {prompt[:80]}...")
            return False

        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            return False

    def _process_single_item(self, item: Dict, idx: int) -> Optional[Dict]:
        """Process a single item: generate markdown and image."""
        item_id = item.get('id', f'item_{idx}')
        title = item.get('title', 'Untitled')

        # Generate Markdown file
        md_path = self._generate_markdown_file(item, idx)

        # Generate image with Design DNA
        prompt = self._build_image_prompt(item)
        filename = f"{item_id}_hero.png"
        session_image_path = os.path.join(self.images_dir, filename)
        flat_image_path = os.path.join(self.assets_dir, filename)

        self.logger.info(f"Generating image for {item_id}...")
        self.logger.debug(f"Prompt: {prompt[:200]}...")

        success = self._generate_image(prompt, session_image_path)

        if success:
            # Copy to flat folder for backward compatibility
            shutil.copy2(session_image_path, flat_image_path)

            manifest_entry = {
                "item_id": item_id,
                "title": title,
                "markdown_file": md_path,
                "session_image_path": session_image_path,
                "asset_path": flat_image_path,
                "asset_type": "image/png",
                "visual_style": "editorial_infographic",
                "aspect_ratio": self.prompt_builder.get_aspect_ratio(),
            }

            # Add debug info if enabled
            if self.debug_prompts:
                manifest_entry["_debug_prompt"] = prompt

            # Add source info for traceability
            if item.get('sources'):
                manifest_entry["source_count"] = len(item.get('sources', []))

            return manifest_entry

        return None

    def _generate_session_index(self, manifest_entries: List[Dict]) -> str:
        """Generate README.md index file for session folder."""
        index_path = os.path.join(self.session_dir, "README.md")

        lines = [
            f"# Session: {self.timestamp}",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Visual Style",
            "",
            "All images use the **Design DNA v3.0** editorial infographic system:",
            "- Professional infographic style (NOT photorealistic, NOT cartoony)",
            "- Clean geometric icons and flowcharts",
            "- Story-driven layout with arrows and connections",
            "- 4:5 portrait aspect ratio (Instagram-optimized)",
            "- Dark backgrounds with accent colors",
            "",
            "## Stories",
            "",
        ]

        for entry in manifest_entries:
            title = entry.get('title', 'Untitled')
            md_file = os.path.basename(entry.get('markdown_file', ''))
            source_count = entry.get('source_count', 0)
            source_note = f" ({source_count} sources)" if source_count else ""
            lines.append(f"- [{title}](./{md_file}){source_note}")

        lines.extend([
            "",
            "## Images",
            "",
            "All hero images are in the `images/` folder.",
            "",
            "---",
            "",
            f"*Schema Version: {SCHEMA_VERSION}*",
        ])

        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return index_path

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: generate visual assets and markdown files.

        Args:
            items: List of items from Stage 5 with social_drafts

        Returns:
            List of manifest entries
        """
        # Setup directories
        self._setup_directories()

        self.logger.info(f"Processing {len(items)} items with Design DNA v3.0 (editorial infographic)")

        manifest_entries = []

        for idx, item in enumerate(items):
            manifest_entry = self._process_single_item(item, idx)

            if manifest_entry:
                manifest_entries.append(manifest_entry)

            # Rate limiting (skip last)
            if idx < len(items) - 1:
                self.rate_limit()

        # Generate session index
        self._generate_session_index(manifest_entries)

        # Also save manifest in session folder
        session_manifest = os.path.join(self.session_dir, 'manifest.json')
        self.save_output(manifest_entries, session_manifest)

        # Log summary
        self.logger.info("Stage 6 Complete.")
        self.logger.info(f"Session folder: {self.session_dir}")
        self.logger.info(f"Items processed: {len(manifest_entries)}")
        self.logger.info(f"Visual style: Design DNA v3.0 (editorial infographic)")

        return manifest_entries


def run_stage_6(input_file: str) -> None:
    """
    Execute Stage 6 visual generation pipeline.

    Args:
        input_file: Path to Stage 5 output (5_social_drafts.json)
    """
    stage = Stage6Visuals(input_file)
    stage.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
