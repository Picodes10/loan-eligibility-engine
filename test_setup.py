#!/usr/bin/env python3
"""
Quick test script to verify database setup
"""

import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def test_environment():
    """Test if environment variables are loaded correctly"""
    print("🔍 Testing Environment Variables:")
    print("=" * 40)
    
    env_vars = ['POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_PORT']
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Hide password for security
            display_value = "***" if "PASSWORD" in var else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
    
    print()

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing Database Connection:")
    print("=" * 40)
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            database=os.getenv('POSTGRES_DB', 'loan_engine'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres123'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful!")
        print(f"✅ PostgreSQL version: {version}")
        
        # Test if loan_engine database exists
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"✅ Connected to database: {current_db}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def main():
    print("🚀 Loan Eligibility Engine - Setup Test")
    print("=" * 50)
    print()
    
    test_environment()
    
    if test_database_connection():
        print()
        print("🎉 All tests passed! You can now run:")
        print("   python scripts/setup_database.py")
        print("   python app.py")
    else:
        print()
        print("❌ Database connection failed. Please:")
        print("   1. Make sure Docker is running")
        print("   2. Run: docker-compose up -d")
        print("   3. Wait 30 seconds for PostgreSQL to start")
        print("   4. Try again")

if __name__ == "__main__":
    main()