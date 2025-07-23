import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.database = os.getenv('POSTGRES_DB', 'loan_engine')
        self.user = os.getenv('POSTGRES_USER', 'postgres')
        self.password = os.getenv('POSTGRES_PASSWORD', 'postgres123')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
                connect_timeout=10
            )
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    def initialize_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    monthly_income DECIMAL(12,2),
                    credit_score INTEGER,
                    employment_status VARCHAR(100),
                    age INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create loan_products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_products (
                    id SERIAL PRIMARY KEY,
                    product_name VARCHAR(255) NOT NULL,
                    provider VARCHAR(255) NOT NULL,
                    interest_rate DECIMAL(5,2),
                    min_income DECIMAL(12,2),
                    min_credit_score INTEGER,
                    max_credit_score INTEGER,
                    min_age INTEGER,
                    max_age INTEGER,
                    employment_required BOOLEAN DEFAULT FALSE,
                    max_amount DECIMAL(12,2),
                    min_amount DECIMAL(12,2),
                    tenure_months INTEGER,
                    url VARCHAR(500),
                    eligibility_criteria JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100) NOT NULL,
                    product_id INTEGER NOT NULL,
                    match_score DECIMAL(5,2),
                    match_reasons JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES loan_products(id),
                    UNIQUE(user_id, product_id)
                )
            """)
            
            # Create processing_logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id SERIAL PRIMARY KEY,
                    batch_id VARCHAR(100) NOT NULL,
                    operation VARCHAR(100) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    errors JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            logger.info("Database initialized successfully")

    def insert_users_batch(self, users_data: List[Dict[str, Any]]) -> int:
        """Insert multiple users with conflict resolution"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO users (user_id, email, monthly_income, credit_score, employment_status, age)
                VALUES (%(user_id)s, %(email)s, %(monthly_income)s, %(credit_score)s, %(employment_status)s, %(age)s)
                ON CONFLICT (user_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    monthly_income = EXCLUDED.monthly_income,
                    credit_score = EXCLUDED.credit_score,
                    employment_status = EXCLUDED.employment_status,
                    age = EXCLUDED.age,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.executemany(insert_query, users_data)
            return cursor.rowcount

    def insert_loan_products_batch(self, products_data: List[Dict[str, Any]]) -> int:
        """Insert multiple loan products with conflict resolution"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO loan_products (
                    product_name, provider, interest_rate, min_income, min_credit_score, 
                    max_credit_score, min_age, max_age, employment_required, max_amount, 
                    min_amount, tenure_months, url, eligibility_criteria
                ) VALUES (
                    %(product_name)s, %(provider)s, %(interest_rate)s, %(min_income)s, 
                    %(min_credit_score)s, %(max_credit_score)s, %(min_age)s, %(max_age)s, 
                    %(employment_required)s, %(max_amount)s, %(min_amount)s, %(tenure_months)s, 
                    %(url)s, %(eligibility_criteria)s
                ) ON CONFLICT (product_name, provider) DO UPDATE SET
                    interest_rate = EXCLUDED.interest_rate,
                    min_income = EXCLUDED.min_income,
                    min_credit_score = EXCLUDED.min_credit_score,
                    max_credit_score = EXCLUDED.max_credit_score,
                    min_age = EXCLUDED.min_age,
                    max_age = EXCLUDED.max_age,
                    employment_required = EXCLUDED.employment_required,
                    max_amount = EXCLUDED.max_amount,
                    min_amount = EXCLUDED.min_amount,
                    tenure_months = EXCLUDED.tenure_months,
                    url = EXCLUDED.url,
                    eligibility_criteria = EXCLUDED.eligibility_criteria,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.executemany(insert_query, products_data)
            return cursor.rowcount

    def get_users_for_matching(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get users that need matching"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT u.* FROM users u
                WHERE u.updated_at > COALESCE(
                    (SELECT MAX(created_at) FROM matches m WHERE m.user_id = u.user_id),
                    '1970-01-01'::timestamp
                )
                ORDER BY u.updated_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_loan_products(self) -> List[Dict[str, Any]]:
        """Get all loan products"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM loan_products ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def insert_matches_batch(self, matches_data: List[Dict[str, Any]]) -> int:
        """Insert multiple matches"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO matches (user_id, product_id, match_score, match_reasons)
                VALUES (%(user_id)s, %(product_id)s, %(match_score)s, %(match_reasons)s)
                ON CONFLICT (user_id, product_id) DO UPDATE SET
                    match_score = EXCLUDED.match_score,
                    match_reasons = EXCLUDED.match_reasons,
                    created_at = CURRENT_TIMESTAMP
            """
            
            cursor.executemany(insert_query, matches_data)
            return cursor.rowcount

    def get_user_matches(self, user_id: str) -> List[Dict[str, Any]]:
        """Get matches for a specific user"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT m.*, lp.product_name, lp.provider, lp.interest_rate, 
                       lp.min_amount, lp.max_amount, lp.tenure_months, lp.url
                FROM matches m
                JOIN loan_products lp ON m.product_id = lp.id
                WHERE m.user_id = %s
                ORDER BY m.match_score DESC
            """
            
            cursor.execute(query, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_users_with_new_matches(self, since_hours: int = 24) -> List[Dict[str, Any]]:
        """Get users with new matches for notification"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT DISTINCT u.user_id, u.email, u.monthly_income, u.credit_score,
                       COUNT(m.id) as match_count
                FROM users u
                JOIN matches m ON u.user_id = m.user_id
                WHERE m.created_at > NOW() - INTERVAL '%s hours'
                GROUP BY u.user_id, u.email, u.monthly_income, u.credit_score
                ORDER BY match_count DESC
            """
            
            cursor.execute(query, (since_hours,))
            return [dict(row) for row in cursor.fetchall()]

    def log_processing_operation(self, batch_id: str, operation: str, status: str, 
                               records_processed: int = 0, errors: Optional[Dict] = None):
        """Log processing operations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO processing_logs (batch_id, operation, status, records_processed, errors)
                VALUES (%s, %s, %s, %s, %s)
            """, (batch_id, operation, status, records_processed, json.dumps(errors) if errors else None))

    def get_processing_status(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get processing status for a batch"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM processing_logs
                WHERE batch_id = %s
                ORDER BY created_at DESC
            """, (batch_id,))
            
            return [dict(row) for row in cursor.fetchall()]

    def execute_optimized_matching_query(self, min_income: float, min_credit_score: int, 
                                       max_credit_score: int, age: int, employment_status: str) -> List[Dict[str, Any]]:
        """Execute optimized SQL query for pre-filtering loan products"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT * FROM loan_products 
                WHERE (min_income IS NULL OR min_income <= %s)
                AND (min_credit_score IS NULL OR min_credit_score <= %s)
                AND (max_credit_score IS NULL OR max_credit_score >= %s)
                AND (min_age IS NULL OR min_age <= %s)
                AND (max_age IS NULL OR max_age >= %s)
                AND (employment_required = FALSE OR %s IN ('employed', 'self-employed'))
                ORDER BY interest_rate ASC
            """
            
            cursor.execute(query, (min_income, min_credit_score, max_credit_score, age, age, employment_status))
            return [dict(row) for row in cursor.fetchall()]

    def get_users_paginated(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get users with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM users 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]

    def insert_user(self, user_data: Dict[str, Any]) -> str:
        """Insert a single user and return user_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO users (user_id, email, monthly_income, credit_score, employment_status, age)
                VALUES (%(user_id)s, %(email)s, %(monthly_income)s, %(credit_score)s, %(employment_status)s, %(age)s)
                ON CONFLICT (user_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    monthly_income = EXCLUDED.monthly_income,
                    credit_score = EXCLUDED.credit_score,
                    employment_status = EXCLUDED.employment_status,
                    age = EXCLUDED.age,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING user_id
            """
            
            cursor.execute(insert_query, user_data)
            return cursor.fetchone()[0]

    def get_users_by_ids(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        """Get users by their IDs"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            placeholders = ','.join(['%s'] * len(user_ids))
            query = f"""
                SELECT * FROM users 
                WHERE user_id IN ({placeholders})
            """
            
            cursor.execute(query, user_ids)
            return [dict(row) for row in cursor.fetchall()]

    def insert_match(self, match_data: Dict[str, Any]) -> int:
        """Insert a single match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO matches (user_id, product_id, match_score, match_reasons)
                VALUES (%(user_id)s, %(product_id)s, %(match_score)s, %(match_reasons)s)
                ON CONFLICT (user_id, product_id) DO UPDATE SET
                    match_score = EXCLUDED.match_score,
                    match_reasons = EXCLUDED.match_reasons,
                    created_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(insert_query, match_data)
            return cursor.rowcount

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            stats = {}
            
            # Total users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats['total_users'] = cursor.fetchone()['count']
            
            # Total products
            cursor.execute("SELECT COUNT(*) as count FROM loan_products")
            stats['total_products'] = cursor.fetchone()['count']
            
            # Total matches
            cursor.execute("SELECT COUNT(*) as count FROM matches")
            stats['total_matches'] = cursor.fetchone()['count']
            
            # Recent matches (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) as count FROM matches 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            stats['recent_matches'] = cursor.fetchone()['count']
            
            return stats

    def get_recent_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent matches for display"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT m.*, u.email, lp.product_name, lp.provider, lp.interest_rate
                FROM matches m
                JOIN users u ON m.user_id = u.user_id
                JOIN loan_products lp ON m.product_id = lp.id
                ORDER BY m.created_at DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]