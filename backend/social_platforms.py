import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class SocialPlatformParser:
    """Base class for social media platform parsers"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content using requests"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        matches = re.findall(email_pattern, text)
        return matches[0] if matches else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        phone_patterns = [
            r'\+91[\s-]?\d{10}',
            r'0\d{10}',
            r'\d{10}',
            r'\+1[\s-]?\d{10}',
            r'\+44[\s-]?\d{10}',
            r'\(\d{3}\)\s*\d{3}[\s-]?\d{4}',
            r'\d{3}[\s-]\d{3}[\s-]\d{4}',
            r'\d{5}[\s-]\d{5}',
            r'\+\d{1,3}[\s-]?\d{10}',
            r'[0-9]{10}',
        ]

        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            if matches:
                phone = matches[0]
                phone = re.sub(r'\s+', ' ', phone)
                phone = re.sub(r'[^0-9+]', '', phone)
                if len(phone) == 10 and phone.isdigit():
                    return f"+91 {phone[:5]} {phone[5:]}"
                elif len(phone) == 11 and phone.startswith('0'):
                    return f"+91 {phone[1:6]} {phone[6:]}"
                elif len(phone) == 12 and phone.startswith('91'):
                    return f"+91 {phone[2:7]} {phone[7:]}"
                return phone
        return None

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract address from text"""
        # Common address patterns
        address_patterns = [
            r'\d{1,5}\s+[\w\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl|Court|Ct|Park|Pkwy)',
            r'[\w\s,]+(?:Tower|Building|Complex|Park|Centre|Center|Office|House|Society|Apartment|Flats|Floor|Corner|Meridian)',
            r'[\w\s,]+(?:Surat|Mumbai|Delhi|Ahmedabad|Bangalore|Chennai|Kolkata|Hyderabad|Pune|Gujarat|Maharashtra)',
            r'[A-Za-z0-9\s,]+(?:GJ|MH|KA|TN|DL|WB|UP|RJ|HR|PB|KL|TG)\s*\d{5,6}',
            r'\d{5,6}\s*[\w\s,]+',
            r'[\w\s]+,\s*[\w\s]+,\s*[\w\s]+\s*\d{5,6}',
        ]

        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                address = matches[0].strip()
                address = re.sub(r'\s+', ' ', address)
                if len(address) > 10 and len(address) < 300:
                    # Filter out follower counts
                    if not any(keyword in address.lower() for keyword in
                               ['followers', 'following', 'posts', 'likes', 'comments']):
                        return address[:200]
        return None

    def _is_follower_text(self, text: str) -> bool:
        """Check if text contains follower/following/post counts"""
        text_lower = text.lower()
        follower_keywords = ['followers', 'following', 'posts', 'post', 'likes', 'comments', 'views', 'reactions', 'shares']
        for keyword in follower_keywords:
            if keyword in text_lower:
                return True
        if re.search(r'[\d,]+[\s]+(?:followers|following|posts|post)', text_lower):
            return True
        return False

    def _is_valid_address(self, text: str) -> bool:
        """Check if text is a valid address"""
        if not text or len(text) < 8:
            return False

        if self._is_follower_text(text):
            return False

        address_indicators = [
            'road', 'street', 'st', 'avenue', 'ave', 'boulevard', 'blvd',
            'lane', 'ln', 'drive', 'dr', 'way', 'place', 'pl', 'court', 'ct',
            'tower', 'building', 'complex', 'park', 'centre', 'center',
            'office', 'house', 'society', 'apartment', 'floor', 'corner',
            'surat', 'mumbai', 'delhi', 'ahmedabad', 'bangalore', 'chennai',
            'kolkata', 'hyderabad', 'pune', 'gujarat', 'maharashtra',
            'india', 'meridian', 'chicago', 'texas', 'california'
        ]

        has_numbers = any(char.isdigit() for char in text)
        has_address_keywords = any(keyword in text.lower() for keyword in address_indicators)

        return has_numbers or has_address_keywords

    def _clean_and_format_single_address(self, address: str) -> str:
        """Clean and format a single address"""
        if not address:
            return address

        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^\d+\.\s*', '', address)
        address = re.sub(r'\s+', ' ', address)
        address = address.strip()

        # Add proper spacing
        address = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', address)
        address = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', address)
        address = re.sub(r'([A-Za-z])(\d{5,6})', r'\1 \2', address)
        address = re.sub(r'(\d{5,6})([A-Za-z])', r'\1 \2', address)
        address = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', address)
        address = re.sub(r'([a-z])([A-Z])', r'\1 \2', address)
        address = re.sub(r'([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5,6})', r'\1, \2 \3', address)
        address = re.sub(r'([A-Z]{2})\s+(IN|US|UK|CA|AU)', r'\1, \2', address)
        address = re.sub(r'\s*-\s*', ' - ', address)
        address = re.sub(r'Opp\.', 'Opp.', address)
        address = re.sub(r'Opp\.\s+', 'Opp. ', address)
        address = re.sub(r'\s+', ' ', address)
        address = address.strip()

        return address

    def _format_address_with_proper_spacing(self, address: str) -> str:
        """Format address with proper spacing"""
        if not address:
            return address

        if '\n' in address:
            lines = address.split('\n')
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line and self._is_valid_address(line):
                    formatted_line = self._clean_and_format_single_address(line)
                    if formatted_line:
                        formatted_lines.append(formatted_line)
            if formatted_lines:
                return '\n'.join(formatted_lines)

        if self._is_valid_address(address):
            return self._clean_and_format_single_address(address)

        return None


class LinkedInParser(SocialPlatformParser):
    """Parser for LinkedIn profiles - uses requests for public data"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        # Try with requests first (more reliable on Render)
        page_content = self._fetch_page(url)

        if not page_content:
            logger.warning(f"Failed to fetch LinkedIn page: {url}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        # Extract data
        email = self._extract_email(text)
        phone = self._extract_phone(text)

        # Extract address - use multiple methods
        office = self._extract_linkedin_address(soup, text)

        if office and office != 'Not found':
            office = self._format_address_with_proper_spacing(office)

        logger.info(f"LinkedIn extraction - Phone: {phone}, Email: {email}, Address: {office}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _extract_linkedin_address(self, soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract address from LinkedIn page"""
        try:
            # Method 1: Look for location in the profile header
            location_selectors = [
                '.pv-top-card-section__location',
                '.pv-top-card--list .t-black--light',
                '[data-field="location"]',
                '.pv-top-card .pv-top-card-section__location',
                '.pv-entity__location',
                '.org-location',
                '.org-locations',
                '.pv-about-section .pv-about__summary-text',
            ]

            for selector in location_selectors:
                elements = soup.select(selector)
                for element in elements:
                    location_text = element.get_text(strip=True)
                    if location_text and len(location_text) > 3:
                        if self._is_valid_address(location_text):
                            logger.info(f"Found location from selector: {location_text}")
                            return location_text

            # Method 2: Look for address in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                if tag.get('name') == 'location' or tag.get('property') == 'og:location':
                    content = tag.get('content', '')
                    if content and len(content) > 3 and self._is_valid_address(content):
                        return content

            # Method 3: Extract from text
            address = self._extract_address_from_text(text)
            if address and self._is_valid_address(address):
                return address

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn address: {str(e)}")
            return None


class InstagramParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Instagram profile: {url}")

        page_content = self._fetch_page(url)

        if not page_content:
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        email = self._extract_email(text)
        phone = self._extract_phone(text)
        address = self._extract_address_from_text(text)

        if address:
            address = self._format_address_with_proper_spacing(address)

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': address if address else 'Not found'
        }


class FacebookParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Facebook profile: {url}")

        page_content = self._fetch_page(url)

        if not page_content:
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        email = self._extract_email(text)
        phone = self._extract_phone(text)
        address = self._extract_address_from_text(text)

        if address:
            address = self._format_address_with_proper_spacing(address)

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': address if address else 'Not found'
        }


class TwitterParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Twitter/X profile: {url}")

        page_content = self._fetch_page(url)

        if not page_content:
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        email = self._extract_email(text)
        phone = self._extract_phone(text)
        address = self._extract_address_from_text(text)

        if address:
            address = self._format_address_with_proper_spacing(address)

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': address if address else 'Not found'
        }


class YouTubeParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing YouTube profile: {url}")

        page_content = self._fetch_page(url)

        if not page_content:
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        email = self._extract_email(text)
        phone = self._extract_phone(text)
        address = self._extract_address_from_text(text)

        if address:
            address = self._format_address_with_proper_spacing(address)

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': address if address else 'Not found'
        }


class GenericParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Using generic parser for: {url}")

        page_content = self._fetch_page(url)

        if page_content:
            soup = BeautifulSoup(page_content, 'html.parser')
            text = soup.get_text()

            phone = self._extract_phone(text)
            email = self._extract_email(text)
            address = self._extract_address_from_text(text)

            if address:
                address = self._format_address_with_proper_spacing(address)

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': address if address else 'Not found'
            }

        return {
            'phone': 'Not found',
            'email': 'Not found',
            'office': 'Not found'
        }
