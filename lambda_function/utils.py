import re
import requests
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_user_data(user_data: Dict[str, Any]) -> List[str]:
    """
    Validate user data and return list of validation errors.
    """
    errors = []
    
    # Validate user_id
    if not user_data.get('user_id'):
        errors.append("user_id is required")
    elif len(str(user_data['user_id'])) > 100:
        errors.append("user_id must be less than 100 characters")
    
    # Validate email
    email = user_data.get('email')
    if not email:
        errors.append("email is required")
    elif not is_valid_email(email):
        errors.append("invalid email format")
    
    # Validate monthly_income
    income = user_data.get('monthly_income')
    if income is not None:
        if not isinstance(income, (int, float)) or income < 0:
            errors.append("monthly_income must be a positive number")
        elif income > 10000000:  # 10 million limit
            errors.append("monthly_income seems unrealistic (>10M)")
    
    # Validate credit_score
    credit_score = user_data.get('credit_score')
    if credit_score is not None:
        if not isinstance(credit_score, int) or credit_score < 300 or credit_score > 850:
            errors.append("credit_score must be between 300 and 850")
    
    # Validate employment_status
    employment_status = user_data.get('employment_status')
    if employment_status is not None:
        valid_statuses = ['employed', 'unemployed', 'self-employed', 'student', 'retired']
        if employment_status not in valid_statuses:
            errors.append(f"employment_status must be one of: {valid_statuses}")
    
    # Validate age
    age = user_data.get('age')
    if age is not None:
        if not isinstance(age, int) or age < 18 or age > 100:
            errors.append("age must be between 18 and 100")
    
    return errors


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def trigger_n8n_webhook(webhook_url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Trigger n8n webhook with payload.
    """
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully triggered n8n webhook: {webhook_url}")
            return response.json() if response.content else {'status': 'success'}
        else:
            logger.error(f"n8n webhook failed with status {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering n8n webhook: {str(e)}")
        return None


def calculate_match_score(user: Dict[str, Any], product: Dict[str, Any]) -> float:
    """
    Calculate match score between user and loan product.
    Returns a score between 0 and 100.
    """
    score = 0.0
    max_score = 100.0
    
    # Credit score matching (30% weight)
    if user.get('credit_score') and product.get('min_credit_score'):
        if user['credit_score'] >= product['min_credit_score']:
            # Bonus points for higher credit score
            credit_bonus = min(20, (user['credit_score'] - product['min_credit_score']) / 10)
            score += 30 + credit_bonus
        else:
            score += 0  # No points if below minimum
    else:
        score += 15  # Partial points if criteria not specified
    
    # Income matching (25% weight)
    if user.get('monthly_income') and product.get('min_income'):
        if user['monthly_income'] >= product['min_income']:
            # Bonus points for higher income
            income_ratio = user['monthly_income'] / product['min_income']
            income_bonus = min(10, income_ratio * 5)
            score += 25 + income_bonus
        else:
            score += 0  # No points if below minimum
    else:
        score += 12  # Partial points if criteria not specified
    
    # Age matching (15% weight)
    if user.get('age'):
        min_age = product.get('min_age', 18)
        max_age = product.get('max_age', 65)
        if min_age <= user['age'] <= max_age:
            score += 15
        else:
            score += 0
    else:
        score += 7  # Partial points if age not specified
    
    # Employment status matching (15% weight)
    if user.get('employment_status'):
        if product.get('employment_required', False):
            if user['employment_status'] in ['employed', 'self-employed']:
                score += 15
            else:
                score += 0
        else:
            score += 15  # Full points if employment not required
    else:
        score += 7  # Partial points if employment status not specified
    
    # Interest rate bonus (15% weight)
    if product.get('interest_rate'):
        # Lower interest rate = higher score
        rate_score = max(0, 15 - (product['interest_rate'] - 5))
        score += min(15, rate_score)
    else:
        score += 7
    
    return min(max_score, score)


def generate_match_reasons(user: Dict[str, Any], product: Dict[str, Any], score: float) -> List[str]:
    """
    Generate human-readable reasons for the match.
    """
    reasons = []
    
    # Credit score reasons
    if user.get('credit_score') and product.get('min_credit_score'):
        if user['credit_score'] >= product['min_credit_score']:
            reasons.append(f"Your credit score ({user['credit_score']}) meets the minimum requirement ({product['min_credit_score']})")
        else:
            reasons.append(f"Your credit score ({user['credit_score']}) is below the minimum requirement ({product['min_credit_score']})")
    
    # Income reasons
    if user.get('monthly_income') and product.get('min_income'):
        if user['monthly_income'] >= product['min_income']:
            reasons.append(f"Your monthly income (${user['monthly_income']:,.2f}) meets the minimum requirement (${product['min_income']:,.2f})")
        else:
            reasons.append(f"Your monthly income (${user['monthly_income']:,.2f}) is below the minimum requirement (${product['min_income']:,.2f})")
    
    # Employment reasons
    if user.get('employment_status') and product.get('employment_required', False):
        if user['employment_status'] in ['employed', 'self-employed']:
            reasons.append(f"Your employment status ({user['employment_status']}) meets the requirement")
        else:
            reasons.append(f"Employment is required but your status is {user['employment_status']}")
    
    # Age reasons
    if user.get('age'):
        min_age = product.get('min_age', 18)
        max_age = product.get('max_age', 65)
        if min_age <= user['age'] <= max_age:
            reasons.append(f"Your age ({user['age']}) is within the acceptable range ({min_age}-{max_age})")
        else:
            reasons.append(f"Your age ({user['age']}) is outside the acceptable range ({min_age}-{max_age})")
    
    # Interest rate
    if product.get('interest_rate'):
        reasons.append(f"Competitive interest rate: {product['interest_rate']:.2f}% APR")
    
    return reasons


def format_currency(amount: float) -> str:
    """Format currency amount for display."""
    return f"${amount:,.2f}"


def format_percentage(rate: float) -> str:
    """Format percentage for display."""
    return f"{rate:.2f}%"


def sanitize_html(text: str) -> str:
    """
    Basic HTML sanitization for user-generated content.
    """
    import html
    return html.escape(str(text))


def get_environment_config() -> Dict[str, Any]:
    """
    Get environment configuration for the application.
    """
    import os
    
    return {
        'postgres_host': os.getenv('POSTGRES_HOST'),
        'postgres_db': os.getenv('POSTGRES_DB', 'loan_engine'),
        'postgres_user': os.getenv('POSTGRES_USER', 'admin'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD'),
        'n8n_webhook_url': os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
        'environment': os.getenv('ENVIRONMENT', 'development')
    }


def log_performance_metrics(operation: str, duration: float, records_processed: int = 0):
    """
    Log performance metrics for monitoring.
    """
    logger.info(f"Performance Metrics - Operation: {operation}, Duration: {duration:.2f}s, Records: {records_processed}")


def retry_with_backoff(func, max_retries: int = 3, backoff_factor: float = 2.0):
    """
    Retry function with exponential backoff.
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
            time.sleep(wait_time)


def validate_loan_product_data(product_data: Dict[str, Any]) -> List[str]:
    """
    Validate loan product data and return list of validation errors.
    """
    errors = []
    
    # Required fields
    required_fields = ['product_name', 'provider']
    for field in required_fields:
        if not product_data.get(field):
            errors.append(f"{field} is required")
    
    # Validate interest rate
    interest_rate = product_data.get('interest_rate')
    if interest_rate is not None:
        if not isinstance(interest_rate, (int, float)) or interest_rate < 0 or interest_rate > 50:
            errors.append("interest_rate must be between 0 and 50")
    
    # Validate income requirements
    min_income = product_data.get('min_income')
    if min_income is not None:
        if not isinstance(min_income, (int, float)) or min_income < 0:
            errors.append("min_income must be a positive number")
    
    # Validate credit score requirements
    min_credit = product_data.get('min_credit_score')
    max_credit = product_data.get('max_credit_score')
    
    if min_credit is not None:
        if not isinstance(min_credit, int) or min_credit < 300 or min_credit > 850:
            errors.append("min_credit_score must be between 300 and 850")
    
    if max_credit is not None:
        if not isinstance(max_credit, int) or max_credit < 300 or max_credit > 850:
            errors.append("max_credit_score must be between 300 and 850")
    
    if min_credit and max_credit and min_credit > max_credit:
        errors.append("min_credit_score cannot be greater than max_credit_score")
    
    # Validate age requirements
    min_age = product_data.get('min_age')
    max_age = product_data.get('max_age')
    
    if min_age is not None:
        if not isinstance(min_age, int) or min_age < 18 or min_age > 100:
            errors.append("min_age must be between 18 and 100")
    
    if max_age is not None:
        if not isinstance(max_age, int) or max_age < 18 or max_age > 100:
            errors.append("max_age must be between 18 and 100")
    
    if min_age and max_age and min_age > max_age:
        errors.append("min_age cannot be greater than max_age")
    
    return errors


def create_batch_id() -> str:
    """Create a unique batch ID."""
    import uuid
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()
