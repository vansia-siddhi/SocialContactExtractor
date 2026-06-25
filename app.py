from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from backend.extractor import ContactExtractor
import logging
import os
from datetime import datetime, timezone
import traceback

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

app = Flask(__name__)
CORS(app)

extractor = ContactExtractor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
def extract_contacts():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid request: No JSON data received'
            }), 400

        url = data.get('url', '').strip()

        if not url:
            return jsonify({
                'success': False,
                'error': 'Please provide a valid URL'
            }), 400

        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        logger.info(f"Extracting contacts from: {url}")

        contacts = extractor.extract(url)
        platform = extractor.detect_platform(url)

        # Ensure all values are strings
        for key in ['phone', 'email', 'office']:
            if key not in contacts or contacts[key] is None:
                contacts[key] = 'Not found'

        return jsonify({
            'success': True,
            'data': contacts,
            'platform': platform,
            'url': url,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error extracting contacts: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
