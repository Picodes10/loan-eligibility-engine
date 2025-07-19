import json
import boto3
import logging
from typing import Dict, Any, Optional
from database_manager import DatabaseManager
from utils import validate_user_data, calculate_match_score, generate_match_reasons

logger = logging.getLogger(__name__)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gateway handler for the loan eligibility engine.
    Handles various HTTP endpoints for the web UI and API.
    """
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }
        
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Parse request
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        # Route requests based on path and method
        if path == '/' or path == '/index.html':
            return serve_web_ui(headers)
        elif path == '/api/users' and http_method == 'GET':
            return get_users(headers, query_parameters)
        elif path == '/api/users' and http_method == 'POST':
            return create_user(headers, event)
        elif path.startswith('/api/users/') and http_method == 'GET':
            user_id = path_parameters.get('user_id')
            return get_user_matches(headers, user_id)
        elif path == '/api/products' and http_method == 'GET':
            return get_loan_products(headers, query_parameters)
        elif path == '/api/matches' and http_method == 'POST':
            return create_matches(headers, event)
        elif path == '/api/status' and http_method == 'GET':
            batch_id = query_parameters.get('batch_id')
            return get_processing_status(headers, batch_id)
        elif path == '/api/health' and http_method == 'GET':
            return health_check(headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        logger.error(f"API Gateway error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def serve_web_ui(headers: Dict[str, str]) -> Dict[str, Any]:
    """Serve the main web UI HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loan Eligibility Engine</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Loan Eligibility Engine</h1>
            <p>Upload user data and discover matching loan products</p>
        </header>
        
        <main>
            <section class="upload-section">
                <h2>Upload User Data</h2>
                <div class="upload-area" id="uploadArea">
                    <input type="file" id="csvFile" accept=".csv" style="display: none;">
                    <div class="upload-content">
                        <div class="upload-icon">📁</div>
                        <p>Drag and drop a CSV file here or click to browse</p>
                        <button class="btn btn-primary" onclick="document.getElementById('csvFile').click()">
                            Choose File
                        </button>
                    </div>
                </div>
                <div id="uploadProgress" class="progress-bar" style="display: none;">
                    <div class="progress-fill"></div>
                </div>
                <div id="uploadStatus"></div>
            </section>
            
            <section class="stats-section">
                <h2>System Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <p id="totalUsers">Loading...</p>
                    </div>
                    <div class="stat-card">
                        <h3>Loan Products</h3>
                        <p id="totalProducts">Loading...</p>
                    </div>
                    <div class="stat-card">
                        <h3>Matches Made</h3>
                        <p id="totalMatches">Loading...</p>
                    </div>
                </div>
            </section>
            
            <section class="recent-matches">
                <h2>Recent Matches</h2>
                <div id="recentMatches" class="matches-list">
                    <p>Loading recent matches...</p>
                </div>
            </section>
        </main>
    </div>
    
    <script src="/static/script.js"></script>
</body>
</html>
    """
    
    return {
        'statusCode': 200,
        'headers': {**headers, 'Content-Type': 'text/html'},
        'body': html_content
    }


def get_users(headers: Dict[str, str], query_params: Dict[str, str]) -> Dict[str, Any]:
    """Get users with optional filtering"""
    try:
        db_manager = DatabaseManager()
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))
        
        # This would need to be implemented in DatabaseManager
        users = db_manager.get_users_paginated(limit, offset)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'users': users,
                'total': len(users),
                'limit': limit,
                'offset': offset
            })
        }
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to get users: {str(e)}'})
        }


def create_user(headers: Dict[str, str], event: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate user data
        validation_errors = validate_user_data(body)
        if validation_errors:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Validation failed', 'details': validation_errors})
            }
        
        db_manager = DatabaseManager()
        user_id = db_manager.insert_user(body)
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'User created successfully',
                'user_id': user_id
            })
        }
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to create user: {str(e)}'})
        }


def get_user_matches(headers: Dict[str, str], user_id: str) -> Dict[str, Any]:
    """Get matches for a specific user"""
    try:
        if not user_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'user_id is required'})
            }
        
        db_manager = DatabaseManager()
        matches = db_manager.get_user_matches(user_id)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'user_id': user_id,
                'matches': matches,
                'total_matches': len(matches)
            })
        }
    except Exception as e:
        logger.error(f"Error getting user matches: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to get matches: {str(e)}'})
        }


def get_loan_products(headers: Dict[str, str], query_params: Dict[str, str]) -> Dict[str, Any]:
    """Get loan products with optional filtering"""
    try:
        db_manager = DatabaseManager()
        products = db_manager.get_loan_products()
        
        # Apply filters if provided
        min_income = query_params.get('min_income')
        min_credit_score = query_params.get('min_credit_score')
        
        if min_income:
            products = [p for p in products if p.get('min_income', 0) <= float(min_income)]
        if min_credit_score:
            products = [p for p in products if p.get('min_credit_score', 0) <= int(min_credit_score)]
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'products': products,
                'total': len(products)
            })
        }
    except Exception as e:
        logger.error(f"Error getting loan products: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to get products: {str(e)}'})
        }


def create_matches(headers: Dict[str, str], event: Dict[str, Any]) -> Dict[str, Any]:
    """Create matches for users"""
    try:
        body = json.loads(event.get('body', '{}'))
        user_ids = body.get('user_ids', [])
        
        if not user_ids:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'user_ids array is required'})
            }
        
        db_manager = DatabaseManager()
        users = db_manager.get_users_by_ids(user_ids)
        products = db_manager.get_loan_products()
        
        matches_created = 0
        for user in users:
            for product in products:
                match_score = calculate_match_score(user, product)
                if match_score > 50:  # Only create matches with score > 50
                    match_reasons = generate_match_reasons(user, product, match_score)
                    db_manager.insert_match({
                        'user_id': user['user_id'],
                        'product_id': product['id'],
                        'match_score': match_score,
                        'match_reasons': match_reasons
                    })
                    matches_created += 1
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'message': 'Matches created successfully',
                'matches_created': matches_created
            })
        }
    except Exception as e:
        logger.error(f"Error creating matches: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to create matches: {str(e)}'})
        }


def get_processing_status(headers: Dict[str, str], batch_id: str) -> Dict[str, Any]:
    """Get processing status for a batch"""
    try:
        if not batch_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'batch_id is required'})
            }
        
        db_manager = DatabaseManager()
        status_logs = db_manager.get_processing_status(batch_id)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'batch_id': batch_id,
                'status_logs': status_logs
            })
        }
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Failed to get status: {str(e)}'})
        }


def health_check(headers: Dict[str, str]) -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        db_manager = DatabaseManager()
        # Test database connection
        db_manager.test_connection()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': '2024-01-01T00:00:00Z',
                'version': '1.0.0'
            })
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'statusCode': 503,
            'headers': headers,
            'body': json.dumps({
                'status': 'unhealthy',
                'error': str(e)
            })
        } 