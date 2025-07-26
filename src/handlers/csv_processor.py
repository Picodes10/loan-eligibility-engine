import json
import boto3
import pandas as pd
import requests
from io import StringIO
from src.models.database import get_database_session, User, ProcessingLog
from datetime import datetime
import os

def handler(event, context):
    """
    Lambda handler for processing CSV files uploaded to S3
    Triggered by S3 ObjectCreated events
    """
    try:
        # Extract S3 bucket and key from the event
        s3_event = event['Records'][0]['s3']
        bucket_name = s3_event['bucket']['name']
        object_key = s3_event['object']['key']
        
        # Log the start of processing
        session = get_database_session()
        log_entry = ProcessingLog(
            process_type='csv_upload',
            status='started',
            details=f'Processing file: {object_key}'
        )
        session.add(log_entry)
        session.commit()
        
        # Download the CSV file from S3
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Parse CSV data
        df = pd.read_csv(StringIO(csv_content))
        
        # Validate required columns
        required_columns = ['user_id', 'email', 'monthly_income', 'credit_score', 'employment_status', 'age']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Process and insert users
        users_processed = 0
        users_added = 0
        
        for _, row in df.iterrows():
            try:
                # Check if user already exists
                existing_user = session.query(User).filter_by(user_id=str(row['user_id'])).first()
                
                if not existing_user:
                    # Create new user
                    user = User(
                        user_id=str(row['user_id']),
                        email=str(row['email']),
                        monthly_income=float(row['monthly_income']),
                        credit_score=int(row['credit_score']),
                        employment_status=str(row['employment_status']),
                        age=int(row['age']),
                        processed=False
                    )
                    session.add(user)
                    users_added += 1
                else:
                    # Update existing user
                    existing_user.email = str(row['email'])
                    existing_user.monthly_income = float(row['monthly_income'])
                    existing_user.credit_score = int(row['credit_score'])
                    existing_user.employment_status = str(row['employment_status'])
                    existing_user.age = int(row['age'])
                    existing_user.processed = False
                
                users_processed += 1
                
            except Exception as e:
                print(f"Error processing user {row.get('user_id', 'unknown')}: {str(e)}")
                continue
        
        session.commit()
        
        # Update processing log
        log_entry.status = 'completed'
        log_entry.records_processed = users_processed
        log_entry.completed_at = datetime.utcnow()
        log_entry.details = f'Successfully processed {users_processed} users, added {users_added} new users'
        session.commit()
        
        # Trigger n8n workflow for user-loan matching
        webhook_url = os.getenv('N8N_WEBHOOK_URL')
        if webhook_url:
            try:
                payload = {
                    'event_type': 'csv_processed',
                    'users_processed': users_processed,
                    'users_added': users_added,
                    'file_name': object_key,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = requests.post(webhook_url, json=payload, timeout=30)
                print(f"n8n webhook triggered: {response.status_code}")
                
            except Exception as e:
                print(f"Failed to trigger n8n webhook: {str(e)}")
        
        session.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CSV processed successfully',
                'users_processed': users_processed,
                'users_added': users_added
            })
        }
        
    except Exception as e:
        # Log the error
        try:
            session = get_database_session()
            log_entry = ProcessingLog(
                process_type='csv_upload',
                status='failed',
                details=f'Error: {str(e)}'
            )
            session.add(log_entry)
            session.commit()
            session.close()
        except:
            pass
        
        print(f"Error processing CSV: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process CSV file',
                'details': str(e)
            })
        }

def validate_user_data(row):
    """Validate individual user data row"""
    errors = []
    
    # Validate email format
    if '@' not in str(row.get('email', '')):
        errors.append('Invalid email format')
    
    # Validate numeric fields
    try:
        monthly_income = float(row['monthly_income'])
        if monthly_income < 0:
            errors.append('Monthly income must be positive')
    except (ValueError, TypeError):
        errors.append('Invalid monthly income')
    
    try:
        credit_score = int(row['credit_score'])
        if not (300 <= credit_score <= 850):
            errors.append('Credit score must be between 300 and 850')
    except (ValueError, TypeError):
        errors.append('Invalid credit score')
    
    try:
        age = int(row['age'])
        if not (18 <= age <= 100):
            errors.append('Age must be between 18 and 100')
    except (ValueError, TypeError):
        errors.append('Invalid age')
    
    return errors
