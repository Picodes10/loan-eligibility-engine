#!/bin/bash

# Loan Eligibility Engine - Quick Test Script
# This script performs basic testing of the application

set -e  # Exit on any error

echo "🚀 Loan Eligibility Engine - Quick Test"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if required tools are installed
check_tool() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

check_tool "node" || exit 1
check_tool "npm" || exit 1
check_tool "docker" || exit 1
check_tool "docker-compose" || exit 1
check_tool "aws" || exit 1
check_tool "serverless" || exit 1

print_success "All prerequisites are installed!"

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file with your AWS credentials and settings"
    else
        print_error ".env.example not found. Please create .env file manually"
        exit 1
    fi
fi

# Check if users.csv exists
if [ ! -f users.csv ]; then
    print_error "users.csv file not found in the current directory"
    exit 1
fi

print_success "Found users.csv file"

# Function to test database connection
test_database() {
    print_status "Testing database connection..."
    
    python3 -c "
from lambda_function.database_manager import DatabaseManager
try:
    db = DatabaseManager()
    db.test_connection()
    print('✅ Database connection successful')
    db.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" || return 1
    
    print_success "Database connection test passed"
}

# Function to test API endpoints
test_api() {
    print_status "Testing API endpoints..."
    
    # Get API Gateway URL
    API_ID=$(aws apigateway get-rest-apis --region us-east-1 --query 'items[?name==`loan-eligibility-engine-dev`].id' --output text 2>/dev/null || echo "")
    
    if [ -z "$API_ID" ]; then
        print_warning "API Gateway not found. Skipping API tests."
        return 0
    fi
    
    API_BASE="https://${API_ID}.execute-api.us-east-1.amazonaws.com/dev"
    
    # Test health endpoint
    print_status "Testing health endpoint..."
    if curl -s -f "$API_BASE/health" > /dev/null; then
        print_success "Health endpoint is working"
    else
        print_warning "Health endpoint is not responding"
    fi
    
    # Test stats endpoint
    print_status "Testing stats endpoint..."
    if curl -s -f "$API_BASE/api/stats" > /dev/null; then
        print_success "Stats endpoint is working"
    else
        print_warning "Stats endpoint is not responding"
    fi
}

# Function to test file upload
test_upload() {
    print_status "Testing file upload functionality..."
    
    # Check if S3 bucket exists
    BUCKET_NAME="loan-eligibility-engine-dev-uploads"
    if aws s3 ls "s3://$BUCKET_NAME" > /dev/null 2>&1; then
        print_success "S3 bucket exists"
        
        # Test upload
        if aws s3 cp users.csv "s3://$BUCKET_NAME/test-upload.csv" > /dev/null 2>&1; then
            print_success "File upload test successful"
            # Clean up test file
            aws s3 rm "s3://$BUCKET_NAME/test-upload.csv" > /dev/null 2>&1
        else
            print_warning "File upload test failed"
        fi
    else
        print_warning "S3 bucket not found. Skipping upload test."
    fi
}

# Function to test n8n workflows
test_n8n() {
    print_status "Testing n8n workflows..."
    
    # Check if n8n is running
    if curl -s -f "http://localhost:5678" > /dev/null 2>&1; then
        print_success "n8n is running"
        
        # Check if workflows exist
        if [ -f "workflows/loan_discovery.json" ] && \
           [ -f "workflows/user_matching.json" ] && \
           [ -f "workflows/user_notification.json" ]; then
            print_success "All workflow files exist"
        else
            print_warning "Some workflow files are missing"
        fi
    else
        print_warning "n8n is not running. Start it with: docker-compose up -d"
    fi
}

# Function to run basic database tests
run_database_tests() {
    print_status "Running database tests..."
    
    python3 -c "
from lambda_function.database_manager import DatabaseManager
import json

try:
    db = DatabaseManager()
    
    # Test user count
    count = db.get_user_count()
    print(f'✅ Total users in database: {count}')
    
    # Test product count
    products = db.get_loan_products()
    print(f'✅ Total products in database: {len(products)}')
    
    # Test match count
    matches = db.get_recent_matches(limit=1000)
    print(f'✅ Total matches in database: {len(matches)}')
    
    # Test system stats
    stats = db.get_system_stats()
    print(f'✅ System stats: {json.dumps(stats, indent=2)}')
    
    db.close()
    print('✅ Database tests completed successfully')
    
except Exception as e:
    print(f'❌ Database tests failed: {e}')
    exit(1)
" || return 1
    
    print_success "Database tests passed"
}

# Function to check system status
check_system_status() {
    print_status "Checking system status..."
    
    # Check if Docker containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker containers are running"
    else
        print_warning "Docker containers are not running"
    fi
    
    # Check if AWS services are accessible
    if aws sts get-caller-identity > /dev/null 2>&1; then
        print_success "AWS credentials are valid"
    else
        print_warning "AWS credentials may be invalid"
    fi
}

# Main test execution
main() {
    print_status "Starting comprehensive system test..."
    
    # Check system status
    check_system_status
    
    # Test database
    test_database
    
    # Run database tests
    run_database_tests
    
    # Test API endpoints
    test_api
    
    # Test file upload
    test_upload
    
    # Test n8n workflows
    test_n8n
    
    echo ""
    echo "🎉 Quick Test Completed!"
    echo "========================"
    print_success "Basic system functionality verified"
    print_status "For detailed testing, see TESTING_GUIDE.md"
    print_status "To start the full system: ./scripts/deploy.sh dev us-east-1"
}

# Run main function
main "$@" 