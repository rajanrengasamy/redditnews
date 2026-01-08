"""
Carousel Renderer - Playwright-based HTML to PNG conversion

Renders McKinsey-style carousel HTML slides to PNG images:
- 1080x1350px portrait format (4:5 aspect ratio)
- 2x device scale factor for Retina quality
- Sequential rendering to manage memory
"""

import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CarouselConfig:
    """Configuration for carousel rendering."""
    width: int = 1080
    height: int = 1350
    device_scale_factor: int = 2  # 2x for Retina quality


async def render_slide_async(
    html: str,
    config: Optional[CarouselConfig] = None
) -> bytes:
    """
    Render a single HTML slide to PNG bytes using Playwright.

    Args:
        html: Complete HTML string for the slide
        config: Rendering configuration (uses defaults if None)

    Returns:
        PNG image as bytes
    """
    from playwright.async_api import async_playwright

    if config is None:
        config = CarouselConfig()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={
                'width': config.width,
                'height': config.height,
            },
            device_scale_factor=config.device_scale_factor,
        )

        await page.set_content(html, wait_until='domcontentloaded')

        # Take screenshot
        screenshot = await page.screenshot(type='png')

        await browser.close()

        return screenshot


async def render_all_slides_async(
    html_slides: List[str],
    config: Optional[CarouselConfig] = None
) -> List[bytes]:
    """
    Render multiple HTML slides to PNG bytes.

    Uses a single browser instance for efficiency, but renders sequentially
    to manage memory usage.

    Args:
        html_slides: List of complete HTML strings
        config: Rendering configuration

    Returns:
        List of PNG images as bytes
    """
    from playwright.async_api import async_playwright

    if config is None:
        config = CarouselConfig()

    results: List[bytes] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for idx, html in enumerate(html_slides):
            logger.debug(f"Rendering slide {idx + 1}/{len(html_slides)}")

            page = await browser.new_page(
                viewport={
                    'width': config.width,
                    'height': config.height,
                },
                device_scale_factor=config.device_scale_factor,
            )

            await page.set_content(html, wait_until='domcontentloaded')
            screenshot = await page.screenshot(type='png')
            results.append(screenshot)

            await page.close()

        await browser.close()

    return results


def render_slide(html: str, config: Optional[CarouselConfig] = None) -> bytes:
    """
    Synchronous wrapper for render_slide_async.

    Args:
        html: Complete HTML string for the slide
        config: Rendering configuration

    Returns:
        PNG image as bytes
    """
    return asyncio.run(render_slide_async(html, config))


def render_all_slides(
    html_slides: List[str],
    config: Optional[CarouselConfig] = None
) -> List[bytes]:
    """
    Synchronous wrapper for render_all_slides_async.

    Args:
        html_slides: List of complete HTML strings
        config: Rendering configuration

    Returns:
        List of PNG images as bytes
    """
    return asyncio.run(render_all_slides_async(html_slides, config))
