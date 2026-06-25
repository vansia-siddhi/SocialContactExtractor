import re
import json
from typing import Dict, Any
from datetime import datetime

class ContactFormatter:
    """Utility class for formatting contact details"""

    @staticmethod
    def format_phone(phone: str) -> str:
        """Format phone number"""
        # Remove all non-numeric characters
        cleaned = re.sub(r'[^\d+]', '', phone)

        if len(cleaned) == 10:
            return f"+91 {cleaned[:5]} {cleaned[5:]}"
        elif len(cleaned) == 11 and cleaned.startswith('0'):
            return f"+91 {cleaned[1:6]} {cleaned[6:]}"
        elif len(cleaned) == 12 and cleaned.startswith('91'):
            return f"+{cleaned[:2]} {cleaned[2:7]} {cleaned[7:]}"
        return phone

    @staticmethod
    def format_email(email: str) -> str:
        """Validate and format email"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return email.lower()
        return email

class DataManager:
    """Manage data storage and retrieval"""

    def __init__(self, data_file='data/extracted_contacts.json'):
        self.data_file = data_file

    def save_contact(self, url: str, contacts: Dict[str, Any]):
        """Save extracted contact to file"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        entry = {
            'url': url,
            'contacts': contacts,
            'timestamp': datetime.utcnow().isoformat()
        }
        data.append(entry)

        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_history(self, limit: int = 10) -> list:
        """Get extraction history"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            return data[-limit:]
        except (FileNotFoundError, json.JSONDecodeError):
            return []
