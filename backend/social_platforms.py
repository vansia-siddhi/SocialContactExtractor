import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import logging
import os
import json

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
        """Check if text is a valid address (not company description)"""
        if not text or len(text) < 8:
            return False

        # Skip text with non-address keywords
        skip_keywords = ['followers', 'employee', 'developer', 'services', 'solutions',
                         'technology', 'software', 'website', 'programming', 'design',
                         'excellence', 'innovation', 'product', 'engineering', 'development',
                         'established', 'intention', 'concentrate', 'expanding', 'competitive',
                         'market', 'modern', 'technologies', 'expertise', 'portfolio',
                         'intuitive', 'solid', 'designs', 'team', 'handle', 'problems',
                         'custom-fit', 'suite', 'needs', 'discover', 'employees']
        if any(keyword in text.lower() for keyword in skip_keywords):
            return False

        address_indicators = [
            'road', 'street', 'st', 'avenue', 'ave', 'boulevard', 'blvd',
            'lane', 'ln', 'drive', 'dr', 'way', 'place', 'pl', 'court', 'ct',
            'tower', 'building', 'complex', 'park', 'centre', 'center',
            'office', 'house', 'society', 'apartment', 'floor', 'corner',
            'surat', 'mumbai', 'delhi', 'ahmedabad', 'bangalore', 'chennai',
            'kolkata', 'hyderabad', 'pune', 'gujarat', 'maharashtra',
            'india', 'meridian', 'chicago', 'texas', 'california',
            'usa', 'united states', 'uk', 'united kingdom', 'europe',
            'gj', 'mh', 'ka', 'tn', 'dl', 'wb', 'up', 'rj', 'hr', 'pb'
        ]

        has_numbers = any(char.isdigit() for char in text)
        has_address_keywords = any(keyword in text.lower() for keyword in address_indicators)

        return has_numbers or has_address_keywords

    def _clean_address(self, address: str) -> str:
        """Clean up address text"""
        if not address:
            return address

        address = re.sub(r'Get directions', '', address, flags=re.IGNORECASE)
        address = re.sub(r'^Primary', '', address, flags=re.IGNORECASE)
        address = re.sub(r'\s+', ' ', address)
        address = re.sub(r';+$', '', address)
        return address.strip()

    def _clean_and_format_single_address(self, address: str) -> str:
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

        return address

    def _format_multiple_addresses(self, addresses: List[str]) -> str:
        """Format multiple addresses with numbering and spacing"""
        if not addresses:
            return None

        cleaned_addresses = []
        seen = set()

        for addr in addresses:
            if not addr:
                continue

            clean_addr = self._clean_address(addr)

            if not clean_addr or len(clean_addr) < 5:
                continue

            if not self._is_valid_address(clean_addr):
                continue

            if clean_addr.lower() in seen:
                continue

            cleaned_addresses.append(clean_addr)
            seen.add(clean_addr.lower())

        if not cleaned_addresses:
            return None

        if len(cleaned_addresses) == 1:
            return self._clean_and_format_single_address(cleaned_addresses[0])

        formatted = []
        for i, addr in enumerate(cleaned_addresses, 1):
            formatted_addr = self._clean_and_format_single_address(addr)
            formatted.append(f"Address {i}: {formatted_addr}")

        return "\n\n".join(formatted)

    def _format_address_with_proper_spacing(self, address: str) -> str:
        """Format a single address with proper spacing"""
        if not address:
            return address
        return self._clean_and_format_single_address(address)


class LinkedInParser(SocialPlatformParser):
    """Parser for LinkedIn profiles"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing LinkedIn profile: {url}")

        company_name = self._extract_company_name(url)

        if company_name:
            api_result = self._try_linkedin_api(company_name)
            if api_result:
                return api_result

        logger.info("Falling back to requests + BeautifulSoup...")
        return self._parse_with_requests(url)

    def _try_linkedin_api(self, company_name: str) -> Optional[Dict[str, Optional[str]]]:
        try:
            from linkedin_api import Linkedin

            username = os.environ.get('LINKEDIN_USERNAME')
            password = os.environ.get('LINKEDIN_PASSWORD')

            if not username or not password:
                logger.warning("LinkedIn credentials not set.")
                return None

            api = Linkedin(username, password)
            company_data = api.get_company(company_name)

            if not company_data:
                return None

            email = self._extract_email_from_data(company_data)
            phone = self._extract_phone_from_data(company_data)
            office = self._extract_locations_from_data(company_data)

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': office if office else 'Not found'
            }

        except Exception as e:
            logger.error(f"LinkedIn API error: {str(e)}")
            return None

    def _parse_with_requests(self, url: str) -> Dict[str, Optional[str]]:
        try:
            urls_to_try = [
                url,
                url.replace('in.linkedin.com', 'www.linkedin.com'),
                url.replace('/in/', '/'),
                url + '/about/',
                ]

            page_content = None
            for try_url in urls_to_try:
                page_content = self._fetch_page(try_url)
                if page_content and len(page_content) > 1000:
                    break

            if not page_content:
                return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}

            soup = BeautifulSoup(page_content, 'html.parser')
            text = soup.get_text()

            email = self._extract_email(text)
            phone = self._extract_phone(text)
            office = self._extract_linkedin_locations(soup)

            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': office if office else 'Not found'
            }

        except Exception as e:
            logger.error(f"Error in requests fallback: {str(e)}")
            return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}

    def _extract_company_name(self, url: str) -> Optional[str]:
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

    def _extract_linkedin_locations(self, soup: BeautifulSoup) -> Optional[str]:
        all_addresses = []
        seen = set()

        try:
            locations_headers = soup.find_all(['h2', 'h3', 'h4', 'div'], string=re.compile(r'Locations|Location', re.IGNORECASE))

            for header in locations_headers:
                parent = header.parent
                if parent:
                    address_elements = parent.find_all(['div', 'span', 'p'], class_=re.compile(r'address|location|org-location', re.IGNORECASE))
                    for elem in address_elements:
                        address_text = elem.get_text(strip=True)
                        if address_text and len(address_text) > 10:
                            clean_addr = self._clean_address(address_text)
                            if clean_addr and clean_addr.lower() not in seen:
                                if self._is_valid_address(clean_addr):
                                    all_addresses.append(clean_addr)
                                    seen.add(clean_addr.lower())

            location_elements = soup.select('.org-location, .org-locations, .pv-entity__location')
            for elem in location_elements:
                address_text = elem.get_text(strip=True)
                if address_text and len(address_text) > 10:
                    clean_addr = self._clean_address(address_text)
                    if clean_addr and clean_addr.lower() not in seen:
                        if self._is_valid_address(clean_addr):
                            all_addresses.append(clean_addr)
                            seen.add(clean_addr.lower())

            for i in range(20):
                address_element = soup.find(id=f'address-{i}')
                if address_element:
                    address_text = address_element.get_text(strip=True)
                    if address_text and len(address_text) > 10:
                        clean_addr = self._clean_address(address_text)
                        if clean_addr and clean_addr.lower() not in seen:
                            if self._is_valid_address(clean_addr):
                                all_addresses.append(clean_addr)
                                seen.add(clean_addr.lower())

            if all_addresses:
                return self._format_multiple_addresses(all_addresses)

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn locations: {str(e)}")
            return None

    def _extract_locations_from_data(self, data: dict) -> Optional[str]:
        addresses = []
        seen = set()

        if 'headquarters' in data:
            hq = data['headquarters']
            if hq and isinstance(hq, dict):
                for key in ['address', 'location', 'streetAddress', 'formattedAddress']:
                    if key in hq and hq[key]:
                        addr = self._clean_address(str(hq[key]))
                        if addr and addr.lower() not in seen and self._is_valid_address(addr):
                            addresses.append(addr)
                            seen.add(addr.lower())

        if 'locations' in data:
            for loc in data['locations']:
                if isinstance(loc, dict):
                    for key in ['address', 'location', 'streetAddress', 'formattedAddress']:
                        if key in loc and loc[key]:
                            addr = self._clean_address(str(loc[key]))
                            if addr and addr.lower() not in seen and self._is_valid_address(addr):
                                addresses.append(addr)
                                seen.add(addr.lower())

        if addresses:
            return self._format_multiple_addresses(addresses)

        return None

    def _extract_email_from_data(self, data: dict) -> Optional[str]:
        email_fields = ['email', 'contactEmail', 'businessEmail', 'supportEmail']
        for field in email_fields:
            if field in data and data[field]:
                return data[field]

        if 'contact_info' in data and isinstance(data['contact_info'], dict):
            if 'email' in data['contact_info'] and data['contact_info']['email']:
                return data['contact_info']['email']

        if 'description' in data:
            email = self._extract_email(data['description'])
            if email:
                return email

        return None

    def _extract_phone_from_data(self, data: dict) -> Optional[str]:
        phone_fields = ['phone', 'contactPhone', 'businessPhone', 'supportPhone']
        for field in phone_fields:
            if field in data and data[field]:
                return data[field]

        if 'contact_info' in data and isinstance(data['contact_info'], dict):
            if 'phone' in data['contact_info'] and data['contact_info']['phone']:
                return data['contact_info']['phone']

        if 'description' in data:
            phone = self._extract_phone(data['description'])
            if phone:
                return phone

        return None


class YouTubeParser(SocialPlatformParser):
    """Parser for YouTube channels - Extracts from description"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing YouTube profile: {url}")

        # Try to get channel ID
        channel_id = self._extract_channel_id(url)
        api_key = os.environ.get('YOUTUBE_API_KEY')

        # Get description from YouTube API if possible
        description = None
        if channel_id and api_key:
            channel_data = self._fetch_channel_data(channel_id, api_key)
            if channel_data:
                description = channel_data.get('snippet', {}).get('description', '')

        # If no description from API, scrape the page
        if not description:
            logger.info("Scraping YouTube page for description...")
            description = self._scrape_description_from_page(url)

        # Extract data from description
        email = self._extract_email(description) if description else None
        phone = self._extract_phone(description) if description else None
        office = self._extract_address_from_text(description) if description else None

        # Try to get location from channel data if available
        if not office and channel_id and api_key:
            channel_data = self._fetch_channel_data(channel_id, api_key)
            if channel_data:
                office = self._extract_location_from_channel(channel_data)

        # Try to get website from channel
        if not office and channel_id and api_key:
            channel_data = self._fetch_channel_data(channel_id, api_key)
            if channel_data:
                website = self._extract_website_from_channel(channel_data)
                if website:
                    office = website

        if office and office != 'Not found':
            office = self._format_address_with_proper_spacing(office)

        logger.info(f"YouTube extraction - Phone: {phone}, Email: {email}, Office: {office}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _scrape_description_from_page(self, url: str) -> Optional[str]:
        """Scrape description from YouTube page HTML"""
        try:
            # Try different URL formats
            urls_to_try = [
                url,
                url + '/about',
                url.replace('/videos', '/about'),
                url.replace('/featured', '/about'),
                ]

            for page_url in urls_to_try:
                logger.info(f"Scraping: {page_url}")
                page_content = self._fetch_page(page_url)
                if not page_content:
                    continue

                # Try to find description in meta tags
                soup = BeautifulSoup(page_content, 'html.parser')
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')
                    if content and len(content) > 20:
                        return content

                # Try to find description in JSON-LD
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if 'description' in data:
                                return data['description']
                            if 'about' in data and isinstance(data['about'], dict):
                                if 'description' in data['about']:
                                    return data['about']['description']
                    except:
                        pass

                # Try to find description in the page text
                text = soup.get_text()
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and len(line) > 30:
                        # Check if it contains email, phone, or address patterns
                        if (re.search(r'@', line) or
                                re.search(r'\+91|\d{10}', line) or
                                re.search(r'Road|Street|Tower|Building|Surat|Mumbai|Gujarat', line, re.IGNORECASE)):
                            return line

                # Check if we have any text content that looks like a description
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 30 and len(line) < 500:
                        if not any(keyword in line.lower() for keyword in ['subscribe', 'views', 'subscribers', 'videos', 'share', 'like']):
                            return line

            return None

        except Exception as e:
            logger.error(f"Error scraping description: {str(e)}")
            return None

    def _extract_channel_id(self, url: str) -> Optional[str]:
        patterns = [
            r'youtube\.com/channel/([^/?]+)',
            r'youtube\.com/c/([^/?]+)',
            r'youtube\.com/@([^/?]+)',
            r'youtube\.com/user/([^/?]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                identifier = match.group(1)
                if url.count('@') > 0 or pattern == r'youtube\.com/@([^/?]+)':
                    return self._handle_to_channel_id(identifier)
                return identifier

        return None

    def _handle_to_channel_id(self, handle: str) -> Optional[str]:
        try:
            api_key = os.environ.get('YOUTUBE_API_KEY')
            if not api_key:
                return None

            search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={handle}&type=channel&key={api_key}"
            response = requests.get(search_url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    return data['items'][0]['snippet']['channelId']
            return None

        except Exception as e:
            logger.error(f"Error converting handle to channel ID: {str(e)}")
            return None

    def _fetch_channel_data(self, channel_id: str, api_key: str) -> Optional[dict]:
        try:
            url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails,brandingSettings,status,topicDetails&id={channel_id}&key={api_key}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('items') and len(data['items']) > 0:
                    return data['items'][0]
            return None

        except Exception as e:
            logger.error(f"Error fetching channel data: {str(e)}")
            return None

    def _extract_location_from_channel(self, channel_data: dict) -> Optional[str]:
        try:
            branding = channel_data.get('brandingSettings', {})
            channel = branding.get('channel', {})

            if 'country' in channel and channel['country']:
                return channel['country']

            snippet = channel_data.get('snippet', {})
            if 'country' in snippet and snippet['country']:
                return snippet['country']

            return None

        except Exception as e:
            logger.error(f"Error extracting location: {str(e)}")
            return None

    def _extract_website_from_channel(self, channel_data: dict) -> Optional[str]:
        try:
            branding = channel_data.get('brandingSettings', {})
            links = branding.get('links', [])

            for link in links:
                url = link.get('url', '')
                if url and 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
                    return url

            description = channel_data.get('snippet', {}).get('description', '')
            if description:
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', description)
                for url in urls:
                    if url and 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
                        return url

            return None

        except Exception as e:
            logger.error(f"Error extracting website: {str(e)}")
            return None


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
            address = self._format_multiple_addresses([address]) if isinstance(address, str) else address
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
            address = self._format_multiple_addresses([address]) if isinstance(address, str) else address
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
            address = self._format_multiple_addresses([address]) if isinstance(address, str) else address
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
                address = self._format_multiple_addresses([address]) if isinstance(address, str) else address
            return {
                'phone': phone if phone else 'Not found',
                'email': email if email else 'Not found',
                'office': address if address else 'Not found'
            }
        return {'phone': 'Not found', 'email': 'Not found', 'office': 'Not found'}
