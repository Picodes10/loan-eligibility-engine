#!/usr/bin/env python3
"""
Database Setup Script for Loan Eligibility Engine
This script initializes the PostgreSQL database with required tables and sample data.
"""

import os
import sys
import psycopg2
import logging
from datetime import datetime
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self):
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.database = os.getenv('POSTGRES_DB', 'loan_engine')
        self.user = os.getenv('POSTGRES_USER', 'postgres')
        self.password = os.getenv('POSTGRES_PASSWORD', 'postgres123')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        
    def get_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                connect_timeout=10
            )
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def create_database(self):
        """Create database if it doesn't exist"""
        try:
            # Connect to default postgres database
            conn = psycopg2.connect(
                host=self.host,
                database='postgres',
                user=self.user,
                password=self.password,
                port=self.port,
                connect_timeout=10
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database,))
            exists = cursor.fetchone()
            
            if not exists:
                logger.info(f"Creating database: {self.database}")
                cursor.execute(f"CREATE DATABASE {self.database}")
                logger.info("Database created successfully")
            else:
                logger.info(f"Database {self.database} already exists")
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_tables(self):
        """Create all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logger.info("Creating database tables...")
            
            # Read schema from file
            schema_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'db_schema.sql')
            
            if os.path.exists(schema_file):
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()
                
                # Split and execute SQL statements
                statements = schema_sql.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        cursor.execute(statement)
                
                conn.commit()
                logger.info("Database tables created successfully")
            else:
                logger.warning("Schema file not found, creating basic tables...")
                self.create_basic_tables(cursor)
                conn.commit()
                
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Failed to create tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def create_basic_tables(self, cursor):
        """Create basic tables if schema file is not available"""
        
        # Users table
        cursor.execute("""
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
            )
        """)
        
        # Loan products table
        cursor.execute("""
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
            )
        """)
        
        # Matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                product_id INTEGER NOT NULL,
                match_score DECIMAL(5,2) CHECK (match_score >= 0 AND match_score <= 100),
                match_reasons JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES loan_products(id) ON DELETE CASCADE,
                UNIQUE(user_id, product_id)
            )
        """)
        
        # Processing logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_logs (
                id SERIAL PRIMARY KEY,
                batch_id VARCHAR(100) NOT NULL,
                operation VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL CHECK (status IN ('started', 'in_progress', 'completed', 'failed')),
                records_processed INTEGER DEFAULT 0,
                errors JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Email notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject VARCHAR(500),
                body TEXT,
                status VARCHAR(50) DEFAULT 'sent' CHECK (status IN ('pending', 'sent', 'failed')),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                match_count INTEGER DEFAULT 0
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
            CREATE INDEX IF NOT EXISTS idx_users_credit_score ON users(credit_score);
            CREATE INDEX IF NOT EXISTS idx_users_income ON users(monthly_income);
            CREATE INDEX IF NOT EXISTS idx_loan_products_provider ON loan_products(provider);
            CREATE INDEX IF NOT EXISTS idx_matches_user_id ON matches(user_id);
            CREATE INDEX IF NOT EXISTS idx_matches_product_id ON matches(product_id);
            CREATE INDEX IF NOT EXISTS idx_processing_logs_batch_id ON processing_logs(batch_id);
        """)
        
        logger.info("Basic tables created successfully")
    
    def insert_sample_data(self):
        """Insert sample loan products and users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logger.info("Inserting sample data...")
            
            # Sample loan products
            sample_products = [
                {
                    'product_name': 'Personal Loan Plus',
                    'provider': 'BankABC',
                    'interest_rate': 8.99,
                    'min_income': 30000,
                    'min_credit_score': 650,
                    'max_credit_score': 850,
                    'min_age': 21,
                    'max_age': 65,
                    'employment_required': True,
                    'max_amount': 100000,
                    'min_amount': 5000,
                    'tenure_months': 60,
                    'url': 'https://bankabc.com/personal-loan-plus',
                    'eligibility_criteria': json.dumps({
                        'features': ['Quick approval', 'No prepayment penalty'],
                        'documents_required': ['Salary slips', 'Bank statements']
                    })
                },
                {
                    'product_name': 'Quick Cash Loan',
                    'provider': 'FastCredit',
                    'interest_rate': 12.50,
                    'min_income': 25000,
                    'min_credit_score': 600,
                    'max_credit_score': 800,
                    'min_age': 18,
                    'max_age': 60,
                    'employment_required': True,
                    'max_amount': 50000,
                    'min_amount': 2000,
                    'tenure_months': 36,
                    'url': 'https://fastcredit.com/quick-cash',
                    'eligibility_criteria': json.dumps({
                        'features': ['Same day approval', 'Flexible repayment'],
                        'documents_required': ['ID proof', 'Income proof']
                    })
                },
                {
                    'product_name': 'Premium Personal Loan',
                    'provider': 'EliteBank',
                    'interest_rate': 6.75,
                    'min_income': 50000,
                    'min_credit_score': 700,
                    'max_credit_score': 850,
                    'min_age': 25,
                    'max_age': 60,
                    'employment_required': True,
                    'max_amount': 500000,
                    'min_amount': 10000,
                    'tenure_months': 84,
                    'url': 'https://elitebank.com/premium-personal',
                    'eligibility_criteria': json.dumps({
                        'features': ['Lowest rates', 'Premium service'],
                        'documents_required': ['ITR', 'Bank statements', 'Employment letter']
                    })
                },
                {
                    'product_name': 'Student Friendly Loan',
                    'provider': 'YoungBank',
                    'interest_rate': 15.00,
                    'min_income': 15000,
                    'min_credit_score': 300,
                    'max_credit_score': 650,
                    'min_age': 18,
                    'max_age': 30,
                    'employment_required': False,
                    'max_amount': 25000,
                    'min_amount': 1000,
                    'tenure_months': 24,
                    'url': 'https://youngbank.com/student-loan',
                    'eligibility_criteria': json.dumps({
                        'features': ['No employment required', 'Student friendly'],
                        'documents_required': ['ID proof', 'Student ID']
                    })
                }
            ]
            
            # Insert sample products
            for product in sample_products:
                cursor.execute("""
                    INSERT INTO loan_products (
                        product_name, provider, interest_rate, min_income, min_credit_score,
                        max_credit_score, min_age, max_age, employment_required, max_amount,
                        min_amount, tenure_months, url, eligibility_criteria
                    ) VALUES (
                        %(product_name)s, %(provider)s, %(interest_rate)s, %(min_income)s,
                        %(min_credit_score)s, %(max_credit_score)s, %(min_age)s, %(max_age)s,
                        %(employment_required)s, %(max_amount)s, %(min_amount)s, %(tenure_months)s,
                        %(url)s, %(eligibility_criteria)s
                    ) ON CONFLICT (product_name, provider) DO NOTHING
                """, product)
            
            # Sample users
            sample_users = [
                {
                    'user_id': 'user_001',
                    'email': 'john.doe@example.com',
                    'monthly_income': 75000,
                    'credit_score': 780,
                    'employment_status': 'employed',
                    'age': 32
                },
                {
                    'user_id': 'user_002',
                    'email': 'jane.smith@example.com',
                    'monthly_income': 45000,
                    'credit_score': 720,
                    'employment_status': 'employed',
                    'age': 28
                },
                {
                    'user_id': 'user_003',
                    'email': 'mike.johnson@example.com',
                    'monthly_income': 35000,
                    'credit_score': 650,
                    'employment_status': 'self-employed',
                    'age': 35
                },
                {
                    'user_id': 'user_004',
                    'email': 'sarah.wilson@example.com',
                    'monthly_income': 25000,
                    'credit_score': 580,
                    'employment_status': 'student',
                    'age': 22
                }
            ]
            
            # Insert sample users
            for user in sample_users:
                cursor.execute("""
                    INSERT INTO users (user_id, email, monthly_income, credit_score, employment_status, age)
                    VALUES (%(user_id)s, %(email)s, %(monthly_income)s, %(credit_score)s, %(employment_status)s, %(age)s)
                    ON CONFLICT (user_id) DO NOTHING
                """, user)
            
            conn.commit()
            logger.info("Sample data inserted successfully")
            
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Failed to insert sample data: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def create_views(self):
        """Create useful database views"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logger.info("Creating database views...")
            
            # User matches view
            cursor.execute("""
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
                ORDER BY m.match_score DESC
            """)
            
            # Processing status view
            cursor.execute("""
                CREATE OR REPLACE VIEW processing_status_view AS
                SELECT 
                    batch_id,
                    operation,
                    status,
                    records_processed,
                    errors,
                    created_at,
                    ROW_NUMBER() OVER (PARTITION BY batch_id, operation ORDER BY created_at DESC) as rn
                FROM processing_logs
            """)
            
            conn.commit()
            logger.info("Database views created successfully")
            
        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"Failed to create views: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def verify_setup(self):
        """Verify that the database setup is correct"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            logger.info("Verifying database setup...")
            
            # Check tables exist
            tables = ['users', 'loan_products', 'matches', 'processing_logs', 'email_notifications']
            for table in tables:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (table,))
                exists = cursor.fetchone()[0]
                if exists:
                    logger.info(f"✅ Table '{table}' exists")
                else:
                    logger.error(f"❌ Table '{table}' does not exist")
                    return False
            
            # Check sample data
            cursor.execute("SELECT COUNT(*) FROM loan_products")
            product_count = cursor.fetchone()[0]
            logger.info(f"✅ Found {product_count} loan products")
            
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            logger.info(f"✅ Found {user_count} users")
            
            # Check views
            views = ['user_matches_view', 'processing_status_view']
            for view in views:
                cursor.execute("SELECT EXISTS (SELECT FROM information_schema.views WHERE table_name = %s)", (view,))
                exists = cursor.fetchone()[0]
                if exists:
                    logger.info(f"✅ View '{view}' exists")
                else:
                    logger.error(f"❌ View '{view}' does not exist")
                    return False
            
            logger.info("✅ Database setup verification completed successfully")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Failed to verify setup: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def run_setup(self):
        """Run the complete database setup"""
        try:
            logger.info("Starting database setup...")
            
            # Create database
            self.create_database()
            
            # Create tables
            self.create_tables()
            
            # Insert sample data
            self.insert_sample_data()
            
            # Create views
            self.create_views()
            
            # Verify setup
            if self.verify_setup():
                logger.info("🎉 Database setup completed successfully!")
                return True
            else:
                logger.error("❌ Database setup verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            return False

def main():
    """Main function"""
    print("🚀 Loan Eligibility Engine - Database Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        sys.exit(1)
    
    # Run setup
    setup = DatabaseSetup()
    success = setup.run_setup()
    
    if success:
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the n8n workflows")
        print("2. Upload your first CSV file")
        print("3. Monitor the system through the web UI")
    else:
        print("\n❌ Database setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
