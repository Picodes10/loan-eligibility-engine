# Automated Loan Matching System

A comprehensive system that ingests user data, discovers personal loan products from public websites, matches users to eligible products, and notifies them via email.

## Architecture Overview

- **Backend**: Python with AWS Lambda
- **Database**: Amazon RDS PostgreSQL
- **Workflow Engine**: Self-hosted n8n via Docker
- **AI Integration**: Google Gemini API for advanced matching
- **Email Service**: AWS SES
- **Deployment**: Serverless Framework + Docker Compose

## Components

### 1. AWS Infrastructure
- **Lambda Functions**: CSV processing, data ingestion
- **RDS PostgreSQL**: User data, loan products, matches storage
- **S3**: CSV file storage and event triggers
- **SES**: Email notifications

### 2. n8n Workflows
- **Workflow A**: Loan Product Discovery (scheduled web crawler)
- **Workflow B**: User-Loan Matching (webhook-triggered)
- **Workflow C**: User Notification (email automation)

### 3. Web Interface
- Minimal UI for CSV upload
- Triggers the entire processing pipeline

## Setup Instructions

1. **Prerequisites**
   ```bash
   npm install -g serverless
   pip install -r requirements.txt
   ```

2. **AWS Setup**
   - Configure AWS credentials
   - Deploy infrastructure: `serverless deploy`

3. **n8n Setup**
   ```bash
   docker-compose up -d
   ```

4. **Database Setup**
   - Run migration scripts to create tables

5. **Environment Configuration**
   - Set up environment variables for API keys and database connections

## Usage

1. Upload CSV file through the web interface
2. System automatically processes users and matches them with loan products
3. Users receive personalized email notifications

## Optimization Features

- Multi-stage filtering pipeline for efficient matching
- SQL-based pre-filtering before AI evaluation
- Event-driven architecture for scalability
- Cost-optimized AI usage patterns
