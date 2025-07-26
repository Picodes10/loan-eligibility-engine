import boto3
import json
from typing import List, Dict
from datetime import datetime
from jinja2 import Template
from src.models.database import get_database_session, User, LoanProduct, UserLoanMatch, ProcessingLog
import os

class EmailNotificationService:
    def __init__(self):
        self.ses_client = boto3.client('ses', region_name=os.getenv('SES_REGION', 'us-east-1'))
        self.from_email = os.getenv('SES_FROM_EMAIL', 'noreply@yourdomain.com')
        
        # Email templates
        self.email_template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personal Loan Matches</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #667eea;
        }
        .header h1 {
            color: #667eea;
            margin: 0;
            font-size: 28px;
        }
        .header p {
            color: #666;
            margin: 10px 0 0 0;
            font-size: 16px;
        }
        .greeting {
            font-size: 18px;
            margin-bottom: 20px;
            color: #333;
        }
        .loan-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            background: #fafafa;
            transition: all 0.3s ease;
        }
        .loan-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .loan-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .loan-name {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin: 0;
        }
        .match-score {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .lender {
            color: #666;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .loan-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        .detail-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .detail-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .detail-value {
            font-size: 16px;
            font-weight: bold;
            color: #333;
        }
        .eligibility-status {
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 15px;
        }
        .eligible {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .likely-eligible {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeaa7;
        }
        .needs-review {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .reasons {
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .reasons h4 {
            margin: 0 0 10px 0;
            color: #333;
            font-size: 16px;
        }
        .reasons ul {
            margin: 0;
            padding-left: 20px;
        }
        .reasons li {
            margin-bottom: 5px;
            color: #666;
        }
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            text-align: center;
            transition: all 0.3s ease;
        }
        .cta-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 14px;
        }
        .disclaimer {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
            line-height: 1.4;
        }
        @media (max-width: 600px) {
            .loan-details {
                grid-template-columns: 1fr;
            }
            .loan-header {
                flex-direction: column;
                align-items: flex-start;
            }
            .match-score {
                margin-top: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏦 Your Personal Loan Matches</h1>
            <p>We found {{ matches|length }} loan product{{ 's' if matches|length != 1 else '' }} that match your profile</p>
        </div>
        
        <div class="greeting">
            Hello! Based on your financial profile, we've identified some personal loan options that you may qualify for.
        </div>
        
        {% for match in matches %}
        <div class="loan-card">
            <div class="loan-header">
                <h3 class="loan-name">{{ match.product.product_name }}</h3>
                <div class="match-score">{{ (match.match_score * 100)|round|int }}% Match</div>
            </div>
            
            <div class="lender">by {{ match.product.lender_name }}</div>
            
            <div class="eligibility-status {{ match.eligibility_status.replace('_', '-') }}">
                {% if match.eligibility_status == 'eligible' %}
                    ✅ Likely Eligible
                {% elif match.eligibility_status == 'likely_eligible' %}
                    ⚡ Good Match
                {% else %}
                    📋 Needs Review
                {% endif %}
            </div>
            
            <div class="loan-details">
                <div class="detail-item">
                    <div class="detail-label">Interest Rate</div>
                    <div class="detail-value">{{ match.product.interest_rate_min }}% - {{ match.product.interest_rate_max }}%</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Loan Amount</div>
                    <div class="detail-value">${{ "{:,.0f}".format(match.product.min_loan_amount) }} - ${{ "{:,.0f}".format(match.product.max_loan_amount) }}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Min Credit Score</div>
                    <div class="detail-value">{{ match.product.min_credit_score or 'Not specified' }}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Min Income</div>
                    <div class="detail-value">${{ "{:,.0f}".format(match.product.min_income_required) if match.product.min_income_required else 'Not specified' }}</div>
                </div>
            </div>
            
            {% if match.reasons %}
            <div class="reasons">
                <h4>Why this might be a good fit:</h4>
                <ul>
                    {% for reason in match.reasons %}
                    <li>{{ reason }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if match.product.product_url %}
            <a href="{{ match.product.product_url }}" class="cta-button">Learn More & Apply</a>
            {% endif %}
        </div>
        {% endfor %}
        
        <div class="footer">
            <p><strong>Next Steps:</strong></p>
            <p>Review each option carefully and compare terms. Consider applying to multiple lenders to get the best rates.</p>
            
            <div class="disclaimer">
                <strong>Disclaimer:</strong> These matches are based on the information you provided and general eligibility criteria. 
                Final approval depends on the lender's complete underwriting process. Interest rates and terms may vary based on 
                your complete financial profile. We recommend comparing multiple offers before making a decision.
            </div>
        </div>
    </div>
</body>
</html>
        """)
    
    def send_loan_matches_email(self, user: User, matches: List[UserLoanMatch]) -> bool:
        """
        Send personalized loan matches email to a user
        """
        try:
            if not matches:
                print(f"No matches to send for user {user.user_id}")
                return False
            
            # Prepare match data for template
            match_data = []
            for match in matches:
                try:
                    reasons = json.loads(match.match_reasons) if match.match_reasons else []
                except json.JSONDecodeError:
                    reasons = [match.match_reasons] if match.match_reasons else []
                
                match_data.append({
                    'product': match.loan_product,
                    'match_score': match.match_score,
                    'eligibility_status': match.eligibility_status,
                    'reasons': reasons
                })
            
            # Sort matches by score
            match_data.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Generate email content
            html_content = self.email_template.render(matches=match_data)
            
            # Create subject line
            subject = f"🏦 {len(matches)} Personal Loan Match{'es' if len(matches) > 1 else ''} Found for You"
            
            # Send email via SES
            response = self.ses_client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [user.email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                        'Text': {'Data': self._generate_text_content(match_data), 'Charset': 'UTF-8'}
                    }
                }
            )
            
            print(f"Email sent successfully to {user.email}. Message ID: {response['MessageId']}")
            return True
            
        except Exception as e:
            print(f"Error sending email to {user.email}: {e}")
            return False
    
    def _generate_text_content(self, matches: List[Dict]) -> str:
        """Generate plain text version of the email"""
        text_content = "Your Personal Loan Matches\n"
        text_content += "=" * 30 + "\n\n"
        
        text_content += f"We found {len(matches)} loan product{'s' if len(matches) != 1 else ''} that match your profile:\n\n"
        
        for i, match in enumerate(matches, 1):
            product = match['product']
            text_content += f"{i}. {product.product_name}\n"
            text_content += f"   Lender: {product.lender_name}\n"
            text_content += f"   Match Score: {int(match['match_score'] * 100)}%\n"
            text_content += f"   Interest Rate: {product.interest_rate_min}% - {product.interest_rate_max}%\n"
            text_content += f"   Loan Amount: ${product.min_loan_amount:,.0f} - ${product.max_loan_amount:,.0f}\n"
            
            if match['reasons']:
                text_content += f"   Why it's a good fit:\n"
                for reason in match['reasons']:
                    text_content += f"   - {reason}\n"
            
            if product.product_url:
                text_content += f"   Learn more: {product.product_url}\n"
            
            text_content += "\n"
        
        text_content += "Next Steps:\n"
        text_content += "Review each option carefully and compare terms. Consider applying to multiple lenders to get the best rates.\n\n"
        
        text_content += "Disclaimer: These matches are based on the information you provided and general eligibility criteria. "
        text_content += "Final approval depends on the lender's complete underwriting process."
        
        return text_content
    
    def send_notifications_for_new_matches(self) -> Dict:
        """
        Send email notifications for all users with new matches
        """
        session = get_database_session()
        
        # Log start of notification process
        log_entry = ProcessingLog(
            process_type='notification',
            status='started',
            details='Starting email notification process'
        )
        session.add(log_entry)
        session.commit()
        
        try:
            # Get users with unsent match notifications
            users_with_matches = session.query(User).join(UserLoanMatch).filter(
                UserLoanMatch.notification_sent == False
            ).distinct().all()
            
            if not users_with_matches:
                log_entry.status = 'completed'
                log_entry.details = 'No users with unsent notifications found'
                log_entry.completed_at = datetime.utcnow()
                session.commit()
                return {'success': True, 'emails_sent': 0, 'users_notified': 0}
            
            emails_sent = 0
            users_notified = 0
            
            for user in users_with_matches:
                try:
                    # Get unsent matches for this user
                    unsent_matches = session.query(UserLoanMatch).filter(
                        UserLoanMatch.user_id == user.id,
                        UserLoanMatch.notification_sent == False
                    ).all()
                    
                    if unsent_matches:
                        # Send email
                        if self.send_loan_matches_email(user, unsent_matches):
                            # Mark notifications as sent
                            for match in unsent_matches:
                                match.notification_sent = True
                                match.notification_sent_at = datetime.utcnow()
                            
                            emails_sent += 1
                            users_notified += 1
                            
                            session.commit()
                            
                            # Rate limiting
                            import time
                            time.sleep(1)  # 1 second between emails to respect SES limits
                        
                except Exception as e:
                    print(f"Error sending notification to user {user.user_id}: {e}")
                    continue
            
            # Update log with success
            log_entry.status = 'completed'
            log_entry.records_processed = users_notified
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = f'Successfully sent {emails_sent} emails to {users_notified} users'
            session.commit()
            
            return {
                'success': True,
                'emails_sent': emails_sent,
                'users_notified': users_notified
            }
            
        except Exception as e:
            # Update log with error
            log_entry.status = 'failed'
            log_entry.completed_at = datetime.utcnow()
            log_entry.details = f'Error during notification process: {str(e)}'
            session.commit()
            raise
        finally:
            session.close()

def run_email_notifications():
    """
    Main function to run email notifications
    """
    try:
        email_service = EmailNotificationService()
        result = email_service.send_notifications_for_new_matches()
        
        print(f"Email notifications completed:")
        print(f"- Emails sent: {result['emails_sent']}")
        print(f"- Users notified: {result['users_notified']}")
        
        return result
        
    except Exception as e:
        print(f"Error in email notification process: {e}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    result = run_email_notifications()
    print(json.dumps(result, indent=2))
