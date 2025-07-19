# Loan Eligibility Engine - Testing Guide

## 🚀 Quick Start

### Prerequisites Check

Before running the application, ensure you have the following installed:

```bash
# Check if required tools are installed
node --version          # Should be v16 or higher
npm --version           # Should be v8 or higher
docker --version        # Should be v20 or higher
docker-compose --version # Should be v2 or higher
aws --version           # Should be v2 or higher
serverless --version    # Should be v3 or higher
```

### 1. Initial Setup

```bash
# Clone or navigate to the project directory
cd loan-eligibility-engine

# Install dependencies
npm install

# Create environment file
cp .env.example .env
```

### 2. Configure Environment Variables

Edit the `.env` file with your AWS credentials and settings:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=loan_eligibility
DB_USER=postgres
DB_PASSWORD=your_password

# Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# n8n Configuration
N8N_BASE_URL=http://localhost:5678
N8N_WEBHOOK_URL=http://localhost:5678/webhook

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🏃‍♂️ Running the Application

### Option 1: Full Deployment (Recommended)

```bash
# Run the complete deployment script
./scripts/deploy.sh dev us-east-1
```

This script will:
- ✅ Check all prerequisites
- ✅ Deploy AWS infrastructure
- ✅ Start local services (n8n, PostgreSQL)
- ✅ Initialize database
- ✅ Import n8n workflows
- ✅ Run system tests

### Option 2: Manual Step-by-Step

#### Step 1: Deploy AWS Infrastructure

```bash
# Deploy serverless infrastructure
serverless deploy --stage dev --region us-east-1

# Verify deployment
serverless info --stage dev
```

#### Step 2: Start Local Services

```bash
# Start PostgreSQL and n8n via Docker
docker-compose up -d

# Check if services are running
docker-compose ps
```

#### Step 3: Initialize Database

```bash
# Run database setup script
python scripts/setup_database.py

# Verify database connection
python -c "
from lambda_function.database_manager import DatabaseManager
db = DatabaseManager()
print('Database connection successful!')
db.close()
"
```

#### Step 4: Import n8n Workflows

1. Open n8n in your browser: `http://localhost:5678`
2. Import the workflows from the `workflows/` directory:
   - `loan_discovery.json`
   - `user_matching.json`
   - `user_notification.json`

## 🧪 Testing the Application

### 1. Web Interface Testing

#### Access the Web UI

```bash
# Get the API Gateway URL
aws apigateway get-rest-apis --region us-east-1

# The web UI will be available at:
# https://[api-id].execute-api.us-east-1.amazonaws.com/dev/
```

#### Test File Upload

1. **Open the web interface** in your browser
2. **Drag and drop** the `users.csv` file onto the upload area
3. **Monitor the upload progress** in real-time
4. **Check the processing status** on the dashboard

#### Expected Results:
- ✅ File uploads successfully
- ✅ Processing status updates in real-time
- ✅ Statistics update after processing
- ✅ Recent matches appear in the dashboard

### 2. API Testing

#### Test API Endpoints

```bash
# Get the API base URL
API_BASE="https://[api-id].execute-api.us-east-1.amazonaws.com/dev"

# Test health check
curl -X GET "$API_BASE/health"

# Test system stats
curl -X GET "$API_BASE/api/stats"

# Test users endpoint
curl -X GET "$API_BASE/api/users?page=1&limit=10"

# Test products endpoint
curl -X GET "$API_BASE/api/products"

# Test matches endpoint
curl -X GET "$API_BASE/api/matches?page=1&limit=10"
```

#### Expected API Responses:

**Health Check:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

**System Stats:**
```json
{
  "total_users": 10002,
  "total_products": 4,
  "total_matches": 150,
  "processing_status": "completed",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### 3. Database Testing

#### Test Database Operations

```bash
# Create a test script
cat > test_db.py << 'EOF'
from lambda_function.database_manager import DatabaseManager
import json

db = DatabaseManager()

# Test connection
print("Testing database connection...")
try:
    db.test_connection()
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")

# Test user count
print("\nTesting user count...")
try:
    count = db.get_user_count()
    print(f"✅ Total users: {count}")
except Exception as e:
    print(f"❌ Failed to get user count: {e}")

# Test sample users
print("\nTesting user retrieval...")
try:
    users = db.get_users(page=1, limit=5)
    print(f"✅ Retrieved {len(users)} users")
    for user in users[:2]:
        print(f"  - {user['name']} ({user['email']})")
except Exception as e:
    print(f"❌ Failed to retrieve users: {e}")

# Test products
print("\nTesting product retrieval...")
try:
    products = db.get_loan_products()
    print(f"✅ Retrieved {len(products)} products")
    for product in products:
        print(f"  - {product['name']} (Min credit: {product['min_credit_score']})")
except Exception as e:
    print(f"❌ Failed to retrieve products: {e}")

db.close()
print("\n✅ Database testing completed")
EOF

# Run the test
python test_db.py
```

### 4. n8n Workflow Testing

#### Test Loan Discovery Workflow

1. **Open n8n**: `http://localhost:5678`
2. **Navigate to** the "Loan Discovery" workflow
3. **Click "Execute Workflow"**
4. **Monitor the execution** in real-time
5. **Check the results** in the database

#### Expected Results:
- ✅ Workflow executes successfully
- ✅ Loan products are scraped from websites
- ✅ Data is stored in the database
- ✅ Logs show successful processing

#### Test User Matching Workflow

1. **Navigate to** the "User Matching" workflow
2. **Trigger the workflow** manually or via webhook
3. **Monitor the matching process**
4. **Check generated matches** in the database

#### Expected Results:
- ✅ Users are matched to eligible products
- ✅ Match scores are calculated correctly
- ✅ Matches are stored with reasons
- ✅ Processing logs are created

#### Test User Notification Workflow

1. **Navigate to** the "User Notification" workflow
2. **Execute the workflow** manually
3. **Check email delivery** (if configured)
4. **Verify notification logs**

#### Expected Results:
- ✅ Emails are generated with personalized content
- ✅ Notifications are sent to matched users
- ✅ Delivery logs are created
- ✅ Slack notifications are sent (if configured)

### 5. End-to-End Testing

#### Complete User Journey Test

```bash
# Create a comprehensive test script
cat > e2e_test.py << 'EOF'
import requests
import time
import json

# Configuration
API_BASE = "https://[api-id].execute-api.us-east-1.amazonaws.com/dev"

def test_end_to_end():
    print("🚀 Starting End-to-End Test")
    
    # 1. Test health check
    print("\n1. Testing health check...")
    response = requests.get(f"{API_BASE}/health")
    assert response.status_code == 200
    print("✅ Health check passed")
    
    # 2. Check initial stats
    print("\n2. Checking initial stats...")
    response = requests.get(f"{API_BASE}/api/stats")
    assert response.status_code == 200
    stats = response.json()
    print(f"✅ Initial stats: {stats['total_users']} users, {stats['total_products']} products")
    
    # 3. Test user retrieval
    print("\n3. Testing user retrieval...")
    response = requests.get(f"{API_BASE}/api/users?page=1&limit=5")
    assert response.status_code == 200
    users = response.json()
    print(f"✅ Retrieved {len(users)} users")
    
    # 4. Test product retrieval
    print("\n4. Testing product retrieval...")
    response = requests.get(f"{API_BASE}/api/products")
    assert response.status_code == 200
    products = response.json()
    print(f"✅ Retrieved {len(products)} products")
    
    # 5. Test matches retrieval
    print("\n5. Testing matches retrieval...")
    response = requests.get(f"{API_BASE}/api/matches?page=1&limit=5")
    assert response.status_code == 200
    matches = response.json()
    print(f"✅ Retrieved {len(matches)} matches")
    
    print("\n🎉 End-to-End Test Completed Successfully!")

if __name__ == "__main__":
    test_end_to_end()
EOF

# Run the end-to-end test
python e2e_test.py
```

## 🔍 Monitoring and Debugging

### 1. CloudWatch Logs

```bash
# View Lambda function logs
aws logs describe-log-groups --region us-east-1

# Get recent logs for CSV processor
aws logs tail /aws/lambda/loan-eligibility-engine-dev-csv-processor --follow

# Get recent logs for API gateway
aws logs tail /aws/lambda/loan-eligibility-engine-dev-api-gateway --follow
```

### 2. Database Monitoring

```bash
# Connect to PostgreSQL
docker exec -it loan-eligibility-engine_postgres_1 psql -U postgres -d loan_eligibility

# Check recent activity
SELECT * FROM processing_logs ORDER BY created_at DESC LIMIT 10;

# Check user processing status
SELECT status, COUNT(*) FROM users GROUP BY status;

# Check match generation
SELECT COUNT(*) as total_matches FROM user_loan_matches;
```

### 3. n8n Monitoring

1. **Open n8n dashboard**: `http://localhost:5678`
2. **Check workflow execution history**
3. **View detailed logs** for each node
4. **Monitor webhook triggers**

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Database Connection Failed
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres

# Check database logs
docker-compose logs postgres
```

#### Issue 2: Lambda Function Errors
```bash
# Check Lambda logs
aws logs tail /aws/lambda/loan-eligibility-engine-dev-csv-processor --follow

# Test Lambda function locally
serverless invoke local --function csv-processor --data '{"Records":[{"s3":{"bucket":{"name":"test-bucket"},"object":{"key":"test.csv"}}}]}'
```

#### Issue 3: n8n Workflow Failures
1. **Check n8n logs**: `docker-compose logs n8n`
2. **Verify webhook URLs** are correct
3. **Check workflow configuration** in n8n UI
4. **Test individual nodes** in the workflow

#### Issue 4: File Upload Issues
```bash
# Check S3 bucket permissions
aws s3 ls s3://loan-eligibility-engine-dev-uploads

# Test S3 upload manually
aws s3 cp users.csv s3://loan-eligibility-engine-dev-uploads/test.csv
```

#### Issue 5: API Gateway Issues
```bash
# Check API Gateway logs
aws logs tail /aws/apigateway/loan-eligibility-engine-dev --follow

# Test API endpoints directly
curl -v -X GET "https://[api-id].execute-api.us-east-1.amazonaws.com/dev/health"
```

## 📊 Performance Testing

### Load Testing

```bash
# Install Apache Bench (if not available)
# On Ubuntu: sudo apt-get install apache2-utils
# On macOS: brew install httpd

# Test API performance
ab -n 100 -c 10 "https://[api-id].execute-api.us-east-1.amazonaws.com/dev/health"

# Test file upload performance
ab -n 10 -c 2 -p users.csv -T "text/csv" "https://[api-id].execute-api.us-east-1.amazonaws.com/dev/upload"
```

### Database Performance

```bash
# Test database query performance
python -c "
from lambda_function.database_manager import DatabaseManager
import time

db = DatabaseManager()

# Test user retrieval performance
start_time = time.time()
users = db.get_users(page=1, limit=1000)
end_time = time.time()
print(f'Retrieved 1000 users in {end_time - start_time:.2f} seconds')

db.close()
"
```

## ✅ Success Criteria

Your application is working correctly if:

1. **✅ Web UI loads** without errors
2. **✅ File upload works** and shows progress
3. **✅ Database contains** users and products
4. **✅ API endpoints return** correct data
5. **✅ n8n workflows execute** successfully
6. **✅ Matches are generated** for users
7. **✅ Notifications are sent** (if email configured)
8. **✅ Monitoring shows** healthy system status

## 🎯 Next Steps After Testing

1. **Configure production settings** in `.env`
2. **Set up monitoring alerts** in CloudWatch
3. **Configure email notifications** for production
4. **Set up backup strategies** for the database
5. **Implement additional security measures**
6. **Scale the system** based on usage patterns

## 📞 Support

If you encounter issues:

1. **Check the logs** using the monitoring tools above
2. **Review the troubleshooting section**
3. **Verify all prerequisites** are installed correctly
4. **Ensure environment variables** are properly configured
5. **Check AWS service limits** and quotas

The system is designed to be robust and self-healing, but proper monitoring and testing will ensure optimal performance! 🚀 