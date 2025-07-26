# 🚀 Automated Loan Matching System - Setup & Run Guide

## 📋 Prerequisites

### Required Software
1. **Python 3.9+** - [Download Python](https://www.python.org/downloads/)
2. **Node.js 16+** - [Download Node.js](https://nodejs.org/)
3. **Docker & Docker Compose** - [Download Docker](https://www.docker.com/products/docker-desktop/)
4. **PostgreSQL** (or use AWS RDS)
5. **AWS CLI** - [Install AWS CLI](https://aws.amazon.com/cli/)

### Required Accounts & API Keys
1. **AWS Account** - For RDS, Lambda, S3, SES
2. **Google AI Studio** - For Gemini API key ([Get API Key](https://makersuite.google.com/app/apikey))

## 🛠️ Step-by-Step Setup

### Step 1: Environment Setup

1. **Clone/Navigate to the project directory:**
   ```bash
   cd c:\Users\DELL\Desktop\demo
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Serverless Framework:**
   ```bash
   npm install -g serverless
   npm install serverless-python-requirements
   ```

### Step 2: Configure Environment Variables

1. **Copy the environment template:**
   ```bash
   copy .env.example .env
   ```

2. **Edit `.env` file with your credentials:**
   ```env
   # Database Configuration (Use AWS RDS or local PostgreSQL)
   DB_HOST=your-rds-endpoint.amazonaws.com
   DB_NAME=loan_matching_db
   DB_USER=postgres
   DB_PASSWORD=your-secure-password

   # n8n Configuration
   N8N_WEBHOOK_URL=http://localhost:5678/webhook/user-matching

   # AI Configuration
   GEMINI_API_KEY=your-gemini-api-key-here

   # AWS Configuration
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key

   # Email Configuration
   SES_FROM_EMAIL=noreply@yourdomain.com
   SES_REGION=us-east-1
   ```

### Step 3: AWS Setup

1. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

2. **Create RDS PostgreSQL instance** (or use local PostgreSQL):
   - Go to AWS RDS Console
   - Create PostgreSQL database (db.t3.micro for free tier)
   - Note the endpoint, username, and password
   - Update `.env` file with database details

3. **Set up AWS SES:**
   - Go to AWS SES Console
   - Verify your sender email address
   - If in sandbox mode, verify recipient emails too

### Step 4: Database Setup

1. **Run database setup script:**
   ```bash
   python scripts/setup_database.py
   ```

   This will:
   - Create all required tables
   - Add sample loan products for testing

### Step 5: Start n8n Workflow Engine

1. **Start n8n with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Access n8n interface:**
   - Open browser: http://localhost:5678
   - Login: admin / admin123

3. **Import workflows:**
   - In n8n interface, go to "Workflows"
   - Import each workflow JSON file from `n8n/workflows/` folder:
     - `workflow-a-loan-discovery.json`
     - `workflow-b-user-matching.json`
     - `workflow-c-notifications.json`

### Step 6: Start API Server

1. **Start the Flask API server:**
   ```bash
   python api_server.py
   ```

   The API server will run on http://localhost:8000

## 🎯 Running the Application

### Option A: Local Development (Recommended for Testing)

1. **Start all services:**
   ```bash
   # Terminal 1: Start n8n
   docker-compose up -d

   # Terminal 2: Start API server
   python api_server.py

   # Terminal 3: Start web interface (if using serverless offline)
   serverless offline
   ```

2. **Access the web interface:**
   - Open browser: http://localhost:3000 (or your serverless offline URL)
   - Upload the sample CSV file: `sample_data/sample_users.csv`

### Option B: AWS Deployment (Production)

1. **Deploy to AWS:**
   ```bash
   # Deploy serverless infrastructure
   serverless deploy

   # Note the API Gateway URL from the output
   ```

2. **Update n8n workflow URLs:**
   - In n8n workflows, replace `http://host.docker.internal:8000` with your API Gateway URL

3. **Upload CSV via the deployed web interface**

## 📊 Testing the Complete Pipeline

### Test Flow:
1. **Upload CSV** → Triggers Lambda function
2. **CSV Processing** → Stores users in database
3. **Webhook Trigger** → Starts n8n matching workflow
4. **Loan Matching** → AI-powered matching engine
5. **Email Notifications** → Sends personalized emails

### Monitor Progress:
- **n8n Dashboard**: http://localhost:5678 - View workflow executions
- **API Logs**: Check terminal running `api_server.py`
- **Database**: Query tables to see processed data

## 🔧 Manual Testing Commands

### Test Individual Components:

1. **Test Loan Discovery:**
   ```bash
   python -c "from src.scrapers.loan_discovery import run_loan_discovery; print(run_loan_discovery())"
   ```

2. **Test Matching Engine:**
   ```bash
   python -c "from src.matching.loan_matcher import run_user_loan_matching; print(run_user_loan_matching())"
   ```

3. **Test Email Notifications:**
   ```bash
   python -c "from src.notifications.email_service import run_email_notifications; print(run_email_notifications())"
   ```

## 📁 Project Structure
```
loan-matching-system/
├── src/
│   ├── models/database.py          # Database models
│   ├── handlers/                   # AWS Lambda handlers
│   ├── scrapers/loan_discovery.py  # Web scraping engine
│   ├── matching/loan_matcher.py    # AI matching engine
│   └── notifications/email_service.py # Email system
├── n8n/workflows/                  # n8n workflow definitions
├── scripts/setup_database.py       # Database setup
├── sample_data/sample_users.csv    # Test data
├── api_server.py                   # Local API server
├── docker-compose.yml              # n8n setup
├── serverless.yml                  # AWS deployment
└── requirements.txt                # Python dependencies
```

## 🚨 Troubleshooting

### Common Issues:

1. **Database Connection Error:**
   - Check `.env` file database credentials
   - Ensure PostgreSQL is running
   - For AWS RDS, check security groups

2. **n8n Workflows Not Triggering:**
   - Check webhook URLs in workflows
   - Ensure API server is running on port 8000
   - Verify n8n can reach the API server

3. **Email Not Sending:**
   - Verify AWS SES setup and email verification
   - Check SES sending limits (sandbox mode)
   - Confirm `.env` email configuration

4. **AI Matching Errors:**
   - Verify Gemini API key is valid
   - Check API quota limits
   - Ensure internet connectivity

### Logs to Check:
- n8n execution logs in the web interface
- API server terminal output
- AWS CloudWatch logs (for deployed version)

## 🎉 Success Indicators

When everything is working correctly, you should see:
1. ✅ CSV file uploaded successfully
2. ✅ Users processed and stored in database
3. ✅ n8n workflows executing in sequence
4. ✅ Loan matches created with AI scoring
5. ✅ Personalized emails sent to users

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Ensure all services are running
4. Check logs for specific error messages
