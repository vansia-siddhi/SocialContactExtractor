import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging
import time

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
                    return address[:200]
        return None

    def _clean_and_format_single_address(self, address: str, address_num: int = None) -> str:
        """Clean and format a single address with proper spacing."""
        if not address:
            return address

        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^\d+\.\s*', '', address)
        address = re.sub(r'\s+', ' ', address)
        address = address.strip()

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

        if address_num is not None:
            return f"Address {address_num}: {address}"

        return address

    def _format_address_with_proper_spacing(self, address: str) -> str:
        """Format address with proper spacing and numbering."""
        if not address:
            return address

        if '\n' in address:
            lines = address.split('\n')
            formatted_lines = []
            address_counter = 1
            for line in lines:
                line = line.strip()
                if line:
                    formatted_line = self._clean_and_format_single_address(line, address_counter)
                    if formatted_line:
                        formatted_lines.append(formatted_line)
                        address_counter += 1
            if formatted_lines:
                return '\n'.join(formatted_lines)

        return self._clean_and_format_single_address(address)


class LinkedInParser(SocialPlatformParser):
    """Parser for LinkedIn profiles - uses requests"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        page_content = self._fetch_page(url)

        if not page_content:
            logger.warning(f"Failed to fetch LinkedIn page: {url}")
            # Try alternative URL format (remove in.linkedin.com -> linkedin.com)
            if "in.linkedin.com" in url:
                alt_url = url.replace("in.linkedin.com", "www.linkedin.com")
                logger.info(f"Trying alternative URL: {alt_url}")
                page_content = self._fetch_page(alt_url)

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
        office = self._extract_linkedin_addresses(soup, text)

        if office and office != 'Not found':
            office = self._format_address_with_proper_spacing(office)

        logger.info(f"LinkedIn extraction - Phone: {phone}, Email: {email}, Address: {office}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _extract_linkedin_addresses(self, soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract address from LinkedIn page"""
        try:
            # Method 1: Look for address in the page text using patterns
            address = self._extract_address_from_text(text)
            if address:
                logger.info(f"Found address from text: {address}")
                return address

            # Method 2: Look for location in meta tags
            meta_selectors = [
                'meta[property="og:description"]',
                'meta[name="description"]',
            ]

            for selector in meta_selectors:
                elements = soup.select(selector)
                for element in elements:
                    content = element.get('content', '')
                    if content:
                        address = self._extract_address_from_text(content)
                        if address:
                            logger.info(f"Found address in meta: {address}")
                            return address

            # Method 3: Look for location in specific sections
            location_selectors = [
                '.pv-top-card-section__location',
                '.pv-top-card--list .t-black--light',
                '[data-field="location"]',
                '.pv-top-card .pv-top-card-section__location',
                '.org-location',
                '.org-locations',
                '.pv-about-section .pv-about__summary-text',
                '.pv-entity__location',
            ]

            for selector in location_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text_content = element.get_text(strip=True)
                    if text_content and len(text_content) > 5:
                        address = self._extract_address_from_text(text_content)
                        if address:
                            logger.info(f"Found address from selector {selector}: {address}")
                            return address

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn address: {str(e)}")
            return None


class InstagramParser(SocialPlatformParser):
    """Parser for Instagram profiles"""

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

        address = None
        about_selectors = ['.about', '.profile-about', '[data-testid="about"]']
        for selector in about_selectors:
            elements = soup.select(selector)
            for element in elements:
                text_content = element.get_text(strip=True)
                if any(keyword in text_content.lower() for keyword in ['road', 'street', 'tower', 'surat', 'mumbai']):
                    address = text_content
                    break
            if address:
                break

        if not address:
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

        address = None
        bio_selectors = ['.bio', '[data-testid="UserDescription"]']
        for selector in bio_selectors:
            elements = soup.select(selector)
            for element in elements:
                text_content = element.get_text(strip=True)
                if any(keyword in text_content.lower() for keyword in ['road', 'street', 'tower', 'surat', 'mumbai']):
                    address = text_content
                    break
            if address:
                break

        if not address:
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
