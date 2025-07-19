-- Database schema for Loan Eligibility Engine
-- PostgreSQL database schema

-- Create database if not exists
-- CREATE DATABASE loan_engine;

-- Users table to store user data from CSV uploads
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    monthly_income DECIMAL(12,2),
    credit_score INTEGER CHECK (credit_score >= 300 AND credit_score <= 850),
    employment_status VARCHAR(100) CHECK (employment_status IN ('employed', 'unemployed', 'self-employed', 'student', 'retired')),
    age INTEGER CHECK (age >= 18 AND age <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Loan products table to store discovered loan products
CREATE TABLE IF NOT EXISTS loan_products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    interest_rate DECIMAL(5,2) CHECK (interest_rate >= 0),
    min_income DECIMAL(12,2) CHECK (min_income >= 0),
    min_credit_score INTEGER CHECK (min_credit_score >= 300 AND min_credit_score <= 850),
    max_credit_score INTEGER CHECK (max_credit_score >= 300 AND max_credit_score <= 850),
    min_age INTEGER CHECK (min_age >= 18),
    max_age INTEGER CHECK (max_age <= 100),
    employment_required BOOLEAN DEFAULT FALSE,
    max_amount DECIMAL(12,2),
    min_amount DECIMAL(12,2),
    tenure_months INTEGER,
    url VARCHAR(500),
    eligibility_criteria JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_name, provider)
);

-- Matches table to store user-loan product matches
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id INTEGER NOT NULL,
    match_score DECIMAL(5,2) CHECK (match_score >= 0 AND match_score <= 100),
    match_reasons JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES loan_products(id) ON DELETE CASCADE,
    UNIQUE(user_id, product_id)
);

-- Processing logs table to track batch processing status
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('started', 'in_progress', 'completed', 'failed')),
    records_processed INTEGER DEFAULT 0,
    errors JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email notifications table to track sent notifications
CREATE TABLE IF NOT EXISTS email_notifications (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    body TEXT,
    status VARCHAR(50) DEFAULT 'sent' CHECK (status IN ('pending', 'sent', 'failed')),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    match_count INTEGER DEFAULT 0
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_credit_score ON users(credit_score);
CREATE INDEX IF NOT EXISTS idx_users_income ON users(monthly_income);
CREATE INDEX IF NOT EXISTS idx_users_age ON users(age);
CREATE INDEX IF NOT EXISTS idx_users_employment ON users(employment_status);

CREATE INDEX IF NOT EXISTS idx_loan_products_provider ON loan_products(provider);
CREATE INDEX IF NOT EXISTS idx_loan_products_interest_rate ON loan_products(interest_rate);
CREATE INDEX IF NOT EXISTS idx_loan_products_min_income ON loan_products(min_income);
CREATE INDEX IF NOT EXISTS idx_loan_products_min_credit ON loan_products(min_credit_score);

CREATE INDEX IF NOT EXISTS idx_matches_user_id ON matches(user_id);
CREATE INDEX IF NOT EXISTS idx_matches_product_id ON matches(product_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_created_at ON matches(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_logs_batch_id ON processing_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_operation ON processing_logs(operation);

CREATE INDEX IF NOT EXISTS idx_email_notifications_user_id ON email_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_email_notifications_status ON email_notifications(status);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_loan_products_updated_at BEFORE UPDATE ON loan_products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample loan products for testing
INSERT INTO loan_products (
    product_name, provider, interest_rate, min_income, min_credit_score, 
    max_credit_score, min_age, max_age, employment_required, max_amount, 
    min_amount, tenure_months, url, eligibility_criteria
) VALUES 
(
    'Personal Loan Plus', 'BankABC', 8.99, 30000, 650, 850, 21, 65, true, 100000, 5000, 60,
    'https://bankabc.com/personal-loan-plus',
    '{"features": ["Quick approval", "No prepayment penalty"], "documents_required": ["Salary slips", "Bank statements"]}'
),
(
    'Quick Cash Loan', 'FastCredit', 12.50, 25000, 600, 800, 18, 60, true, 50000, 2000, 36,
    'https://fastcredit.com/quick-cash',
    '{"features": ["Same day approval", "Flexible repayment"], "documents_required": ["ID proof", "Income proof"]}'
),
(
    'Premium Personal Loan', 'EliteBank', 6.75, 50000, 700, 850, 25, 60, true, 500000, 10000, 84,
    'https://elitebank.com/premium-personal',
    '{"features": ["Lowest rates", "Premium service"], "documents_required": ["ITR", "Bank statements", "Employment letter"]}'
),
(
    'Student Friendly Loan', 'YoungBank', 15.00, 15000, 300, 650, 18, 30, false, 25000, 1000, 24,
    'https://youngbank.com/student-loan',
    '{"features": ["No employment required", "Student friendly"], "documents_required": ["ID proof", "Student ID"]}'
)
ON CONFLICT (product_name, provider) DO NOTHING;

-- Create a view for easy querying of user matches with product details
CREATE OR REPLACE VIEW user_matches_view AS
SELECT 
    u.user_id,
    u.email,
    u.monthly_income,
    u.credit_score,
    u.employment_status,
    u.age,
    lp.product_name,
    lp.provider,
    lp.interest_rate,
    lp.min_amount,
    lp.max_amount,
    lp.tenure_months,
    lp.url,
    m.match_score,
    m.match_reasons,
    m.created_at as matched_at
FROM users u
JOIN matches m ON u.user_id = m.user_id
JOIN loan_products lp ON m.product_id = lp.id
ORDER BY m.match_score DESC;

-- Create a view for processing status
CREATE OR REPLACE VIEW processing_status_view AS
SELECT 
    batch_id,
    operation,
    status,
    records_processed,
    errors,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY batch_id, operation ORDER BY created_at DESC) as rn
FROM processing_logs;

