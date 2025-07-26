from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    monthly_income = Column(Float, nullable=False)
    credit_score = Column(Integer, nullable=False)
    employment_status = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    
    # Relationships
    matches = relationship("UserLoanMatch", back_populates="user")

class LoanProduct(Base):
    __tablename__ = 'loan_products'
    
    id = Column(Integer, primary_key=True)
    product_name = Column(String(255), nullable=False)
    lender_name = Column(String(255), nullable=False)
    interest_rate_min = Column(Float, nullable=False)
    interest_rate_max = Column(Float, nullable=True)
    min_loan_amount = Column(Float, nullable=True)
    max_loan_amount = Column(Float, nullable=True)
    min_income_required = Column(Float, nullable=True)
    min_credit_score = Column(Integer, nullable=True)
    max_credit_score = Column(Integer, nullable=True)
    employment_requirements = Column(Text, nullable=True)
    age_min = Column(Integer, nullable=True)
    age_max = Column(Integer, nullable=True)
    product_url = Column(String(500), nullable=True)
    terms_and_conditions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    matches = relationship("UserLoanMatch", back_populates="loan_product")

class UserLoanMatch(Base):
    __tablename__ = 'user_loan_matches'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    loan_product_id = Column(Integer, ForeignKey('loan_products.id'), nullable=False)
    match_score = Column(Float, nullable=True)  # AI-generated match confidence
    eligibility_status = Column(String(50), nullable=False)  # 'eligible', 'likely_eligible', 'needs_review'
    match_reasons = Column(Text, nullable=True)  # JSON string of matching criteria
    created_at = Column(DateTime, default=datetime.utcnow)
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="matches")
    loan_product = relationship("LoanProduct", back_populates="matches")

class ProcessingLog(Base):
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True)
    process_type = Column(String(100), nullable=False)  # 'csv_upload', 'loan_discovery', 'matching', 'notification'
    status = Column(String(50), nullable=False)  # 'started', 'completed', 'failed'
    details = Column(Text, nullable=True)
    records_processed = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

# Database connection and session management
def get_database_url():
    """Get database URL based on configuration"""
    db_host = os.getenv('DB_HOST', 'localhost')
    
    if db_host == 'sqlite':
        # SQLite configuration
        db_name = os.getenv('DB_NAME', 'loan_eligibility.db')
        return f'sqlite:///{db_name}'
    else:
        # PostgreSQL configuration
        db_name = os.getenv('DB_NAME', 'loan_eligibility_db')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        db_port = os.getenv('DB_PORT', '5432')
        
        return f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

# Create engine with appropriate configuration
DATABASE_URL = get_database_url()
if 'sqlite' in DATABASE_URL:
    engine = create_engine(DATABASE_URL, echo=False)
else:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_database_session():
    return SessionLocal()

def create_tables():
    Base.metadata.create_all(bind=engine)

def drop_tables():
    Base.metadata.drop_all(bind=engine)
