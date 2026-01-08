"""
Stage 1: Ingestion

Fetches Reddit RSS feeds and collects posts within a time window.
"""

import calendar
import feedparser
import logging
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from utils.config_loader import load_subreddits
from utils.stage_base import StageBase

logger = logging.getLogger(__name__)


class Stage1Ingestion(StageBase):
    """
    Stage 1: Ingest Reddit RSS feeds.

    Unlike other stages, this generates data rather than transforming it.
    """

    stage_number = 1
    stage_name = "Ingestion"
    output_filename = "1_raw_feed.json"
    default_rate_limit = 2.0
    requires_input = False  # Stage 1 generates data, doesn't transform it

    USER_AGENT = "mac:com.antigravity.redditnewspipeline:v1.0 (by /u/antigravity_agent)"

    def __init__(self, output_dir: str, subreddits_path: str, time_window_hours: tuple = (72, 24)):
        """
        Args:
            output_dir: Directory where output will be saved
            subreddits_path: Path to subreddit list markdown file
            time_window_hours: Tuple of (start_hours_ago, end_hours_ago) for filtering
        """
        # Stage 1 doesn't have input file, set up output directly
        super().__init__(input_file=None)
        self.output_dir = output_dir
        self.output_file = os.path.join(output_dir, self.output_filename)
        self.subreddits_path = subreddits_path
        self.window_start_hours = time_window_hours[0]
        self.window_end_hours = time_window_hours[1]
        self.subreddits: List[str] = []

        os.makedirs(output_dir, exist_ok=True)

    def _load_subreddits(self) -> List[str]:
        """Load subreddit list from config file."""
        try:
            subreddits = load_subreddits(self.subreddits_path)
            if not subreddits:
                self.logger.warning("No subreddits found to process.")
            return subreddits
        except Exception as e:
            self.logger.error(f"Error loading subreddits: {e}")
            return []

    def _get_time_window(self) -> tuple:
        """Calculate the time window for filtering posts."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=self.window_start_hours)
        window_end = now - timedelta(hours=self.window_end_hours)
        return window_start, window_end

    def _fetch_subreddit_feed(self, subreddit: str, window_start: datetime, window_end: datetime) -> List[Dict]:
        """Fetch RSS feed for a single subreddit."""
        rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
        items = []

        try:
            headers = {"User-Agent": self.USER_AGENT}
            response = requests.get(rss_url, headers=headers, timeout=10)

            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch {subreddit}: Status {response.status_code}")
                return items

            # Validate content type
            content_type = response.headers.get('Content-Type', '')
            if 'xml' not in content_type and not response.text.strip().startswith(('<?xml', '<rss', '<feed')):
                self.logger.warning(f"Invalid content type for {subreddit}: {content_type}")
                return items

            feed = feedparser.parse(response.content)

            if feed.bozo:
                self.logger.warning(f"Error parsing feed for {subreddit}: {feed.bozo_exception}")

            if not feed.entries:
                self.logger.info(f"No entries found for {subreddit}")
                return items

            # Extract entries within time window
            for entry in feed.entries:
                if not hasattr(entry, 'published_parsed') or not entry.published_parsed:
                    continue

                try:
                    pub_timestamp = calendar.timegm(entry.published_parsed)
                    pub_date = datetime.fromtimestamp(pub_timestamp, timezone.utc)

                    if window_start <= pub_date <= window_end:
                        item = {
                            "id": entry.id,
                            "url": entry.link,
                            "title": entry.title,
                            "published_at": pub_date.isoformat(),
                            "subreddit": subreddit,
                            "author": entry.get('author', 'unknown'),
                        }
                        items.append(item)
                except Exception as e:
                    self.logger.warning(f"Error processing entry date: {e}")

        except Exception as e:
            self.logger.error(f"Failed to fetch {subreddit}: {e}")

        return items

    def process(self, items: List[Dict]) -> List[Dict]:
        """
        Process: fetch RSS feeds and collect items.

        For Stage 1, the items input is ignored (empty list).
        Returns collected RSS feed items.
        """
        # Load subreddits
        self.subreddits = self._load_subreddits()
        if not self.subreddits:
            return []

        # Get time window
        window_start, window_end = self._get_time_window()
        self.logger.info(f"Time Window: {window_start} to {window_end}")

        raw_feed_items = []

        for idx, subreddit in enumerate(self.subreddits):
            self.logger.info(f"Fetching {subreddit}...")

            feed_items = self._fetch_subreddit_feed(subreddit, window_start, window_end)
            raw_feed_items.extend(feed_items)

            # Rate limit (skip after last)
            if idx < len(self.subreddits) - 1:
                self.rate_limit()

        self.logger.info(f"Collected {len(raw_feed_items)} items within the window.")
        return raw_feed_items


def run_stage_1() -> Optional[str]:
    """
    Execute Stage 1 ingestion pipeline.

    Returns:
        Path to output file if successful, None otherwise.
    """
    # Configure paths
    base_dir = os.path.dirname(os.path.dirname(__file__))
    docs_path = os.path.join(base_dir, 'docs', 'subreditlist.md')
    output_dir = os.path.join(base_dir, 'output')

    stage = Stage1Ingestion(
        output_dir=output_dir,
        subreddits_path=docs_path
    )
    result = stage.run()

    return stage.output_file if result else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_stage_1()
