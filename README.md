# Loan Eligibility Engine

A comprehensive automated system that ingests user data, discovers personal loan products from public websites, matches users to eligible products, and notifies them. This project demonstrates integration of cloud services with a powerful, self-hosted workflow automation engine.

## 🚀 Features

- **CSV Data Ingestion**: Upload and process user data via web interface
- **Automated Loan Discovery**: Web scraping of loan products from multiple sources
- **Intelligent Matching**: AI-powered algorithm to match users with suitable loan products
- **Real-time Notifications**: Email notifications to users about new matches
- **Modern Web UI**: Responsive dashboard for monitoring and management
- **Scalable Architecture**: Serverless AWS infrastructure with n8n workflows
- **Comprehensive Logging**: Detailed processing logs and monitoring

## 🏗️ Architecture

### Components

1. **AWS Lambda Functions**
   - `csv_upload_handler`: Handles CSV file uploads to S3
   - `csv_processor`: Processes uploaded CSV files and stores user data
   - `api_gateway`: Main API endpoint for web UI and REST API

2. **Database Layer**
   - PostgreSQL database for storing users, loan products, and matches
   - Optimized queries and indexes for performance
   - Comprehensive logging and audit trails

3. **n8n Workflows**
   - **Loan Discovery**: Automated scraping of loan products from websites
   - **User Matching**: Intelligent matching algorithm execution
   - **User Notification**: Email notification system

4. **Web Interface**
   - Modern, responsive dashboard
   - Real-time statistics and monitoring
   - Drag-and-drop file upload
   - Processing status tracking

### Data Flow

```
CSV Upload → S3 → Lambda Processor → PostgreSQL → n8n Matching → Email Notifications
     ↓
Web Scraping → Loan Products → Matching Algorithm → User Matches
```

## 🛠️ Technology Stack

- **Backend**: Python 3.9, AWS Lambda, API Gateway
- **Database**: PostgreSQL 15
- **Workflow Engine**: n8n
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Infrastructure**: AWS (S3, RDS, CloudWatch), Docker
- **Deployment**: Serverless Framework

## 📋 Prerequisites

Before deploying, ensure you have:

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate permissions
- [Serverless Framework](https://www.serverless.com/) installed globally
- [Docker](https://www.docker.com/) and Docker Compose installed
- [Python 3.9+](https://www.python.org/) installed
- [Node.js](https://nodejs.org/) (for serverless deployment)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd loan-eligibility-engine
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
npm install -g serverless-python-requirements
```

### 3. Configure Environment

Create a `.env` file with your configuration:

```bash
# AWS Configuration
AWS_REGION=us-east-1
STAGE=dev

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_DB=loan_engine
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_secure_password

# n8n Configuration
N8N_WEBHOOK_URL=http://localhost:5678

# OpenAI Configuration (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Slack Webhook (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR_WEBHOOK_URL
```

### 4. Deploy the System

Run the deployment script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh dev us-east-1
```

This will:
- Deploy AWS infrastructure (Lambda, S3, RDS, API Gateway)
- Start local services (n8n, PostgreSQL)
- Initialize database with schema and sample data
- Set up monitoring and logging

### 5. Import n8n Workflows

1. Open the n8n dashboard: http://localhost:5678
2. Go to Workflows
3. Import the workflow files from the `workflows/` directory:
   - `loan_discovery.json`
   - `user_matching.json`
   - `user_notification.json`

### 6. Access the System

- **Web UI**: Available at the API Gateway URL (displayed after deployment)
- **n8n Dashboard**: http://localhost:5678
- **API Documentation**: `/api/health` endpoint

## 📊 Usage

### Uploading User Data

1. Prepare a CSV file with the following columns:
   ```
   user_id,email,monthly_income,credit_score,employment_status,age
   user_001,john@example.com,50000,750,employed,30
   user_002,jane@example.com,35000,680,employed,28
   ```

   **Note**: The system includes a sample `users.csv` file with 10,000+ user records for testing. You can use this file directly or create your own following the same format.

2. Access the web UI and drag-and-drop your CSV file
3. Monitor the processing status in real-time
4. View matches and statistics in the dashboard

### Monitoring

- **CloudWatch Dashboard**: Automatic metrics and logging
- **Processing Logs**: Track batch processing status
- **Real-time Statistics**: View system performance in the web UI

### Workflow Management

- **Loan Discovery**: Runs daily to discover new loan products
- **User Matching**: Triggered automatically when new users are processed
- **Notifications**: Sends emails every 6 hours for new matches

## 🔧 Configuration

### Database Schema

The system uses the following main tables:

- `users`: User profile data
- `loan_products`: Discovered loan products
- `matches`: User-product matches with scores
- `processing_logs`: Batch processing status
- `email_notifications`: Sent notification records

### Matching Algorithm

The matching algorithm considers:
- Credit score compatibility (30% weight)
- Income requirements (25% weight)
- Age restrictions (15% weight)
- Employment status (15% weight)
- Interest rate competitiveness (15% weight)

### Email Templates

Customizable email templates for user notifications with:
- Personalized match recommendations
- Product details and eligibility criteria
- Direct links to lender websites
- Professional styling and branding


## 📝 API Documentation

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI |
| GET | `/api/health` | Health check |
| POST | `/upload-csv` | Upload CSV file |
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| GET | `/api/users/{id}` | Get user matches |
| GET | `/api/products` | List loan products |
| POST | `/api/matches` | Create matches |
| GET | `/api/status` | Check processing status |


