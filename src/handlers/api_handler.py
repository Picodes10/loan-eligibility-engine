import json
import boto3
import os
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app = Flask(__name__)

# HTML template for the upload interface
UPLOAD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loan Matching System - CSV Upload</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            width: 90%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .header h1 {
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            color: #666;
            font-size: 0.9rem;
        }
        
        .upload-area {
            border: 2px dashed #ddd;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background-color: #f8f9ff;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background-color: #f0f2ff;
        }
        
        .upload-icon {
            font-size: 3rem;
            color: #ddd;
            margin-bottom: 1rem;
        }
        
        .upload-text {
            color: #666;
            margin-bottom: 1rem;
        }
        
        .file-input {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress {
            margin-top: 1rem;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .status {
            margin-top: 1rem;
            padding: 1rem;
            border-radius: 5px;
            display: none;
        }
        
        .status.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .file-info {
            margin-top: 1rem;
            padding: 1rem;
            background-color: #f8f9fa;
            border-radius: 5px;
            display: none;
        }
        
        .requirements {
            margin-top: 2rem;
            padding: 1rem;
            background-color: #f8f9ff;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        
        .requirements h3 {
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }
        
        .requirements ul {
            color: #666;
            font-size: 0.9rem;
            margin-left: 1rem;
        }
        
        .requirements li {
            margin-bottom: 0.25rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 Loan Matching System</h1>
            <p>Upload your user data CSV to start the automated matching process</p>
        </div>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📁</div>
            <div class="upload-text">
                <strong>Click to select</strong> or drag and drop your CSV file here
            </div>
            <input type="file" id="fileInput" class="file-input" accept=".csv" />
        </div>
        
        <div class="file-info" id="fileInfo"></div>
        
        <button class="btn" id="uploadBtn" disabled>Upload and Process</button>
        
        <div class="progress" id="progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
        </div>
        
        <div class="status" id="status"></div>
        
        <div class="requirements">
            <h3>📋 CSV Requirements</h3>
            <ul>
                <li><strong>user_id:</strong> Unique identifier for each user</li>
                <li><strong>email:</strong> Valid email address</li>
                <li><strong>monthly_income:</strong> Monthly income in dollars</li>
                <li><strong>credit_score:</strong> Credit score (300-850)</li>
                <li><strong>employment_status:</strong> Employment status</li>
                <li><strong>age:</strong> Age in years (18-100)</li>
            </ul>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const fileInfo = document.getElementById('fileInfo');
        const progress = document.getElementById('progress');
        const progressFill = document.getElementById('progressFill');
        const status = document.getElementById('status');
        
        let selectedFile = null;
        
        // Click to select file
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Drag and drop functionality
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        function handleFileSelect(file) {
            if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
                showStatus('Please select a CSV file.', 'error');
                return;
            }
            
            selectedFile = file;
            
            fileInfo.innerHTML = `
                <strong>Selected File:</strong> ${file.name}<br>
                <strong>Size:</strong> ${(file.size / 1024).toFixed(2)} KB<br>
                <strong>Type:</strong> ${file.type || 'text/csv'}
            `;
            fileInfo.style.display = 'block';
            
            uploadBtn.disabled = false;
            hideStatus();
        }
        
        // Upload functionality
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            uploadBtn.disabled = true;
            progress.style.display = 'block';
            
            try {
                // Get presigned URL for upload
                const response = await fetch('/api/upload-url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        filename: selectedFile.name,
                        contentType: selectedFile.type || 'text/csv'
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to get upload URL');
                }
                
                // Upload file to S3
                const uploadResponse = await fetch(data.uploadUrl, {
                    method: 'PUT',
                    body: selectedFile,
                    headers: {
                        'Content-Type': selectedFile.type || 'text/csv'
                    }
                });
                
                if (!uploadResponse.ok) {
                    throw new Error('Failed to upload file');
                }
                
                progressFill.style.width = '100%';
                
                showStatus('✅ File uploaded successfully! Processing will begin automatically. Users will receive email notifications once matching is complete.', 'success');
                
                // Reset form
                setTimeout(() => {
                    selectedFile = null;
                    fileInput.value = '';
                    fileInfo.style.display = 'none';
                    progress.style.display = 'none';
                    progressFill.style.width = '0%';
                    uploadBtn.disabled = true;
                }, 3000);
                
            } catch (error) {
                console.error('Upload error:', error);
                showStatus(`❌ Upload failed: ${error.message}`, 'error');
                uploadBtn.disabled = false;
                progress.style.display = 'none';
                progressFill.style.width = '0%';
            }
        });
        
        function showStatus(message, type) {
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }
        
        function hideStatus() {
            status.style.display = 'none';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main upload interface"""
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/api/upload-url', methods=['POST'])
def get_upload_url():
    """Generate a presigned URL for S3 upload"""
    try:
        data = request.get_json()
        filename = secure_filename(data.get('filename', ''))
        content_type = data.get('contentType', 'text/csv')
        
        if not filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Generate unique filename
        unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"
        
        # Get S3 bucket name
        bucket_name = f"loan-matching-system-{os.getenv('STAGE', 'dev')}-uploads"
        
        # Generate presigned URL
        s3_client = boto3.client('s3')
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': unique_filename,
                'ContentType': content_type
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return jsonify({
            'uploadUrl': presigned_url,
            'filename': unique_filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get system status and recent processing logs"""
    try:
        from src.models.database import get_database_session, ProcessingLog
        
        session = get_database_session()
        
        # Get recent logs
        recent_logs = session.query(ProcessingLog)\
            .order_by(ProcessingLog.created_at.desc())\
            .limit(10)\
            .all()
        
        logs_data = []
        for log in recent_logs:
            logs_data.append({
                'id': log.id,
                'process_type': log.process_type,
                'status': log.status,
                'details': log.details,
                'records_processed': log.records_processed,
                'created_at': log.created_at.isoformat(),
                'completed_at': log.completed_at.isoformat() if log.completed_at else None
            })
        
        session.close()
        
        return jsonify({
            'status': 'healthy',
            'recent_logs': logs_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def handler(event, context):
    """Lambda handler for API Gateway events"""
    try:
        # Handle different HTTP methods and paths
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        
        # Set up Flask app context
        with app.test_request_context(path, method=http_method):
            if http_method == 'GET' and path == '/':
                response_body = index()
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'text/html',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': response_body
                }
            
            elif http_method == 'POST' and path == '/api/upload-url':
                # Parse request body
                body = json.loads(event.get('body', '{}'))
                
                with app.test_request_context(path, method=http_method, json=body):
                    response = get_upload_url()
                    return {
                        'statusCode': response.status_code,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': response.get_data(as_text=True)
                    }
            
            elif http_method == 'GET' and path == '/api/status':
                response = get_status()
                return {
                    'statusCode': response.status_code,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': response.get_data(as_text=True)
                }
            
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'Not found'})
                }
                
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

if __name__ == '__main__':
    app.run(debug=True)
