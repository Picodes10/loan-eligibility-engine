#!/bin/bash

# Loan Eligibility Engine Deployment Script
# This script deploys the complete system including AWS infrastructure and n8n workflows

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="loan-eligibility-engine"
STAGE=${1:-dev}
REGION=${2:-us-east-1}

echo -e "${BLUE}🚀 Starting deployment of Loan Eligibility Engine...${NC}"
echo -e "${BLUE}Stage: ${STAGE}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Serverless Framework is installed
    if ! command -v serverless &> /dev/null; then
        print_error "Serverless Framework is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_status "All prerequisites are satisfied"
}

# Setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        cat > .env << EOF
# AWS Configuration
AWS_REGION=${REGION}
STAGE=${STAGE}

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_DB=loan_engine
POSTGRES_USER=admin
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# n8n Configuration
N8N_WEBHOOK_URL=http://localhost:5678

# OpenAI Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Email Configuration (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Slack Webhook (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK_URL
EOF
        print_warning "Created .env file. Please update it with your actual credentials."
    else
        print_status ".env file already exists"
    fi
    
    # Source environment variables
    export $(cat .env | grep -v '^#' | xargs)
}

# Deploy AWS infrastructure
deploy_aws_infrastructure() {
    print_status "Deploying AWS infrastructure..."
    
    # Install serverless plugins
    npm install -g serverless-python-requirements
    
    # Deploy using Serverless Framework
    serverless deploy --stage ${STAGE} --region ${REGION} --verbose
    
    if [ $? -eq 0 ]; then
        print_status "AWS infrastructure deployed successfully"
        
        # Get the API Gateway URL
        API_URL=$(aws cloudformation describe-stacks \
            --stack-name ${PROJECT_NAME}-${STAGE} \
            --region ${REGION} \
            --query 'Stacks[0].Outputs[?OutputKey==`ServiceEndpoint`].OutputValue' \
            --output text)
        
        echo "API Gateway URL: ${API_URL}"
        
        # Update .env with the API URL
        sed -i "s|API_GATEWAY_URL=.*|API_GATEWAY_URL=${API_URL}|" .env
        
    else
        print_error "Failed to deploy AWS infrastructure"
        exit 1
    fi
}

# Setup local development environment
setup_local_environment() {
    print_status "Setting up local development environment..."
    
    # Start n8n and PostgreSQL using Docker Compose
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Local services are running"
        echo "n8n Dashboard: http://localhost:5678"
        echo "PostgreSQL: localhost:5432"
    else
        print_error "Failed to start local services"
        exit 1
    fi
}

# Initialize database
initialize_database() {
    print_status "Initializing database..."
    
    # Run database setup script
    python scripts/setup_database.py
    
    if [ $? -eq 0 ]; then
        print_status "Database initialized successfully"
    else
        print_error "Failed to initialize database"
        exit 1
    fi
}

# Import n8n workflows
import_n8n_workflows() {
    print_status "Importing n8n workflows..."
    
    # Create workflows directory if it doesn't exist
    mkdir -p n8n_workflows
    
    # Copy workflow files
    cp workflows/*.json n8n_workflows/
    
    print_status "n8n workflows copied to n8n_workflows directory"
    print_warning "Please import the workflows manually in the n8n dashboard:"
    echo "1. Open http://localhost:5678"
    echo "2. Go to Workflows"
    echo "3. Import each workflow from the n8n_workflows directory"
}

# Setup monitoring and logging
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Create CloudWatch dashboard
    cat > cloudwatch-dashboard.json << EOF
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Duration", "FunctionName", "${PROJECT_NAME}-${STAGE}-csvUploadHandler"],
                    [".", "Errors", ".", "."],
                    [".", "Invocations", ".", "."]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "${REGION}",
                "title": "Lambda Function Metrics"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/S3", "NumberOfObjects", "BucketName", "${PROJECT_NAME}-${STAGE}-uploads"],
                    [".", "BucketSizeBytes", ".", "."]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "${REGION}",
                "title": "S3 Bucket Metrics"
            }
        }
    ]
}
EOF
    
    # Create the dashboard
    aws cloudwatch put-dashboard \
        --dashboard-name "${PROJECT_NAME}-${STAGE}-dashboard" \
        --dashboard-body file://cloudwatch-dashboard.json \
        --region ${REGION}
    
    print_status "CloudWatch dashboard created"
}

# Run tests
run_tests() {
    print_status "Running tests..."
    
    # Create a simple test script
    cat > test_system.py << EOF
#!/usr/bin/env python3
import requests
import json
import time

def test_api_health():
    try:
        response = requests.get('${API_URL}/api/health')
        if response.status_code == 200:
            print("✅ API health check passed")
            return True
        else:
            print("❌ API health check failed")
            return False
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False

def test_csv_upload():
    try:
        # Create a sample CSV file
        csv_content = "user_id,email,monthly_income,credit_score,employment_status,age\\n"
        csv_content += "test_001,test@example.com,50000,750,employed,30\\n"
        
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        response = requests.post('${API_URL}/upload-csv', files=files)
        
        if response.status_code == 200:
            print("✅ CSV upload test passed")
            return True
        else:
            print("❌ CSV upload test failed")
            return False
    except Exception as e:
        print(f"❌ CSV upload test error: {e}")
        return False

if __name__ == "__main__":
    print("Running system tests...")
    
    health_ok = test_api_health()
    upload_ok = test_csv_upload()
    
    if health_ok and upload_ok:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed")
        exit(1)
EOF
    
    # Run tests
    python test_system.py
    
    # Clean up test file
    rm test_system.py
}

# Main deployment function
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Loan Eligibility Engine Deployment${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    
    check_prerequisites
    setup_environment
    deploy_aws_infrastructure
    setup_local_environment
    initialize_database
    import_n8n_workflows
    setup_monitoring
    run_tests
    
    echo ""
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Access Points:${NC}"
    echo "• Web UI: ${API_URL}"
    echo "• n8n Dashboard: http://localhost:5678"
    echo "• API Documentation: ${API_URL}/api/health"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Import n8n workflows from the n8n dashboard"
    echo "2. Configure email settings in .env file"
    echo "3. Set up Slack webhook for notifications"
    echo "4. Upload your first CSV file through the web UI"
    echo ""
    echo -e "${YELLOW}Note: Remember to update the .env file with your actual credentials!${NC}"
}

# Run main function
main "$@"
