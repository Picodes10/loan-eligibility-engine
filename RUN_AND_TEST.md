# 🚀 How to Run and Test the Loan Eligibility Engine

## Quick Start (5 minutes)

### Step 1: Prerequisites Check
```bash
# Windows
quick_test.bat

# Linux/Mac
./quick_test.sh
```

This will check if you have all required tools installed and test basic functionality.

### Step 2: Configure Environment
1. **Create `.env` file** (if not exists):
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** with your settings:
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
   
   # Email Configuration (optional)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   ```

### Step 3: Deploy and Run
```bash
# Deploy everything (AWS + Local services)
./scripts/deploy.sh dev us-east-1
```

This single command will:
- ✅ Deploy AWS infrastructure (Lambda, S3, RDS, API Gateway)
- ✅ Start local services (n8n, PostgreSQL)
- ✅ Initialize database with sample data
- ✅ Import n8n workflows
- ✅ Run system tests

### Step 4: Access the Application
1. **Web UI**: Open the URL shown in the deployment output
2. **n8n Dashboard**: `http://localhost:5678`
3. **Database**: Connect via `localhost:5432`

## 🧪 Testing the Application

### Test 1: Web Interface
1. **Open the web UI** in your browser
2. **Drag and drop** the `users.csv` file
3. **Watch the upload progress** in real-time
4. **Check the dashboard** for statistics and recent matches

### Test 2: API Endpoints
```bash
# Get your API URL
aws apigateway get-rest-apis --region us-east-1

# Test endpoints (replace [api-id] with your actual ID)
API_BASE="https://[api-id].execute-api.us-east-1.amazonaws.com/dev"

# Health check
curl "$API_BASE/health"

# System stats
curl "$API_BASE/api/stats"

# Users
curl "$API_BASE/api/users?page=1&limit=5"

# Products
curl "$API_BASE/api/products"

# Matches
curl "$API_BASE/api/matches?page=1&limit=5"
```

### Test 3: Database
```bash
# Connect to database
docker exec -it loan-eligibility-engine_postgres_1 psql -U postgres -d loan_eligibility

# Check data
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM loan_products;
SELECT COUNT(*) FROM user_loan_matches;
```

### Test 4: n8n Workflows
1. **Open n8n**: `http://localhost:5678`
2. **Test Loan Discovery**:
   - Find "Loan Discovery" workflow
   - Click "Execute Workflow"
   - Check database for new products
3. **Test User Matching**:
   - Find "User Matching" workflow
   - Trigger manually or via webhook
   - Check for new matches
4. **Test Notifications**:
   - Find "User Notification" workflow
   - Execute manually
   - Check email delivery (if configured)

## 📊 Expected Results

### After Uploading users.csv:
- ✅ **10,000+ users** in database
- ✅ **Processing logs** created
- ✅ **Matches generated** for eligible users
- ✅ **Dashboard updated** with statistics

### After Running Workflows:
- ✅ **Loan products** scraped and stored
- ✅ **User matches** calculated and stored
- ✅ **Email notifications** sent (if configured)
- ✅ **Processing logs** updated

## 🔍 Monitoring

### Real-time Monitoring:
```bash
# Lambda logs
aws logs tail /aws/lambda/loan-eligibility-engine-dev-csv-processor --follow

# API Gateway logs
aws logs tail /aws/lambda/loan-eligibility-engine-dev-api-gateway --follow

# Docker logs
docker-compose logs -f
```

### Web Dashboard:
- **System Statistics**: Real-time counts and status
- **Recent Matches**: Latest user-product matches
- **Processing Status**: Upload and workflow status
- **Performance Metrics**: Response times and throughput

## 🐛 Troubleshooting

### Common Issues:

#### Issue: "Database connection failed"
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check if running
docker-compose ps
```

#### Issue: "AWS credentials invalid"
```bash
# Configure AWS credentials
aws configure

# Test credentials
aws sts get-caller-identity
```

#### Issue: "n8n not accessible"
```bash
# Start n8n
docker-compose up -d n8n

# Check logs
docker-compose logs n8n
```

#### Issue: "File upload failed"
```bash
# Check S3 bucket
aws s3 ls s3://loan-eligibility-engine-dev-uploads

# Check Lambda logs
aws logs tail /aws/lambda/loan-eligibility-engine-dev-upload-handler --follow
```

## 🎯 Success Criteria

Your application is working correctly if:

1. **✅ Web UI loads** without errors
2. **✅ File upload works** and shows progress
3. **✅ Database contains** users and products
4. **✅ API endpoints return** correct data
5. **✅ n8n workflows execute** successfully
6. **✅ Matches are generated** for users
7. **✅ Notifications are sent** (if email configured)
8. **✅ Monitoring shows** healthy system status

## 📈 Performance Testing

### Load Testing:
```bash
# Test API performance
ab -n 100 -c 10 "https://[api-id].execute-api.us-east-1.amazonaws.com/dev/health"

# Test file upload
ab -n 10 -c 2 -p users.csv -T "text/csv" "https://[api-id].execute-api.us-east-1.amazonaws.com/dev/upload"
```

### Expected Performance:
- **API Response**: < 200ms
- **File Upload**: < 30 seconds for 10MB
- **Database Queries**: < 100ms
- **Workflow Execution**: < 60 seconds

## 🚀 Next Steps

After successful testing:

1. **Configure production settings** in `.env`
2. **Set up monitoring alerts** in CloudWatch
3. **Configure email notifications** for production
4. **Set up backup strategies** for the database
5. **Implement additional security measures**
6. **Scale the system** based on usage patterns

## 📞 Support

If you encounter issues:

1. **Run the quick test**: `./quick_test.sh` or `quick_test.bat`
2. **Check the logs** using the monitoring tools
3. **Review TESTING_GUIDE.md** for detailed testing procedures
4. **Verify all prerequisites** are installed correctly
5. **Ensure environment variables** are properly configured

The system is designed to be robust and self-healing, but proper monitoring and testing will ensure optimal performance! 🎉 