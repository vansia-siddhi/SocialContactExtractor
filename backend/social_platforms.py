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

        # Must have either numbers OR address keywords to be considered an address
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

    def _format_multiple_addresses(self, addresses: List[str]) -> str:
        """Format multiple addresses with numbering and spacing"""
        if not addresses:
            return None

        # Clean and validate each address
        cleaned_addresses = []
        seen = set()

        for addr in addresses:
            if not addr:
                continue

            clean_addr = self._clean_address(addr)

            if not clean_addr or len(clean_addr) < 5:
                continue

            # Skip if it contains non-address keywords
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

        # Format with "Address X:" numbering
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
    """Parser for LinkedIn profiles - Extracts ONLY location/address data"""

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
            office = self._extract_locations_from_data(company_data)

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

            # Extract ONLY locations/addresses
            office = self._extract_linkedin_locations(soup)

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

    def _extract_linkedin_locations(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract ONLY locations/addresses from LinkedIn"""
        all_addresses = []
        seen = set()

        try:
            # Method 1: Look for location section with "Locations" heading
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
                                    logger.info(f"Found location from section: {clean_addr}")

            # Method 2: Look for org-location elements
            location_elements = soup.select('.org-location, .org-locations, .pv-entity__location')
            for elem in location_elements:
                address_text = elem.get_text(strip=True)
                if address_text and len(address_text) > 10:
                    clean_addr = self._clean_address(address_text)
                    if clean_addr and clean_addr.lower() not in seen:
                        if self._is_valid_address(clean_addr):
                            all_addresses.append(clean_addr)
                            seen.add(clean_addr.lower())
                            logger.info(f"Found location from org-location: {clean_addr}")

            # Method 3: Look for address-0, address-1 IDs
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
                                logger.info(f"Found address-{i}: {clean_addr}")

            # Method 4: Look for "Get directions" links
            directions_links = soup.find_all('a', string=re.compile(r'Get directions', re.IGNORECASE))
            for link in directions_links:
                parent = link.parent
                if parent:
                    address_text = parent.get_text(strip=True)
                    address_text = re.sub(r'Get directions', '', address_text, flags=re.IGNORECASE)
                    address_text = address_text.strip()
                    if address_text and len(address_text) > 10:
                        clean_addr = self._clean_address(address_text)
                        if clean_addr and clean_addr.lower() not in seen:
                            if self._is_valid_address(clean_addr):
                                all_addresses.append(clean_addr)
                                seen.add(clean_addr.lower())
                                logger.info(f"Found location from 'Get directions': {clean_addr}")

            # Format addresses
            if all_addresses:
                return self._format_multiple_addresses(all_addresses)

            return None

        except Exception as e:
            logger.error(f"Error extracting LinkedIn locations: {str(e)}")
            return None

    def _extract_locations_from_data(self, data: dict) -> Optional[str]:
        """Extract ONLY locations from company data (API method)"""
        addresses = []
        seen = set()

        # Check headquarters
        if 'headquarters' in data:
            hq = data['headquarters']
            if hq:
                if isinstance(hq, dict):
                    for key in ['address', 'location', 'streetAddress', 'formattedAddress']:
                        if key in hq and hq[key]:
                            addr = self._clean_address(str(hq[key]))
                            if addr and addr.lower() not in seen and self._is_valid_address(addr):
                                addresses.append(addr)
                                seen.add(addr.lower())

        # Check locations
        if 'locations' in data:
            for loc in data['locations']:
                if isinstance(loc, dict):
                    location_name = loc.get('name', '')
                    for key in ['address', 'location', 'streetAddress', 'formattedAddress']:
                        if key in loc and loc[key]:
                            addr = self._clean_address(str(loc[key]))
                            if addr and addr.lower() not in seen and self._is_valid_address(addr):
                                if location_name and location_name not in addr:
                                    addr = f"{location_name}: {addr}"
                                addresses.append(addr)
                                seen.add(addr.lower())

        if addresses:
            return self._format_multiple_addresses(addresses)

        return None

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


class YouTubeParser(SocialPlatformParser):
    """Parser for YouTube channels using YouTube Data API v3"""

    def parse(self, url: str) -> Dict[str, Optional[str]]:
        logger.info(f"Parsing YouTube profile: {url}")

        # Extract channel ID from URL
        channel_id = self._extract_channel_id(url)
        if not channel_id:
            logger.warning(f"Could not extract channel ID from URL: {url}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        # Get API key from environment variable
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            logger.error("YouTube API key not set. Please set YOUTUBE_API_KEY environment variable.")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        # Fetch channel data from YouTube API
        channel_data = self._fetch_channel_data(channel_id, api_key)
        if not channel_data:
            logger.warning(f"Failed to fetch channel data for: {channel_id}")
            return {
                'phone': 'Not found',
                'email': 'Not found',
                'office': 'Not found'
            }

        # Extract data from channel response
        email = self._extract_email_from_channel(channel_data)
        phone = self._extract_phone_from_channel(channel_data)
        office = self._extract_location_from_channel(channel_data)

        # If no email found, try to extract from description
        if not email:
            description = channel_data.get('snippet', {}).get('description', '')
            email = self._extract_email(description)

        # If no location found, try to extract from description
        if not office:
            description = channel_data.get('snippet', {}).get('description', '')
            office = self._extract_address_from_text(description)

        # Try to get website from channel
        website = self._extract_website_from_channel(channel_data)
        if not office and website:
            office = website

        if office and office != 'Not found':
            office = self._format_address_with_proper_spacing(office)

        logger.info(f"YouTube extraction - Phone: {phone}, Email: {email}, Office: {office}")

        return {
            'phone': phone if phone else 'Not found',
            'email': email if email else 'Not found',
            'office': office if office else 'Not found'
        }

    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from YouTube URL"""
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
                # If it's a handle (@), we need to convert it to channel ID
                if url.count('@') > 0 or pattern == r'youtube\.com/@([^/?]+)':
                    return self._handle_to_channel_id(identifier)
                return identifier

        return None

    def _handle_to_channel_id(self, handle: str) -> Optional[str]:
        """Convert YouTube handle to channel ID using API"""
        try:
            api_key = os.environ.get('YOUTUBE_API_KEY')
            if not api_key:
                return None

            # Use search API to find channel by handle
            search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={handle}&type=channel&key={api_key}"
            response = requests.get(search_url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    # Return first result
                    return data['items'][0]['snippet']['channelId']
            return None

        except Exception as e:
            logger.error(f"Error converting handle to channel ID: {str(e)}")
            return None

    def _fetch_channel_data(self, channel_id: str, api_key: str) -> Optional[dict]:
        """Fetch channel data from YouTube API"""
        try:
            # Get channel details including branding settings
            url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails,brandingSettings,status,topicDetails&id={channel_id}&key={api_key}"

            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get('items') and len(data['items']) > 0:
                    return data['items'][0]
                else:
                    logger.warning(f"No channel found for ID: {channel_id}")
                    return None
            else:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching channel data: {str(e)}")
            return None

    def _extract_email_from_channel(self, channel_data: dict) -> Optional[str]:
        """Extract email from channel data"""
        try:
            # Check branding settings for email
            branding = channel_data.get('brandingSettings', {})
            channel = branding.get('channel', {})

            # Check for email in various fields
            email_fields = ['email', 'contactEmail', 'businessEmail']
            for field in email_fields:
                if field in channel and channel[field]:
                    return channel[field]

            # Check description for email
            description = channel_data.get('snippet', {}).get('description', '')
            if description:
                email = self._extract_email(description)
                if email:
                    return email

            # Check for email in links
            links = branding.get('links', [])
            for link in links:
                if 'mailto:' in link.get('url', '').lower():
                    email = link['url'].replace('mailto:', '').strip()
                    if email:
                        return email

            return None

        except Exception as e:
            logger.error(f"Error extracting email from channel: {str(e)}")
            return None

    def _extract_phone_from_channel(self, channel_data: dict) -> Optional[str]:
        """Extract phone number from channel data"""
        try:
            # Check description for phone
            description = channel_data.get('snippet', {}).get('description', '')
            if description:
                phone = self._extract_phone(description)
                if phone:
                    return phone

            # Check branding settings
            branding = channel_data.get('brandingSettings', {})
            channel = branding.get('channel', {})
            if 'phone' in channel and channel['phone']:
                return channel['phone']

            return None

        except Exception as e:
            logger.error(f"Error extracting phone from channel: {str(e)}")
            return None

    def _extract_location_from_channel(self, channel_data: dict) -> Optional[str]:
        """Extract location from channel data"""
        try:
            # Check branding settings for location
            branding = channel_data.get('brandingSettings', {})
            channel = branding.get('channel', {})

            # Check for location/country
            if 'country' in channel and channel['country']:
                return channel['country']

            # Check snippet for country
            snippet = channel_data.get('snippet', {})
            if 'country' in snippet and snippet['country']:
                return snippet['country']

            # Check description for location
            description = snippet.get('description', '')
            if description:
                # Look for location patterns
                location_patterns = [
                    r'[Ll]ocation[\s:]+([A-Za-z\s,]+)',
                    r'[Cc]ountry[\s:]+([A-Za-z\s,]+)',
                    r'[Ff]rom[\s:]+([A-Za-z\s,]+)',
                ]

                for pattern in location_patterns:
                    matches = re.findall(pattern, description)
                    if matches:
                        location = matches[0].strip()
                        if len(location) > 2 and len(location) < 100:
                            return location

            return None

        except Exception as e:
            logger.error(f"Error extracting location from channel: {str(e)}")
            return None

    def _extract_website_from_channel(self, channel_data: dict) -> Optional[str]:
        """Extract website from channel data"""
        try:
            # Check branding settings for links
            branding = channel_data.get('brandingSettings', {})
            links = branding.get('links', [])

            for link in links:
                url = link.get('url', '')
                if url and 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
                    return url

            # Check description for website
            description = channel_data.get('snippet', {}).get('description', '')
            if description:
                urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', description)
                for url in urls:
                    if url and 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
                        return url

            return None

        except Exception as e:
            logger.error(f"Error extracting website from channel: {str(e)}")
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
