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
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def _fetch_with_selenium(self, url: str, wait_time: int = 15) -> Optional[str]:
        """Fetch page content using Selenium with better waiting"""
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
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            driver.get(url)

            # Wait for page to load with longer timeout
            time.sleep(5)
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Scroll down to load more content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Get page source
            page_source = driver.page_source
            return page_source

        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()

    def _fetch_instagram_with_visible_browser(self, url: str) -> Optional[dict]:
        """
        Fetch Instagram profile using visible browser (non-headless)
        User must be logged in to Instagram for this to work
        """
        driver = None
        result = {
            'page_source': None,
            'phone': None,
            'email': None,
            'address': None
        }

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            chrome_options = Options()
            # DON'T use headless - Instagram detects it
            # chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,1024")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Opening Instagram profile in browser...")
            driver.get(url)

            # Wait for page to load
            time.sleep(5)
            wait = WebDriverWait(driver, 30)

            # Check if we're on login page
            current_url = driver.current_url
            if "login" in current_url or "accounts/login" in current_url:
                logger.warning("=" * 60)
                logger.warning("Instagram LOGIN REQUIRED!")
                logger.warning("Please login to Instagram in the browser window that opened.")
                logger.warning("You have 60 seconds to login manually.")
                logger.warning("=" * 60)

                # Wait for user to login (60 seconds)
                time.sleep(60)

                # Refresh the page after login
                logger.info("Refreshing page after login...")
                driver.refresh()
                time.sleep(5)

            # Wait for profile to load
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)
            except:
                pass

            # Scroll to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Try multiple methods to find Contact button
            contact_found = False

            # Method 1: Look for Contact button
            contact_selectors = [
                "//button[contains(text(), 'Contact')]",
                "//div[contains(text(), 'Contact')]",
                "//span[contains(text(), 'Contact')]",
                "//button[contains(@aria-label, 'Contact')]",
                "//div[@role='button' and contains(text(), 'Contact')]",
                "//a[contains(text(), 'Contact')]",
                "//button[contains(@class, 'x1i10hfl')]//span[contains(text(), 'Contact')]",
            ]

            contact_button = None
            for selector in contact_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element and element.is_displayed():
                            contact_button = element
                            logger.info(f"Found Contact button")
                            break
                    if contact_button:
                        break
                except:
                    continue

            # If Contact button found, click it
            if contact_button:
                try:
                    logger.info("Clicking Contact button...")
                    driver.execute_script("arguments[0].click();", contact_button)
                    time.sleep(3)
                    contact_found = True
                except Exception as e:
                    logger.error(f"Error clicking Contact button: {str(e)}")

            # Try to find contact links (mailto: or tel:)
            if not contact_found:
                try:
                    contact_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:') or contains(@href, 'tel:')]")
                    if contact_links:
                        logger.info("Found contact links directly")
                        for link in contact_links:
                            href = link.get_attribute('href')
                            if href:
                                if 'mailto:' in href:
                                    result['email'] = href.replace('mailto:', '').strip()
                                    logger.info(f"Found email: {result['email']}")
                                elif 'tel:' in href:
                                    result['phone'] = href.replace('tel:', '').strip()
                                    logger.info(f"Found phone: {result['phone']}")
                except:
                    pass

            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            text = soup.get_text()

            # Extract data from page
            if not result['email']:
                email = self._extract_email(text)
                if email:
                    result['email'] = email
                    logger.info(f"Found email: {email}")

            if not result['phone']:
                phone = self._extract_phone(text)
                if phone:
                    result['phone'] = phone
                    logger.info(f"Found phone: {phone}")

            # Extract address
            address = self._extract_address_from_text(text)
            if address:
                result['address'] = address
                logger.info(f"Found address: {address}")

            # Try specific address selectors
            if not result['address']:
                address_selectors = [
                    "//div[contains(text(), 'Address')]/following-sibling::div",
                    "//div[contains(text(), 'Address')]/following-sibling::span",
                    "//span[contains(text(), 'Address')]/following-sibling::span",
                    "//div[contains(text(), 'Floor')]",
                    "//div[contains(text(), 'Tower')]",
                    "//div[contains(text(), 'Building')]",
                    "//div[contains(text(), 'Society')]",
                    "//div[contains(text(), 'Surat')]",
                    "//div[contains(text(), 'Gujarat')]",
                    "//span[contains(text(), 'Surat')]",
                ]

                for selector in address_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            text_content = element.text.strip()
                            if text_content and len(text_content) > 10:
                                if any(keyword in text_content.lower() for keyword in
                                       ['road', 'street', 'tower', 'building', 'floor', 'society',
                                        'surat', 'mumbai', 'ahmedabad', 'gujarat', 'complex', 'meridian']):
                                    result['address'] = text_content
                                    logger.info(f"Found address: {text_content}")
                                    break
                        if result['address']:
                            break
                    except:
                        continue

            # Get final page source
            result['page_source'] = driver.page_source

            logger.info("Closing browser in 5 seconds...")
            time.sleep(5)

            return result

        except Exception as e:
            logger.error(f"Error in Instagram fetch: {str(e)}")
            return result
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

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract address from text with more patterns"""
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

    def _is_follower_count(self, text: str) -> bool:
        """Check if text is a follower/following/post count"""
        text_lower = text.lower()
        follower_keywords = ['followers', 'following', 'posts', 'post', 'likes', 'comments', 'views', 'reactions', 'shares']
        for keyword in follower_keywords:
            if keyword in text_lower:
                return True
        if re.search(r'[\d,]+[\s]+(?:followers|following|posts|post)', text_lower):
            return True
        return False

    def _is_bio_text(self, text: str) -> bool:
        """Check if text is likely bio/description text (not address)"""
        text_lower = text.lower()
        bio_keywords = ['excellence', 'innovation', 'product', 'engineering', 'development', 'software', 'solutions', 'services', 'technology', 'digital', 'transformation', 'consulting', 'agency', 'creative', 'design', 'marketing', 'brand', 'strategy', 'management', 'business', 'consultant', 'professional', 'expert', 'leader', 'vision', 'mission', 'culture', 'values', 'team', 'work', 'career', 'opportunity', 'growth', 'success', 'quality', 'commitment', 'passion', 'dedicated', 'experienced', 'specialized', 'providing', 'delivering', 'helping', 'building', 'creating', 'driving', 'leading', 'ui/ux', 'e-commerce', 'cms', 'web']

        for keyword in bio_keywords:
            if keyword in text_lower:
                return True
        return False

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
                if line and not self._is_follower_count(line) and not self._is_bio_text(line):
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
                if not self._is_follower_count(clean_addr) and not self._is_bio_text(clean_addr):
                    formatted_addr = self._clean_and_format_single_address(clean_addr, address_counter)
                    if formatted_addr:
                        formatted_addresses.append(formatted_addr)
                        address_counter += 1

            if formatted_addresses:
                return '\n'.join(formatted_addresses)

        if not self._is_follower_count(address) and not self._is_bio_text(address):
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
                    if not self._is_follower_count(addr):
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
    """Parser for Instagram profiles - Uses visible browser (requires login)"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Instagram profile: {url}")

        # Use visible browser to fetch Instagram
        result = self._fetch_instagram_with_visible_browser(url)

        if not result or not result.get('page_source'):
            logger.warning(f"Failed to fetch Instagram page: {url}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        # Get data from result
        phone = result.get('phone')
        email = result.get('email')
        address = result.get('address')

        # Clean up phone number format
        if phone and phone != 'Not found':
            # Remove any non-digit characters except +
            phone = re.sub(r'[^0-9+]', '', phone)
            if len(phone) == 10 and phone.isdigit():
                phone = f"+91 {phone[:5]} {phone[5:]}"
            elif len(phone) == 11 and phone.startswith('0'):
                phone = f"+91 {phone[1:6]} {phone[6:]}"
            elif len(phone) == 12 and phone.startswith('91'):
                phone = f"+91 {phone[2:7]} {phone[7:]}"

        # Clean up address
        if address and address != 'Not found':
            # Remove "more" if it appears at the beginning
            address = re.sub(r'^more\s*', '', address, flags=re.IGNORECASE)
            # Fix "3 rd" to "3rd"
            address = re.sub(r'(\d+)\s+rd', r'\1rd', address, flags=re.IGNORECASE)
            # Fix "3 rd Floor" to "3rd Floor"
            address = re.sub(r'(\d+)\s+rd\s+Floor', r'\1rd Floor', address, flags=re.IGNORECASE)
            address = address.strip()

        # Format address if found
        if address and address != 'Not found' and len(address) > 5:
            address = self._format_address_with_proper_spacing(address)

        logger.info(f"Final extracted data - Phone: {phone}, Email: {email}, Address: {address}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': address if address else 'Not found'
        }

    def _fetch_instagram_with_visible_browser(self, url: str) -> Optional[dict]:
        """
        Fetch Instagram profile using visible browser (non-headless)
        User must be logged in to Instagram for this to work
        """
        driver = None
        result = {
            'page_source': None,
            'phone': None,
            'email': None,
            'address': None
        }

        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service

            chrome_options = Options()
            # DON'T use headless - Instagram detects it
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,1024")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Opening Instagram profile in browser...")
            driver.get(url)

            # Wait for page to load
            time.sleep(5)
            wait = WebDriverWait(driver, 30)

            # Check if we're on login page
            current_url = driver.current_url
            if "login" in current_url or "accounts/login" in current_url:
                logger.warning("=" * 60)
                logger.warning("Instagram LOGIN REQUIRED!")
                logger.warning("Please login to Instagram in the browser window that opened.")
                logger.warning("You have 60 seconds to login manually.")
                logger.warning("=" * 60)

                # Wait for user to login (60 seconds)
                time.sleep(60)

                # Refresh the page after login
                logger.info("Refreshing page after login...")
                driver.refresh()
                time.sleep(5)

            # Wait for profile to load
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)
            except:
                pass

            # Scroll to load content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Try multiple methods to find and click Contact button
            contact_found = False

            # Method 1: Look for Contact button
            contact_selectors = [
                "//button[contains(text(), 'Contact')]",
                "//div[contains(text(), 'Contact')]",
                "//span[contains(text(), 'Contact')]",
                "//button[contains(@aria-label, 'Contact')]",
                "//div[@role='button' and contains(text(), 'Contact')]",
                "//a[contains(text(), 'Contact')]",
                "//button[contains(@class, 'x1i10hfl')]//span[contains(text(), 'Contact')]",
                "//div[contains(@class, 'x1i10hfl')]//span[contains(text(), 'Contact')]",
                "//button[contains(@class, '_acan')]//span[contains(text(), 'Contact')]",
                "//div[contains(@class, '_acan')]//span[contains(text(), 'Contact')]",
                "//button[contains(@class, 'x1i10hfl') and contains(., 'Contact')]",
                "//div[contains(@class, 'x1i10hfl') and contains(., 'Contact')]",
                # Try to find by aria-label
                "//button[@aria-label='Contact']",
                "//div[@aria-label='Contact']",
            ]

            contact_button = None
            for selector in contact_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element and element.is_displayed():
                            contact_button = element
                            logger.info(f"Found Contact button")
                            break
                    if contact_button:
                        break
                except Exception as e:
                    continue

            # If Contact button found, click it
            if contact_button:
                try:
                    logger.info("Clicking Contact button...")
                    # Click using JavaScript to ensure it works
                    driver.execute_script("arguments[0].click();", contact_button)
                    time.sleep(5)  # Wait for modal to appear
                    contact_found = True
                except Exception as e:
                    logger.error(f"Error clicking Contact button: {str(e)}")

            # If Contact button clicked, look for contact info
            if contact_found:
                logger.info("Looking for contact information...")

                try:
                    # Try to find the modal
                    modal = None
                    try:
                        modal = driver.find_element(By.XPATH, "//div[@role='dialog']")
                        logger.info("Found modal dialog")
                    except:
                        # Try to find the contact info section
                        try:
                            modal = driver.find_element(By.XPATH, "//div[contains(@class, 'x1n2onr6')]//div[contains(text(), 'Email')]/..")
                            logger.info("Found contact info section")
                        except:
                            pass

                    # If we found the modal or contact section, extract data
                    if modal:
                        # Get all text from the modal
                        modal_text = modal.text
                        logger.info(f"Modal text: {modal_text}")

                        # Extract email
                        email = self._extract_email(modal_text)
                        if email:
                            result['email'] = email
                            logger.info(f"Found email: {email}")

                        # Extract phone
                        phone = self._extract_phone(modal_text)
                        if phone:
                            result['phone'] = phone
                            logger.info(f"Found phone: {phone}")

                        # Extract address - look for specific patterns
                        address = self._extract_address_from_text(modal_text)
                        if address:
                            result['address'] = address
                            logger.info(f"Found address: {address}")

                        # If no address found, try to find it from modal text
                        if not result['address']:
                            # Look for address patterns in modal
                            lines = modal_text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and len(line) > 10:
                                    # Check if it looks like an address
                                    if any(keyword in line.lower() for keyword in
                                           ['floor', 'tower', 'building', 'society', 'road', 'street',
                                            'surat', 'gujarat', 'meridian', 'complex', 'avenue', 'lane']):
                                        result['address'] = line
                                        logger.info(f"Found address from line: {line}")
                                        break

                    # If modal not found or no data, try direct extraction from page
                    if not result['phone'] and not result['email'] and not result['address']:
                        logger.info("No data found in modal, trying direct extraction...")
                        page_source = driver.page_source
                        soup = BeautifulSoup(page_source, 'html.parser')
                        text = soup.get_text()

                        # Extract email
                        email = self._extract_email(text)
                        if email:
                            result['email'] = email
                            logger.info(f"Found email from page: {email}")

                        # Extract phone
                        phone = self._extract_phone(text)
                        if phone:
                            result['phone'] = phone
                            logger.info(f"Found phone from page: {phone}")

                        # Extract address
                        address = self._extract_address_from_text(text)
                        if address:
                            result['address'] = address
                            logger.info(f"Found address from page: {address}")

                        # If still no address, look for specific patterns in text
                        if not result['address']:
                            lines = text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and len(line) > 10:
                                    if any(keyword in line.lower() for keyword in
                                           ['floor', 'tower', 'building', 'society', 'road', 'street',
                                            'surat', 'gujarat', 'meridian', 'complex']):
                                        result['address'] = line
                                        logger.info(f"Found address from page line: {line}")
                                        break

                except Exception as e:
                    logger.error(f"Error extracting from modal: {str(e)}")

            # If no contact button found or no data extracted, try direct extraction
            if not contact_found or not result['phone'] and not result['email'] and not result['address']:
                logger.info("Contact button not found or no data, trying direct extraction...")
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                text = soup.get_text()

                # Try to find email
                email = self._extract_email(text)
                if email and not result['email']:
                    result['email'] = email
                    logger.info(f"Found email from page: {email}")

                # Try to find phone
                phone = self._extract_phone(text)
                if phone and not result['phone']:
                    result['phone'] = phone
                    logger.info(f"Found phone from page: {phone}")

                # Try to find address
                address = self._extract_address_from_text(text)
                if address and not result['address']:
                    result['address'] = address
                    logger.info(f"Found address from page: {address}")

                # If still no address, look for specific patterns
                if not result['address']:
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 10:
                            if any(keyword in line.lower() for keyword in
                                   ['floor', 'tower', 'building', 'society', 'road', 'street',
                                    'surat', 'gujarat', 'meridian', 'complex']):
                                result['address'] = line
                                logger.info(f"Found address from line: {line}")
                                break

            # Log final results
            logger.info(f"Final extracted data - Phone: {result['phone']}, Email: {result['email']}, Address: {result['address']}")

            # Get final page source
            result['page_source'] = driver.page_source

            logger.info("Closing browser in 5 seconds...")
            time.sleep(5)

            return result

        except Exception as e:
            logger.error(f"Error in Instagram fetch: {str(e)}")
            import traceback
            traceback.print_exc()
            return result
        finally:
            if driver:
                driver.quit()


class FacebookParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Facebook profile: {url}")

        page_content = self._fetch_with_selenium(url, wait_time=20)

        if not page_content:
            logger.warning(f"Failed to fetch Facebook page: {url}")
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
