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

        # Add protocol if missing
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        logger.info(f"Extracting contacts from: {url}")

        # Extract contact details with timeout protection
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Extraction timed out after 60 seconds")

        # Set timeout (only works on Unix)
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)
        except:
            pass  # Windows doesn't support SIGALRM

        try:
            contacts = extractor.extract(url)
            platform = extractor.detect_platform(url)
        except TimeoutError as e:
            logger.error(f"Extraction timed out: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Extraction timed out. Please try again.'
            }), 504
        finally:
            try:
                signal.alarm(0)
            except:
                pass

        # Ensure all values are strings
        for key in ['phone', 'email', 'office']:
            if key not in contacts or contacts[key] is None:
                contacts[key] = 'Not found'
            elif not isinstance(contacts[key], str):
                contacts[key] = str(contacts[key])

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
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))

    # Run the app
    app.run(debug=False, host='0.0.0.0', port=port)
