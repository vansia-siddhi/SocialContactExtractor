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
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
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
    """Parser for LinkedIn profiles using linkedin-api"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        # Extract company name from URL
        company_name = self._extract_company_name(url)
        if not company_name:
            logger.warning(f"Could not extract company name from URL: {url}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        try:
            from linkedin_api import Linkedin

            # Get credentials from environment variables
            username = os.environ.get('LINKEDIN_USERNAME')
            password = os.environ.get('LINKEDIN_PASSWORD')

            if not username or not password:
                logger.error("LinkedIn credentials not set in environment variables")
                return {
                    'phone': 'Not found',
                    'email': 'Not found',
                    'office': 'Not found'
                }

            # Authenticate and get company data
            logger.info(f"Authenticating LinkedIn for company: {company_name}")
            api = Linkedin(username, password)
            company_data = api.get_company(company_name)

            if not company_data:
                logger.warning(f"No company data found for: {company_name}")
                return {
                    'phone': 'Not found',
                    'email': 'Not found',
                    'office': 'Not found'
                }

            # Extract data
            email = self._extract_email_from_data(company_data)
            phone = self._extract_phone_from_data(company_data)
            office = self._extract_address_from_data(company_data)

            if office and office != 'Not found':
                office = self._format_address_with_proper_spacing(office)

            logger.info(f"LinkedIn extraction - Phone: {phone}, Email: {email}, Address: {office}")

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': office if office else 'Not found'
            }

        except Exception as e:
            logger.error(f"Error extracting LinkedIn data: {str(e)}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

    def _extract_company_name(self, url: str) -> Optional[str]:
        """Extract company name from LinkedIn URL"""
        # Pattern for company URL: linkedin.com/company/{company-name}
        match = re.search(r'linkedin\.com/company/([^/?]+)', url)
        if match:
            return match.group(1)

        # Also check for company URL: linkedin.com/company/{company-name}/about
        match = re.search(r'linkedin\.com/company/([^/?]+)/', url)
        if match:
            return match.group(1)

        return None

    def _extract_email_from_data(self, data: dict) -> Optional[str]:
        """Extract email from company data"""
        # Try common email fields
        email_fields = ['email', 'contactEmail', 'businessEmail', 'supportEmail']
        for field in email_fields:
            if field in data and data[field]:
                return data[field]

        # Check in contact_info
        if 'contact_info' in data:
            contact = data['contact_info']
            if isinstance(contact, dict):
                if 'email' in contact and contact['email']:
                    return contact['email']
                if 'contactEmail' in contact and contact['contactEmail']:
                    return contact['contactEmail']

        # Check in description for email pattern
        if 'description' in data:
            email = self._extract_email(data['description'])
            if email:
                return email

        return None

    def _extract_phone_from_data(self, data: dict) -> Optional[str]:
        """Extract phone from company data"""
        # Try common phone fields
        phone_fields = ['phone', 'contactPhone', 'businessPhone', 'supportPhone']
        for field in phone_fields:
            if field in data and data[field]:
                return data[field]

        # Check in contact_info
        if 'contact_info' in data:
            contact = data['contact_info']
            if isinstance(contact, dict):
                if 'phone' in contact and contact['phone']:
                    return contact['phone']
                if 'contactPhone' in contact and contact['contactPhone']:
                    return contact['contactPhone']

        # Check in description for phone pattern
        if 'description' in data:
            phone = self._extract_phone(data['description'])
            if phone:
                return phone

        return None

    def _extract_address_from_data(self, data: dict) -> Optional[str]:
        """Extract office address from company data"""
        addresses = []
        seen = set()

        # Check headquarters
        if 'headquarters' in data:
            hq = data['headquarters']
            if hq:
                if isinstance(hq, dict):
                    address = hq.get('address', '')
                    if address and address not in seen:
                        addresses.append(address)
                        seen.add(address)
                    # Also check location fields
                    for key in ['location', 'streetAddress', 'addressLine1', 'formattedAddress']:
                        if key in hq and hq[key] and hq[key] not in seen:
                            addresses.append(hq[key])
                            seen.add(hq[key])

        # Check locations
        if 'locations' in data:
            for loc in data['locations']:
                if isinstance(loc, dict):
                    address = loc.get('address', '')
                    if address and address not in seen:
                        addresses.append(address)
                        seen.add(address)
                    # Also check location fields
                    for key in ['location', 'streetAddress', 'addressLine1', 'formattedAddress']:
                        if key in loc and loc[key] and loc[key] not in seen:
                            addresses.append(loc[key])
                            seen.add(loc[key])

        # Check address in about section
        if 'about' in data:
            about = data['about']
            if isinstance(about, dict):
                for key in ['address', 'location', 'headquarters', 'streetAddress']:
                    if key in about and about[key] and about[key] not in seen:
                        addresses.append(about[key])
                        seen.add(about[key])

        # Check for address in description
        if 'description' in data:
            address = self._extract_address_from_text(data['description'])
            if address and address not in seen:
                addresses.append(address)
                seen.add(address)

        # Check for address in company name (sometimes includes location)
        if 'companyName' in data or 'name' in data:
            name = data.get('companyName') or data.get('name', '')
            address = self._extract_address_from_text(name)
            if address and address not in seen:
                addresses.append(address)
                seen.add(address)

        if addresses:
            # Clean up addresses
            cleaned_addresses = []
            for addr in addresses:
                # Remove extra spaces
                addr = re.sub(r'\s+', ' ', addr).strip()
                # Remove duplicate "Get directions"
                addr = re.sub(r'Get directions', '', addr, flags=re.IGNORECASE)
                # Remove "Primary" prefix
                addr = re.sub(r'^Primary', '', addr, flags=re.IGNORECASE)
                if addr and self._is_valid_address(addr):
                    cleaned_addresses.append(addr)

            if cleaned_addresses:
                # Remove duplicates (case insensitive)
                unique = []
                seen = set()
                for addr in cleaned_addresses:
                    if addr.lower() not in seen:
                        unique.append(addr)
                        seen.add(addr.lower())

                if len(unique) == 1:
                    return unique[0]
                else:
                    # Format with numbering
                    formatted = []
                    for i, addr in enumerate(unique, 1):
                        formatted.append(f"{i}. {addr}")
                    return "\n".join(formatted)

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

        address = None
        bio_selectors = ['.bio', '._aaqe', '.x9f619']
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
