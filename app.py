#!/usr/bin/env python3
"""
Local development server for Loan Eligibility Engine
This provides a local Flask server for development and testing
"""

import os
import sys
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the lambda_function directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lambda_function'))

from database_manager import DatabaseManager
from utils import validate_user_data, calculate_match_score, generate_match_reasons

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize database manager
db_manager = DatabaseManager()

@app.route('/')
def index():
    """Serve the main web UI"""
    try:
        with open('web_ui/index.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Loan Eligibility Engine</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { padding: 20px; background: #f0f8ff; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Loan Eligibility Engine</h1>
                <div class="status">
                    <h2>✅ Server is running!</h2>
                    <p>The application is now ready to use.</p>
                    <p><strong>API Endpoints:</strong></p>
                    <ul>
                        <li>GET /api/health - Health check</li>
                        <li>GET /api/users - List users</li>
                        <li>GET /api/products - List loan products</li>
                        <li>POST /api/users - Create user</li>
                        <li>POST /upload-csv - Upload CSV file</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    try:
        static_path = os.path.join('web_ui/static', filename)
        with open(static_path, 'r') as f:
            content = f.read()
        
        if filename.endswith('.css'):
            return content, 200, {'Content-Type': 'text/css'}
        elif filename.endswith('.js'):
            return content, 200, {'Content-Type': 'application/javascript'}
        else:
            return content
    except FileNotFoundError:
        return "File not found", 404

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        if db_manager.test_connection():
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': '2024-01-01T00:00:00Z',
                'version': '1.0.0'
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': 'Database connection failed'
            }), 503
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get users with pagination"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        users = db_manager.get_users_paginated(limit, offset)
        
        return jsonify({
            'users': users,
            'total': len(users),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': f'Failed to get users: {str(e)}'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate user data
        validation_errors = validate_user_data(data)
        if validation_errors:
            return jsonify({
                'error': 'Validation failed',
                'details': validation_errors
            }), 400
        
        user_id = db_manager.insert_user(data)
        
        return jsonify({
            'message': 'User created successfully',
            'user_id': user_id
        }), 201
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get loan products"""
    try:
        products = db_manager.get_loan_products()
        
        # Apply filters if provided
        min_income = request.args.get('min_income')
        min_credit_score = request.args.get('min_credit_score')
        
        if min_income:
            products = [p for p in products if p.get('min_income', 0) <= float(min_income)]
        if min_credit_score:
            products = [p for p in products if p.get('min_credit_score', 0) <= int(min_credit_score)]
        
        return jsonify({
            'products': products,
            'total': len(products)
        })
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        return jsonify({'error': f'Failed to get products: {str(e)}'}), 500

@app.route('/api/matches', methods=['GET'])
def get_matches():
    """Get recent matches"""
    try:
        limit = int(request.args.get('limit', 10))
        matches = db_manager.get_recent_matches(limit)
        
        return jsonify({
            'matches': matches,
            'total': len(matches)
        })
    except Exception as e:
        logger.error(f"Error getting matches: {str(e)}")
        return jsonify({'error': f'Failed to get matches: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        stats = db_manager.get_system_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    """Handle CSV file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Read and process CSV content
        import pandas as pd
        from io import StringIO
        import uuid
        
        content = file.read().decode('utf-8')
        df = pd.read_csv(StringIO(content))
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        
        # Log processing start
        db_manager.log_processing_operation(
            batch_id=batch_id,
            operation='csv_processing',
            status='started'
        )
        
        # Process CSV data
        processed_users = []
        errors = []
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Required columns
        required_columns = ['user_id', 'email', 'monthly_income', 'credit_score', 'employment_status', 'age']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'error': f'Missing required columns: {missing_columns}'
            }), 400
        
        for index, row in df.iterrows():
            try:
                user_data = {
                    'user_id': str(row['user_id']).strip(),
                    'email': str(row['email']).strip().lower(),
                    'monthly_income': float(row['monthly_income']) if pd.notna(row['monthly_income']) else None,
                    'credit_score': int(row['credit_score']) if pd.notna(row['credit_score']) else None,
                    'employment_status': str(row['employment_status']).strip().lower() if pd.notna(row['employment_status']) else None,
                    'age': int(row['age']) if pd.notna(row['age']) else None
                }
                
                # Validate data
                validation_errors = validate_user_data(user_data)
                if validation_errors:
                    errors.append(f"Row {index + 1}: {validation_errors}")
                    continue
                
                processed_users.append(user_data)
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
                continue
        
        if not processed_users:
            return jsonify({
                'error': 'No valid user data found in CSV',
                'details': errors
            }), 400
        
        # Insert users into database
        records_inserted = db_manager.insert_users_batch(processed_users)
        
        # Log processing success
        db_manager.log_processing_operation(
            batch_id=batch_id,
            operation='csv_processing',
            status='completed',
            records_processed=records_inserted
        )
        
        return jsonify({
            'message': 'CSV processed successfully',
            'batch_id': batch_id,
            'records_processed': records_inserted,
            'errors': errors if errors else None
        })
        
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        return jsonify({'error': f'Failed to process CSV: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting Loan Eligibility Engine Development Server...")
    print("=" * 60)
    
    # Test database connection
    try:
        if db_manager.test_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            print("Please ensure PostgreSQL is running and configured correctly")
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("Please check your database configuration in .env file")
    
    print(f"🌐 Server starting on http://localhost:3000")
    print("📊 Access the dashboard at http://localhost:3000")
    print("🔧 n8n dashboard available at http://localhost:5678")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3000, debug=True)