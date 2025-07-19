import json
import boto3
import pandas as pd
import logging
from io import StringIO
from typing import Dict, Any, List
import requests
from database_manager import DatabaseManager
from utils import validate_user_data, trigger_n8n_webhook

logger = logging.getLogger(__name__)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler triggered by S3 object creation.
    Processes CSV files and stores user data in PostgreSQL.
    """
    try:
        # Extract S3 event information
        s3_event = event['Records'][0]['s3']
        bucket_name = s3_event['bucket']['name']
        object_key = s3_event['object']['key']
        
        logger.info(f"Processing file: {object_key} from bucket: {bucket_name}")
        
        # Extract batch_id from object key
        batch_id = object_key.split('_')[1] if '_' in object_key else 'unknown'
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Log processing start
        db_manager.log_processing_operation(
            batch_id=batch_id,
            operation='csv_processing',
            status='started'
        )
        
        # Download file from S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read().decode('utf-8')
        
        # Parse CSV data
        df = pd.read_csv(StringIO(file_content))
        
        # Clean and validate data
        processed_users = process_csv_data(df, batch_id)
        
        if not processed_users:
            raise Exception("No valid user data found in CSV")
        
        # Store users in database
        records_inserted = db_manager.insert_users_batch(processed_users)
        
        # Log processing success
        db_manager.log_processing_operation(
            batch_id=batch_id,
            operation='csv_processing',
            status='completed',
            records_processed=records_inserted
        )
        
        # Trigger n8n workflow for user-loan matching
        webhook_response = trigger_n8n_webhook(
            webhook_url=get_n8n_webhook_url(),
            payload={
                'batch_id': batch_id,
                'records_processed': records_inserted,
                'trigger_type': 'csv_processed'
            }
        )
        
        logger.info(f"Successfully processed {records_inserted} users. Webhook response: {webhook_response}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CSV processed successfully',
                'batch_id': batch_id,
                'records_processed': records_inserted
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        
        # Log processing failure
        if 'batch_id' in locals():
            db_manager.log_processing_operation(
                batch_id=batch_id,
                operation='csv_processing',
                status='failed',
                errors={'error': str(e)}
            )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Processing failed: {str(e)}'})
        }


def process_csv_data(df: pd.DataFrame, batch_id: str) -> List[Dict[str, Any]]:
    """
    Process and validate CSV data, returning clean user records.
    """
    processed_users = []
    errors = []
    
    # Clean column names
    df.columns = df.columns.str.strip().str.lower()
    
    # Expected columns (required)
    required_columns = ['user_id', 'email', 'monthly_income', 'credit_score', 'employment_status', 'age']
    
    # Optional columns
    optional_columns = ['name']
    
    # Check for required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise Exception(f"Missing required columns: {missing_columns}")
    
    # Log which optional columns are present
    present_optional = [col for col in optional_columns if col in df.columns]
    if present_optional:
        logger.info(f"Found optional columns: {present_optional}")
    
    for index, row in df.iterrows():
        try:
            # Extract and clean data
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
    
    # Log errors if any
    if errors:
        logger.warning(f"Processing errors for batch {batch_id}: {errors}")
    
    logger.info(f"Successfully processed {len(processed_users)} out of {len(df)} rows")
    
    return processed_users


def get_n8n_webhook_url() -> str:
    """Get n8n webhook URL from environment variables"""
    import os
    base_url = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678')
    return f"{base_url}/webhook/user-matching"


def cleanup_old_files(bucket_name: str, days_old: int = 7):
    """Clean up old CSV files from S3 to manage storage costs"""
    try:
        s3_client = boto3.client('s3')
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='uploads/')
        
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    logger.info(f"Deleted old file: {obj['Key']}")
                    
    except Exception as e:
        logger.error(f"Error cleaning up old files: {str(e)}")


def batch_process_large_csv(file_content: str, batch_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Process large CSV files in batches to avoid memory issues.
    """
    all_processed_users = []
    
    # Read CSV in chunks
    csv_reader = pd.read_csv(StringIO(file_content), chunksize=batch_size)
    
    for chunk_index, chunk in enumerate(csv_reader):
        logger.info(f"Processing chunk {chunk_index + 1}")
        
        chunk_batch_id = f"chunk_{chunk_index + 1}"
        processed_chunk = process_csv_data(chunk, chunk_batch_id)
        all_processed_users.extend(processed_chunk)
        
        # Optional: Insert each chunk separately for better error handling
        # db_manager = DatabaseManager()
        # db_manager.insert_users_batch(processed_chunk)
    
    return all_processed_users


def get_processing_status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler to check processing status of a batch.
    """
    try:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        }
        
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # Extract batch_id from query parameters
        batch_id = event.get('queryStringParameters', {}).get('batch_id')
        
        if not batch_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'batch_id is required'})
            }
        
        # Get processing status
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
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
        