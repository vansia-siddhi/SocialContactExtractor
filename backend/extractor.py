from typing import Dict, Optional
from backend.social_platforms import (
    LinkedInParser, InstagramParser, FacebookParser,
    TwitterParser, YouTubeParser, GenericParser
)
import logging

logger = logging.getLogger(__name__)

class ContactExtractor:
    """Main contact extractor class"""

    def __init__(self):
        self.platforms = {
            'linkedin': LinkedInParser(),
            'instagram': InstagramParser(),
            'facebook': FacebookParser(),
            'twitter': TwitterParser(),
            'x': TwitterParser(),
            'youtube': YouTubeParser()
        }
        self.generic_parser = GenericParser()

    def detect_platform(self, url: str) -> str:
        """Detect social media platform from URL"""
        url_lower = url.lower()

        if 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
            return 'facebook'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        else:
            return 'generic'

    def extract(self, url: str) -> Dict[str, Optional[str]]:
        """
        Extract contact details from URL
        Returns: {'phone': str, 'email': str, 'office': str}
        """
        platform = self.detect_platform(url)

        try:
            if platform in self.platforms:
                parser = self.platforms[platform]
                contacts = parser.parse(url)
                logger.info(f"Extracted contacts using {platform} parser")
            else:
                contacts = self.generic_parser.parse(url)
                logger.info("Used generic parser")

            return contacts

        except Exception as e:
            logger.error(f"Error extracting contacts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }
