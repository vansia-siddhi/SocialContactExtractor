import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging
import os

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
                    if not any(keyword in address.lower() for keyword in
                               ['followers', 'following', 'posts', 'likes', 'comments']):
                        return address[:200]
        return None

    def _is_valid_address(self, text: str) -> bool:
        """Check if text is a valid address"""
        if not text or len(text) < 8:
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
                if line and self._is_valid_address(line):
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
                if self._is_valid_address(clean_addr):
                    formatted_addr = self._clean_and_format_single_address(clean_addr, address_counter)
                    if formatted_addr:
                        formatted_addresses.append(formatted_addr)
                        address_counter += 1

            if formatted_addresses:
                return '\n'.join(formatted_addresses)

        if self._is_valid_address(address):
            return self._clean_and_format_single_address(address)

        return None


class LinkedInParser(SocialPlatformParser):
    """Parser for LinkedIn profiles - Hybrid approach (API + Fallback)"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        # Try to extract company name from URL
        company_name = self._extract_company_name(url)

        # Method 1: Try linkedin-api (if credentials are available)
        if company_name:
            api_result = self._try_linkedin_api(company_name)
            if api_result:
                return api_result

        # Method 2: Fallback to requests + BeautifulSoup
        logger.info("Falling back to requests + BeautifulSoup...")
        return self._parse_with_requests(url)

    def _try_linkedin_api(self, company_name: str) -> Optional[Dict[str, Optional[str]]]:
        """Try to extract data using linkedin-api"""
        try:
            from linkedin_api import Linkedin
            import os

            username = os.environ.get('LINKEDIN_USERNAME')
            password = os.environ.get('LINKEDIN_PASSWORD')

            if not username or not password:
                logger.warning("LinkedIn credentials not set. Skipping API method.")
                return None

            logger.info(f"Authenticating LinkedIn for company: {company_name}")
            api = Linkedin(username, password)
            company_data = api.get_company(company_name)

            if not company_data:
                logger.warning(f"No company data found for: {company_name}")
                return None

            # Extract data
            email = self._extract_email_from_data(company_data)
            phone = self._extract_phone_from_data(company_data)
            office = self._extract_address_from_data(company_data)

            if office and office != 'Not found':
                office = self._format_address_with_proper_spacing(office)

            logger.info(f"LinkedIn API extraction - Phone: {phone}, Email: {email}, Address: {office}")

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': office if office else 'Not found'
            }

        except Exception as e:
            logger.error(f"LinkedIn API error: {str(e)}")
            return None

    def _parse_with_requests(self, url: str) -> Dict[str, Optional[str]]:
        """Parse LinkedIn profile using requests + BeautifulSoup"""
        try:
            # Try different URL formats
            urls_to_try = [
                url,
                url.replace('in.linkedin.com', 'www.linkedin.com'),
                url.replace('/in/', '/'),
                url + '/about/',
                ]

            page_content = None
            for try_url in urls_to_try:
                logger.info(f"Trying URL: {try_url}")
                page_content = self._fetch_page(try_url)
                if page_content and len(page_content) > 1000:
                    break

            if not page_content:
                logger.warning(f"Failed to fetch LinkedIn page: {url}")
                return {
                    'phone': 'Not found',
                    'email': 'Not found',
                    'office': 'Not found'
                }

            soup = BeautifulSoup(page_content, 'html.parser')
            text = soup.get_text()

            # Extract email
            email = self._extract_email(text)

            # Extract phone
            phone = self._extract_phone(text)

            # Extract address
            office = self._extract_linkedin_address(soup, text)

            if office and office != 'Not found':
                office = self._format_address_with_proper_spacing(office)

            logger.info(f"Requests extraction - Phone: {phone}, Email: {email}, Address: {office}")

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': office if office else 'Not found'
            }

        except Exception as e:
            logger.error(f"Error in requests fallback: {str(e)}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

    def _extract_company_name(self, url: str) -> Optional[str]:
        """Extract company name from LinkedIn URL"""
        patterns = [
            r'linkedin\.com/company/([^/?]+)',
            r'linkedin\.com/company/([^/?]+)/',
            r'linkedin\.com/company/([^/?]+)\?',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                name = match.group(1)
                name = name.split('/')[0]
                name = name.split('?')[0]
                return name
        return None

    def _extract_linkedin_address(self, soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract address from LinkedIn using multiple methods"""
        try:
            # Method 1: Look for address-0, address-1 IDs
            for i in range(10):
                address_element = soup.find(id=f'address-{i}')
                if address_element:
                    address_text = address_element.get_text(strip=True)
                    if address_text and len(address_text) > 5:
                        address_text = self._clean_address(address_text)
                        if self._is_valid_address(address_text):
                            logger.info(f"Found address-{i}: {address_text}")
                            return address_text

            # Method 2: Look for location selectors
            location_selectors = [
                '.pv-top-card-section__location',
                '.pv-top-card--list .t-black--light',
                '[data-field="location"]',
                '.pv-top-card .pv-top-card-section__location',
                '.org-location',
                '.org-locations',
                '.pv-entity__location',
                '.pv-about-section .pv-about__summary-text',
                '.company-location',
                '.headquarters',
                '.location',
                '.address',
            ]

            for selector in location_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text_content = element.get_text(strip=True)
                    if text_content and len(text_content) > 5:
                        text_content = self._clean_address(text_content)
                        if self._is_valid_address(text_content):
                            logger.info(f"Found address from selector {selector}: {text_content}")
                            return text_content

            # Method 3: Look for address in meta tags
            meta_selectors = [
                'meta[property="og:description"]',
                'meta[name="description"]',
                'meta[property="og:title"]',
            ]

            for selector in meta_selectors:
                elements = soup.select(selector)
                for element in elements:
                    content = element.get('content', '')
                    if content:
                        address = self._extract_address_from_text(content)
                        if address and self._is_valid_address(address):
                            logger.info(f"Found address in meta: {address}")
                            return address

            # Method 4: Extract from text
            address = self._extract_address_from_text(text)
            if address and self._is_valid_address(address):
                logger.info(f"Found address from text: {address}")
                return address

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn address: {str(e)}")
            return None

    def _clean_address(self, address: str) -> str:
        """Clean up address text"""
        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)
        address = re.sub(r'\s+', ' ', address)
        address = re.sub(r';+$', '', address)
        return address.strip()

    def _extract_email_from_data(self, data: dict) -> Optional[str]:
        """Extract email from company data"""
        email_fields = ['email', 'contactEmail', 'businessEmail', 'supportEmail']
        for field in email_fields:
            if field in data and data[field]:
                return data[field]

        if 'contact_info' in data:
            contact = data['contact_info']
            if isinstance(contact, dict):
                if 'email' in contact and contact['email']:
                    return contact['email']

        if 'description' in data:
            email = self._extract_email(data['description'])
            if email:
                return email

        return None

    def _extract_phone_from_data(self, data: dict) -> Optional[str]:
        """Extract phone from company data"""
        phone_fields = ['phone', 'contactPhone', 'businessPhone', 'supportPhone']
        for field in phone_fields:
            if field in data and data[field]:
                return data[field]

        if 'contact_info' in data:
            contact = data['contact_info']
            if isinstance(contact, dict):
                if 'phone' in contact and contact['phone']:
                    return contact['phone']

        if 'description' in data:
            phone = self._extract_phone(data['description'])
            if phone:
                return phone

        return None

    def _extract_address_from_data(self, data: dict) -> Optional[str]:
        """Extract office address from company data"""
        addresses = []
        seen = set()

        if 'headquarters' in data:
            hq = data['headquarters']
            if hq:
                if isinstance(hq, dict):
                    address = hq.get('address', '')
                    if address and address not in seen:
                        addresses.append(address)
                        seen.add(address)

        if 'locations' in data:
            for loc in data['locations']:
                if isinstance(loc, dict):
                    address = loc.get('address', '')
                    if address and address not in seen:
                        addresses.append(address)
                        seen.add(address)

        if addresses:
            cleaned = []
            for addr in addresses:
                addr = re.sub(r'\s+', ' ', addr).strip()
                if addr and self._is_valid_address(addr):
                    cleaned.append(addr)

            if cleaned:
                unique = []
                seen = set()
                for addr in cleaned:
                    if addr.lower() not in seen:
                        unique.append(addr)
                        seen.add(addr.lower())

                if len(unique) == 1:
                    return unique[0]
                else:
                    formatted = []
                    for i, addr in enumerate(unique, 1):
                        formatted.append(f"{i}. {addr}")
                    return "\n".join(formatted)

        return None


# Keep the rest of the parsers unchanged
class InstagramParser(SocialPlatformParser):
    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing Instagram profile: {url}")
        page_content = self._fetch_page(url)
        if not page_content:
            return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
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
            return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
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
            return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
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
            return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
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
        return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
