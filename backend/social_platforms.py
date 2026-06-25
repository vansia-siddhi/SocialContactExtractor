import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch page content using Selenium (for JavaScript-heavy sites)"""
        driver = None
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.get(url)

            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Get page source
            page_source = driver.page_source
            return page_source

        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()

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

    def _is_follower_text(self, text: str) -> bool:
        """Check if text contains follower/following/post counts"""
        text_lower = text.lower()
        follower_keywords = ['followers', 'following', 'posts', 'post', 'likes', 'comments', 'views', 'reactions', 'shares']
        for keyword in follower_keywords:
            if keyword in text_lower:
                return True
        # Check for patterns like "1,117 posts", "3,409 followers"
        if re.search(r'[\d,]+[\s]+(?:followers|following|posts|post)', text_lower):
            return True
        # Check for patterns like "1.2K followers"
        if re.search(r'[\d.,]+[KkMm]?\s*(?:followers|following|posts)', text_lower):
            return True
        return False

    def _is_bio_text(self, text: str) -> bool:
        """Check if text is likely bio/description text (not address)"""
        text_lower = text.lower()
        bio_keywords = ['excellence', 'innovation', 'product', 'engineering', 'development', 'software',
                        'solutions', 'services', 'technology', 'digital', 'transformation', 'consulting',
                        'agency', 'creative', 'design', 'marketing', 'brand', 'strategy', 'management',
                        'business', 'consultant', 'professional', 'expert', 'leader', 'vision', 'mission',
                        'culture', 'values', 'team', 'work', 'career', 'opportunity', 'growth', 'success',
                        'quality', 'commitment', 'passion', 'dedicated', 'experienced', 'specialized',
                        'providing', 'delivering', 'helping', 'building', 'creating', 'driving', 'leading',
                        'ui/ux', 'e-commerce', 'cms', 'web', 'development', 'engineer', 'specialist']

        for keyword in bio_keywords:
            if keyword in text_lower:
                return True
        return False

    def _is_valid_address(self, text: str) -> bool:
        """Check if text is a valid address (not follower count, not bio text)"""
        if not text or len(text) < 8:
            return False

        # Check if it's follower count
        if self._is_follower_text(text):
            return False

        # Check if it's bio text
        if self._is_bio_text(text):
            return False

        # Check for address indicators
        address_indicators = [
            'road', 'street', 'st', 'avenue', 'ave', 'boulevard', 'blvd',
            'lane', 'ln', 'drive', 'dr', 'way', 'place', 'pl', 'court', 'ct',
            'tower', 'building', 'complex', 'park', 'centre', 'center',
            'office', 'house', 'society', 'apartment', 'floor', 'corner',
            'surat', 'mumbai', 'delhi', 'ahmedabad', 'bangalore', 'chennai',
            'kolkata', 'hyderabad', 'pune', 'gujarat', 'maharashtra',
            'india', 'meridian', 'chicago', 'texas', 'california',
            'unit', 'suite', 'block', 'sector', 'phase'
        ]

        # Check if it has numbers (address usually has numbers)
        has_numbers = any(char.isdigit() for char in text)

        # Check if it has address keywords
        has_address_keywords = any(keyword in text.lower() for keyword in address_indicators)

        return has_numbers or has_address_keywords

    def _clean_and_format_single_address(self, address: str) -> str:
        """Clean and format a single address with proper spacing."""
        if not address:
            return address

        # Remove "Get directions" and "Primary"
        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)

        # Remove numbering if present (like "1. " at start)
        address = re.sub(r'^\d+\.\s*', '', address)

        # Remove extra spaces
        address = re.sub(r'\s+', ' ', address)
        address = address.strip()

        # Add space after number followed by letter (e.g., "4052Sliver" -> "4052 Sliver")
        address = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', address)

        # Add space before number if preceded by letter (e.g., "Road4052" -> "Road 4052")
        address = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', address)

        # Add space between word and number (e.g., "Gujarat394105" -> "Gujarat 394105")
        address = re.sub(r'([A-Za-z])(\d{5,6})', r'\1 \2', address)

        # Add space between number and word (e.g., "394105IN" -> "394105 IN")
        address = re.sub(r'(\d{5,6})([A-Za-z])', r'\1 \2', address)

        # Add space between uppercase word and next word (e.g., "VIPCircle" -> "VIP Circle")
        address = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', address)

        # Add space between lowercase and uppercase (e.g., "CircleSurat" -> "Circle Surat")
        address = re.sub(r'([a-z])([A-Z])', r'\1 \2', address)

        # Add space between "Road", "Street", "Avenue" and number
        address = re.sub(r'(Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl|Court|Ct)(\d+)', r'\1 \2', address, flags=re.IGNORECASE)

        # Ensure space after "Road", "Street", etc. if missing
        address = re.sub(r'(Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd)([A-Za-z])', r'\1 \2', address, flags=re.IGNORECASE)

        # Add comma after city name if followed by state
        address = re.sub(r'([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5,6})', r'\1, \2 \3', address)

        # Add comma after state if followed by country code
        address = re.sub(r'([A-Z]{2})\s+(IN|US|UK|CA|AU)', r'\1, \2', address)

        # Fix " - " spacing
        address = re.sub(r'\s*-\s*', ' - ', address)

        # Fix "Opp." spacing
        address = re.sub(r'Opp\.', 'Opp.', address)
        address = re.sub(r'Opp\.\s+', 'Opp. ', address)

        # Final cleanup
        address = re.sub(r'\s+', ' ', address)
        address = address.strip()

        return address

    def _format_address_with_proper_spacing(self, address: str) -> str:
        """Format address with proper spacing between all parts."""
        if not address:
            return address

        # First, handle the case where addresses are already separated by newlines
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

        # Check for numbered addresses in the same line
        numbered_pattern = r'(\d+\.\s*[^\d]+?)(?=\s*\d+\.\s*|$)'
        matches = re.findall(numbered_pattern, address)

        if len(matches) > 1:
            formatted_addresses = []
            for match in matches:
                clean_addr = match.strip()
                clean_addr = re.sub(r'Get directions', '', clean_addr, flags=re.IGNORECASE)
                if self._is_valid_address(clean_addr):
                    formatted_addr = self._clean_and_format_single_address(clean_addr)
                    if formatted_addr:
                        formatted_addresses.append(formatted_addr)

            if formatted_addresses:
                return '\n'.join(formatted_addresses)

        # If single address, validate and format
        if self._is_valid_address(address):
            return self._clean_and_format_single_address(address)

        return None


class LinkedInParser(SocialPlatformParser):
    """Parser for LinkedIn profiles"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        page_content = self._fetch_with_selenium(url)

        if not page_content:
            logger.warning(f"Failed to fetch LinkedIn page: {url}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        soup = BeautifulSoup(page_content, 'html.parser')
        text = soup.get_text()

        email = self._extract_email(text)
        phone = self._extract_phone(text)
        office = self._extract_linkedin_addresses(soup)

        if office and office != 'Not found':
            office = self._format_address_with_proper_spacing(office)

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _extract_linkedin_addresses(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            addresses = []
            seen_addresses = set()

            # Method 1: Look for elements with ID pattern address-0, address-1, address-2, etc.
            for i in range(10):
                address_element = soup.find(id=f'address-{i}')
                if address_element:
                    address_text = address_element.get_text(strip=True)
                    if address_text and len(address_text) > 5:
                        address_text = self._clean_address(address_text)
                        if address_text and self._is_valid_address(address_text):
                            if address_text not in seen_addresses:
                                addresses.append(address_text)
                                seen_addresses.add(address_text)
                                logger.info(f"Found address-{i}: {address_text}")

            # Method 2: Look for location selectors
            if not addresses:
                location_selectors = [
                    '.pv-top-card-section__location',
                    '.pv-top-card--list .t-black--light',
                    '[data-field="location"]',
                    '.pv-top-card .pv-top-card-section__location',
                    '.org-location',
                    '.org-locations',
                    '.pv-entity__location',
                    '.pv-about-section .pv-about__summary-text',
                ]

                for selector in location_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 5:
                            text = self._clean_address(text)
                            if text and self._is_valid_address(text):
                                if text not in seen_addresses:
                                    addresses.append(text)
                                    seen_addresses.add(text)
                                    logger.info(f"Found address from selector {selector}: {text}")

            # Method 3: Look for address patterns in the page text (filtered)
            if not addresses:
                all_text = soup.get_text()
                lines = all_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if self._is_valid_address(line) and len(line) > 15 and len(line) < 300:
                        line = re.sub(r'\s+', ' ', line)
                        line = re.sub(r'Get directions', '', line, flags=re.IGNORECASE)
                        line = re.sub(r'^Primary', '', line, flags=re.IGNORECASE)
                        if line and line not in seen_addresses:
                            addresses.append(line)
                            seen_addresses.add(line)
                            logger.info(f"Found address from text: {line}")

            if addresses:
                # Remove duplicates and filter
                unique_addresses = []
                seen = set()
                for addr in addresses:
                    addr_lower = addr.lower()
                    if addr_lower not in seen and self._is_valid_address(addr):
                        unique_addresses.append(addr)
                        seen.add(addr_lower)

                if unique_addresses:
                    if len(unique_addresses) == 1:
                        return unique_addresses[0]
                    else:
                        # Join multiple addresses with numbering
                        formatted = []
                        for i, addr in enumerate(unique_addresses, 1):
                            formatted.append(f"{i}. {addr}")
                        return "\n".join(formatted)

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn address: {str(e)}")
            return None

    def _clean_address(self, address: str) -> str:
        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)
        address = re.sub(r'\s+', ' ', address)
        address = re.sub(r';+$', '', address)
        return address.strip()


class InstagramParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Instagram profile: {url}")

        page_content = self._fetch_with_selenium(url)

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
        bio_selectors = ['.bio', '._aaqe', '.x9f619']
        for selector in bio_selectors:
            elements = soup.select(selector)
            for element in elements:
                text_content = element.get_text(strip=True)
                if self._is_valid_address(text_content):
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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        return None


class FacebookParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Facebook profile: {url}")

        page_content = self._fetch_with_selenium(url)

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
                if self._is_valid_address(text_content):
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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        return None


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
                if self._is_valid_address(text_content):
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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        return None


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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        return None


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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        return None
