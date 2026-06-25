import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging
import time
import os
import sys

logger = logging.getLogger(__name__)

# Try to import selenium, but handle gracefully if not available
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Some features will be limited.")

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

    def _fetch_with_selenium(self, url: str, wait_time: int = 15) -> Optional[str]:
        """Fetch page content using Selenium"""
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available, falling back to requests")
            return self._fetch_page(url)

        driver = None
        try:
            chrome_options = Options()

            # Common options for both local and Render
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            # Try multiple Chrome binary locations
            chrome_paths = [
                "/usr/bin/google-chrome",  # Render
                "/usr/bin/chromium-browser",  # Render alternative
                "/usr/bin/chromium",  # Some Linux
                None  # Let webdriver-manager find it
            ]

            for chrome_path in chrome_paths:
                if chrome_path and os.path.exists(chrome_path):
                    chrome_options.binary_location = chrome_path
                    logger.info(f"Using Chrome at: {chrome_path}")
                    break

            # Try multiple ChromeDriver paths
            driver_paths = [
                "/usr/local/bin/chromedriver",  # Render
                None  # Let webdriver-manager find it
            ]

            service = None
            for driver_path in driver_paths:
                if driver_path and os.path.exists(driver_path):
                    service = Service(driver_path)
                    logger.info(f"Using ChromeDriver at: {driver_path}")
                    break

            if not service:
                # Use webdriver-manager to find ChromeDriver
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    logger.info("Using webdriver-manager for ChromeDriver")
                except:
                    # Fallback: try to create driver without service
                    pass

            if service:
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)

            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            driver.get(url)

            # Wait for page to load
            time.sleep(5)
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Scroll to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            page_source = driver.page_source
            return page_source

        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {str(e)}")
            # Fallback to requests
            return self._fetch_page(url)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

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

        numbered_pattern = r'(\d+\.\s*[^\d]+?)(?=\s*\d+\.\s*|$)'
        matches = re.findall(numbered_pattern, address)

        if len(matches) > 1:
            formatted_addresses = []
            address_counter = 1
            for match in matches:
                clean_addr = match.strip()
                clean_addr = re.sub(r'Get directions', '', clean_addr, flags=re.IGNORECASE)
                formatted_addr = self._clean_and_format_single_address(clean_addr, address_counter)
                if formatted_addr:
                    formatted_addresses.append(formatted_addr)
                    address_counter += 1

            if formatted_addresses:
                return '\n'.join(formatted_addresses)

        return self._clean_and_format_single_address(address)


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

        logger.info(f"LinkedIn extraction - Phone: {phone}, Email: {email}, Address: {office}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _extract_linkedin_addresses(self, soup: BeautifulSoup) -> Optional[str]:
        try:
            addresses = []
            seen_addresses = set()

            for i in range(10):
                address_element = soup.find(id=f'address-{i}')
                if address_element:
                    address_text = address_element.get_text(strip=True)
                    if address_text and len(address_text) > 5:
                        address_text = self._clean_address(address_text)
                        if address_text and address_text not in seen_addresses:
                            addresses.append(address_text)
                            seen_addresses.add(address_text)
                            logger.info(f"Found address-{i}: {address_text}")

            if not addresses:
                location_selectors = [
                    '.pv-top-card-section__location',
                    '.pv-top-card--list .t-black--light',
                    '[data-field="location"]',
                    '.pv-top-card .pv-top-card-section__location',
                ]

                for selector in location_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 5:
                            text = self._clean_address(text)
                            if text and text not in seen_addresses:
                                addresses.append(text)
                                seen_addresses.add(text)

            if addresses:
                filtered_addresses = []
                for addr in addresses:
                    if not any(keyword in addr.lower() for keyword in ['followers', 'following', 'posted', 'likes', 'comments']):
                        addr = re.sub(r'Get directions', '', addr, flags=re.IGNORECASE)
                        addr = re.sub(r'^Primary', '', addr, flags=re.IGNORECASE)
                        addr = addr.strip()
                        if addr:
                            filtered_addresses.append(addr)

                unique_addresses = []
                seen = set()
                for addr in filtered_addresses:
                    addr_lower = addr.lower()
                    if addr_lower not in seen:
                        unique_addresses.append(addr)
                        seen.add(addr_lower)

                if unique_addresses:
                    if len(unique_addresses) == 1:
                        return unique_addresses[0]
                    else:
                        return "\n".join(unique_addresses)

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
    """Parser for Instagram profiles"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Instagram profile: {url}")

        # Try to fetch using requests first (faster)
        page_content = self._fetch_page(url)

        if page_content:
            soup = BeautifulSoup(page_content, 'html.parser')
            text = soup.get_text()

            email = self._extract_email(text)
            phone = self._extract_phone(text)
            address = self._extract_address_from_text(text)

            if address:
                address = self._format_address_with_proper_spacing(address)

            logger.info(f"Instagram extraction - Phone: {phone}, Email: {email}, Address: {address}")

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


class FacebookParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Facebook profile: {url}")

        page_content = self._fetch_with_selenium(url, wait_time=20)

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
