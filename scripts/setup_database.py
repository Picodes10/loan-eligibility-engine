#!/usr/bin/env python3
"""
Database Setup Script for Loan Matching System
Creates tables and initial data
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from models.database import create_tables, drop_tables, get_database_session, LoanProduct
from datetime import datetime

def setup_database():
    """Create all database tables"""
    print("🗄️  Setting up database...")
    
    try:
        # Create all tables
        create_tables()
        print("✅ Database tables created successfully!")
        
        # Add sample loan products
        add_sample_loan_products()
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

def add_sample_loan_products():
    """Add sample loan products for testing"""
    print("📊 Adding sample loan products...")
    
    session = get_database_session()
    
    sample_products = [
        {
            'product_name': 'SoFi Personal Loan',
            'lender_name': 'SoFi',
            'interest_rate_min': 8.99,
            'interest_rate_max': 23.43,
            'min_loan_amount': 5000,
            'max_loan_amount': 100000,
            'min_credit_score': 680,
            'max_credit_score': 850,
            'min_income_required': 45000,
            'employment_requirements': 'Stable employment required',
            'age_min': 18,
            'age_max': 80,
            'product_url': 'https://www.sofi.com/personal-loans/',
            'terms_and_conditions': 'No fees, flexible terms'
        },
        {
            'product_name': 'Marcus Personal Loan',
            'lender_name': 'Marcus by Goldman Sachs',
            'interest_rate_min': 7.99,
            'interest_rate_max': 19.99,
            'min_loan_amount': 3500,
            'max_loan_amount': 40000,
            'min_credit_score': 660,
            'max_credit_score': 850,
            'min_income_required': 35000,
            'employment_requirements': 'Steady income required',
            'age_min': 18,
            'age_max': 75,
            'product_url': 'https://www.marcus.com/personal-loans',
            'terms_and_conditions': 'No fees, fixed rates'
        },
        {
            'product_name': 'LightStream Personal Loan',
            'lender_name': 'LightStream',
            'interest_rate_min': 7.49,
            'interest_rate_max': 25.49,
            'min_loan_amount': 5000,
            'max_loan_amount': 100000,
            'min_credit_score': 700,
            'max_credit_score': 850,
            'min_income_required': 50000,
            'employment_requirements': 'Excellent credit and income',
            'age_min': 18,
            'age_max': 80,
            'product_url': 'https://www.lightstream.com/personal-loans',
            'terms_and_conditions': 'Rate beat program available'
        },
        {
            'product_name': 'Discover Personal Loan',
            'lender_name': 'Discover Bank',
            'interest_rate_min': 6.99,
            'interest_rate_max': 24.99,
            'min_loan_amount': 2500,
            'max_loan_amount': 35000,
            'min_credit_score': 620,
            'max_credit_score': 850,
            'min_income_required': 25000,
            'employment_requirements': 'Regular income required',
            'age_min': 18,
            'age_max': 75,
            'product_url': 'https://www.discover.com/personal-loans/',
            'terms_and_conditions': 'No origination fees'
        },
        {
            'product_name': 'Upstart Personal Loan',
            'lender_name': 'Upstart',
            'interest_rate_min': 6.50,
            'interest_rate_max': 35.99,
            'min_loan_amount': 1000,
            'max_loan_amount': 50000,
            'min_credit_score': 580,
            'max_credit_score': 850,
            'min_income_required': 20000,
            'employment_requirements': 'Employment or regular income',
            'age_min': 18,
            'age_max': 80,
            'product_url': 'https://www.upstart.com/personal-loans',
            'terms_and_conditions': 'AI-powered underwriting'
        }
    ]
    
    try:
        for product_data in sample_products:
            # Check if product already exists
            existing = session.query(LoanProduct).filter_by(
                product_name=product_data['product_name'],
                lender_name=product_data['lender_name']
            ).first()
            
            if not existing:
                loan_product = LoanProduct(**product_data)
                session.add(loan_product)
        
        session.commit()
        print(f"✅ Added {len(sample_products)} sample loan products!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding sample products: {e}")
    finally:
        session.close()

def reset_database():
    """Drop and recreate all tables (WARNING: This will delete all data!)"""
    print("⚠️  WARNING: This will delete all existing data!")
    confirm = input("Are you sure you want to reset the database? (yes/no): ")
    
    if confirm.lower() == 'yes':
        print("🗑️  Dropping existing tables...")
        drop_tables()
        print("✅ Tables dropped!")
        
        setup_database()
    else:
        print("❌ Database reset cancelled.")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database setup for Loan Matching System')
    parser.add_argument('--reset', action='store_true', help='Reset database (WARNING: Deletes all data)')
    
    args = parser.parse_args()
    
    if args.reset:
        reset_database()
    else:
        setup_database()
