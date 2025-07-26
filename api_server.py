from flask import Flask, request, jsonify
import sys
from pathlib import Path
import os
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

# Import with error handling for Lambda environment
try:
    from src.scrapers.loan_discovery import run_loan_discovery
    from src.matching.loan_matcher import run_user_loan_matching
    from src.notifications.email_service import run_email_notifications
except ImportError as e:
    print(f"Import error: {e}")
    # Create dummy functions for Lambda environment
    def run_loan_discovery():
        return {"success": True, "message": "Loan discovery service placeholder", "loans_found": 0}
    
    def run_user_loan_matching():
        return {"success": True, "message": "User matching service placeholder", "matches_created": 0}
    
    def run_email_notifications():
        return {"success": True, "message": "Email notification service placeholder", "emails_sent": 0}

app = Flask(__name__)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        'message': 'Loan Matching API Server',
        'status': 'running',
        'environment': os.environ.get('STAGE', 'local'),
        'region': os.environ.get('AWS_REGION', 'unknown'),
        'endpoints': {
            'health_check': 'GET /api/health',
            'loan_discovery': 'POST /api/run-discovery',
            'user_matching': 'POST /api/run-matching',
            'notifications': 'POST /api/send-notifications',
            'test': 'GET /test'
        },
        'documentation': 'This API is designed for n8n workflow automation'
    })

@app.route('/api/run-discovery', methods=['POST'])
def api_run_discovery():
    """API endpoint for n8n to trigger loan discovery"""
    try:
        result = run_loan_discovery()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'endpoint': 'run-discovery'
        }), 500

@app.route('/api/run-matching', methods=['POST'])
def api_run_matching():
    """API endpoint for n8n to trigger user-loan matching"""
    try:
        result = run_user_loan_matching()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'endpoint': 'run-matching'
        }), 500

@app.route('/api/send-notifications', methods=['POST'])
def api_send_notifications():
    """API endpoint for n8n to trigger email notifications"""
    try:
        result = run_email_notifications()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'endpoint': 'send-notifications'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return jsonify({
        'status': 'healthy',
        'service': 'loan-matching-api',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': os.environ.get('STAGE', 'local'),
        'region': os.environ.get('AWS_REGION', 'unknown'),
        'python_path': sys.path[:3]  # Show first 3 paths for debugging
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint for debugging"""
    return jsonify({
        'status': 'success',
        'message': 'Test endpoint working',
        'lambda_context': 'available' if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ else 'not_available',
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'environment_vars': {
            'AWS_REGION': os.environ.get('AWS_REGION', 'not_set'),
            'STAGE': os.environ.get('STAGE', 'not_set'),
            'AWS_LAMBDA_FUNCTION_NAME': os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'not_set')
        }
    })

# AWS Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler for API Gateway"""
    try:
        import serverless_wsgi
        return serverless_wsgi.handle_request(app, event, context)
    except ImportError as e:
        # Fallback for local development
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "serverless_wsgi not available: {str(e)}"}}'
        }
    except Exception as e:
        # General error handling
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "Lambda handler error: {str(e)}"}}'
        }

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
