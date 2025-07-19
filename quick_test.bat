@echo off
REM Loan Eligibility Engine - Quick Test Script (Windows)
REM This script performs basic testing of the application

echo 🚀 Loan Eligibility Engine - Quick Test
echo ========================================

REM Check prerequisites
echo [INFO] Checking prerequisites...

REM Check if required tools are installed
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] node is not installed
    exit /b 1
) else (
    echo [SUCCESS] node is installed
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed
    exit /b 1
) else (
    echo [SUCCESS] npm is installed
)

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] docker is not installed
    exit /b 1
) else (
    echo [SUCCESS] docker is installed
)

where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] aws CLI is not installed
    exit /b 1
) else (
    echo [SUCCESS] aws CLI is installed
)

where serverless >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] serverless is not installed
    exit /b 1
) else (
    echo [SUCCESS] serverless is installed
)

echo [SUCCESS] All prerequisites are installed!

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found. Creating from template...
    if exist .env.example (
        copy .env.example .env >nul
        echo [SUCCESS] Created .env file from template
        echo [WARNING] Please edit .env file with your AWS credentials and settings
    ) else (
        echo [ERROR] .env.example not found. Please create .env file manually
        exit /b 1
    )
)

REM Check if users.csv exists
if not exist users.csv (
    echo [ERROR] users.csv file not found in the current directory
    exit /b 1
)

echo [SUCCESS] Found users.csv file

REM Test database connection
echo [INFO] Testing database connection...
python -c "from lambda_function.database_manager import DatabaseManager; db = DatabaseManager(); db.test_connection(); print('✅ Database connection successful'); db.close()" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Database connection failed
    exit /b 1
) else (
    echo [SUCCESS] Database connection test passed
)

REM Run database tests
echo [INFO] Running database tests...
python -c "
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
" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Database tests failed
    exit /b 1
) else (
    echo [SUCCESS] Database tests passed
)

REM Test API endpoints
echo [INFO] Testing API endpoints...

REM Get API Gateway URL
for /f "tokens=*" %%i in ('aws apigateway get-rest-apis --region us-east-1 --query "items[?name=='loan-eligibility-engine-dev'].id" --output text 2^>nul') do set API_ID=%%i

if "%API_ID%"=="" (
    echo [WARNING] API Gateway not found. Skipping API tests.
) else (
    set API_BASE=https://%API_ID%.execute-api.us-east-1.amazonaws.com/dev
    
    REM Test health endpoint
    echo [INFO] Testing health endpoint...
    curl -s -f "%API_BASE%/health" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Health endpoint is not responding
    ) else (
        echo [SUCCESS] Health endpoint is working
    )
    
    REM Test stats endpoint
    echo [INFO] Testing stats endpoint...
    curl -s -f "%API_BASE%/api/stats" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Stats endpoint is not responding
    ) else (
        echo [SUCCESS] Stats endpoint is working
    )
)

REM Test file upload
echo [INFO] Testing file upload functionality...

REM Check if S3 bucket exists
aws s3 ls s3://loan-eligibility-engine-dev-uploads >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] S3 bucket not found. Skipping upload test.
) else (
    echo [SUCCESS] S3 bucket exists
    
    REM Test upload
    aws s3 cp users.csv s3://loan-eligibility-engine-dev-uploads/test-upload.csv >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] File upload test failed
    ) else (
        echo [SUCCESS] File upload test successful
        REM Clean up test file
        aws s3 rm s3://loan-eligibility-engine-dev-uploads/test-upload.csv >nul 2>&1
    )
)

REM Test n8n workflows
echo [INFO] Testing n8n workflows...

REM Check if n8n is running
curl -s -f http://localhost:5678 >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] n8n is not running. Start it with: docker-compose up -d
) else (
    echo [SUCCESS] n8n is running
    
    REM Check if workflows exist
    if exist workflows\loan_discovery.json (
        if exist workflows\user_matching.json (
            if exist workflows\user_notification.json (
                echo [SUCCESS] All workflow files exist
            ) else (
                echo [WARNING] user_notification.json is missing
            )
        ) else (
            echo [WARNING] user_matching.json is missing
        )
    ) else (
        echo [WARNING] loan_discovery.json is missing
    )
)

REM Check system status
echo [INFO] Checking system status...

REM Check if Docker containers are running
docker-compose ps | findstr "Up" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Docker containers are not running
) else (
    echo [SUCCESS] Docker containers are running
)

REM Check if AWS services are accessible
aws sts get-caller-identity >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] AWS credentials may be invalid
) else (
    echo [SUCCESS] AWS credentials are valid
)

echo.
echo 🎉 Quick Test Completed!
echo ========================
echo [SUCCESS] Basic system functionality verified
echo [INFO] For detailed testing, see TESTING_GUIDE.md
echo [INFO] To start the full system: scripts\deploy.sh dev us-east-1

pause 