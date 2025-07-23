#!/bin/bash

# Loan Eligibility Engine - Quick Start Script
# This script sets up and starts the application for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Loan Eligibility Engine...${NC}"
echo "=" * 50

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

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_status "Docker is running"

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating default configuration..."
    cp .env .env.backup 2>/dev/null || true
fi

print_status "Environment configuration ready"

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Start Docker services
print_status "Starting Docker services (PostgreSQL + n8n)..."
docker-compose down 2>/dev/null || true
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Check if PostgreSQL is ready
print_status "Checking PostgreSQL connection..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_status "PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "PostgreSQL failed to start"
        exit 1
    fi
    sleep 2
done

# Initialize database
print_status "Initializing database..."
python scripts/setup_database.py

# Start the Flask development server
print_status "Starting Flask development server..."

echo ""
echo -e "${GREEN}🎉 Loan Eligibility Engine is ready!${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "• Web Application: http://localhost:3000"
echo "• n8n Dashboard: http://localhost:5678 (admin/admin123)"
echo "• PostgreSQL: localhost:5432 (postgres/postgres123)"
echo ""
echo -e "${BLUE}Quick Test:${NC}"
echo "1. Open http://localhost:3000 in your browser"
echo "2. Upload the sample users.csv file"
echo "3. Check the system statistics"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the Flask app
python app.py