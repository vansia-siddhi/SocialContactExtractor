from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from backend.extractor import ContactExtractor
import logging
import os
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Initialize extractor
extractor = ContactExtractor()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_contacts():
    """
    API endpoint to extract contact details from social media URL
    """
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid URL'
            }), 400

        # Add protocol if missing
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        logger.info(f"Extracting contacts from: {url}")

        # Extract contact details
        contacts = extractor.extract(url)
        platform = extractor.detect_platform(url)

        return jsonify({
            'success': True,
            'data': contacts,
            'platform': platform,
            'url': url,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error extracting contacts: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))

    # Run the app
    app.run(debug=False, host='0.0.0.0', port=port)
