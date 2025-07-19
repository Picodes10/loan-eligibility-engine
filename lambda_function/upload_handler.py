import json
import boto3
import base64
import uuid
from datetime import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for CSV upload using S3 event-driven pattern.
    This avoids API Gateway size limits by using S3 for large file uploads.
    """
    try:
        # CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
        
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Parse request body
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body']).decode('utf-8')
        else:
            body = event['body']
            
        request_data = json.loads(body)
        
        # Extract file data
        file_content = request_data.get('file_content')
        filename = request_data.get('filename', 'users.csv')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Generate unique batch ID
        batch_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"uploads/{timestamp}_{batch_id}_{filename}"
        
        # Upload to S3
        s3_client = boto3.client('s3')
        bucket_name = os.getenv('S3_BUCKET', context.function_name.split('-')[0] + '-' + context.function_name.split('-')[1] + '-uploads')
        
        # If file_content is base64 encoded, decode it
        if isinstance(file_content, str) and file_content.startswith('data:'):
            # Extract base64 data
            file_content = file_content.split(',')[1]
            file_bytes = base64.b64decode(file_content)
        else:
            file_bytes = file_content.encode('utf-8')
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_bytes,
            Metadata={
                'batch_id': batch_id,
                'original_filename': filename,
                'upload_timestamp': timestamp
            }
        )
        
        logger.info(f"File uploaded successfully to S3: {s3_key}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'File uploaded successfully',
                'batch_id': batch_id,
                's3_key': s3_key,
                'status': 'processing'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in CSV upload handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


def generate_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for S3 object upload"""
    s3_client = boto3.client('s3')
    
    try:
        response = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return response
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise


def get_upload_url_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Alternative handler that provides presigned URLs for direct S3 upload.
    This is more efficient for large files.
    """
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        }
        
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Parse request
        body = json.loads(event['body'])
        filename = body.get('filename', 'users.csv')
        
        # Generate unique identifiers
        batch_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"uploads/{timestamp}_{batch_id}_{filename}"
        
        # Get bucket name from environment
        bucket_name = os.getenv('S3_BUCKET', context.function_name.split('-')[0] + '-' + context.function_name.split('-')[1] + '-uploads')
        
        # Generate presigned URL
        upload_url = generate_presigned_url(bucket_name, s3_key)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'upload_url': upload_url,
                'batch_id': batch_id,
                's3_key': s3_key,
                'bucket': bucket_name
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating upload URL: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
        