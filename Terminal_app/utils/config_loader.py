import re
import os
import logging

logger = logging.getLogger(__name__)

def load_subreddits(file_path):
    """
    Parses the markdown file to extract subreddit names.
    Expected format: - **r/SubName** or similar.
    Returns a list of extracted subreddit names (e.g., ['ChatGPT', 'OpenAI']).
    """
    if not os.path.exists(file_path):
        logger.error(f"Config file not found: {file_path}")
        raise FileNotFoundError(f"Config file not found: {file_path}")
        
    subreddits = set()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Match lines like "- **r/ChatGPT**" or "- r/ChatGPT" or just "r/ChatGPT" inside text
            # Regex looking for r/FoundSubredditName
            # allowing for bold markers ** or not
            matches = re.findall(r'r/([A-Za-z0-9_]+)', line)
            for match in matches:
                # exclude common false positives if any, but regex seems safe enough for "r/Name"
                subreddits.add(match)
                
    logger.info(f"Found {len(subreddits)} unique subreddits in {file_path}")
    return list(subreddits)
