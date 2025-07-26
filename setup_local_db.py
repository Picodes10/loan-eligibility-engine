#!/usr/bin/env python3
"""
Local Database Setup Script
Sets up a local PostgreSQL database using Docker for development/testing
"""

import subprocess
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_command(command, shell=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_docker():
    """Check if Docker is installed and running"""
    print("🐳 Checking Docker...")
    success, stdout, stderr = run_command("docker --version")
    
    if not success:
        print("❌ Docker is not installed or not in PATH")
        print("Please install Docker Desktop from: https://www.docker.com/products/docker-desktop")
        return False
    
    print(f"✅ Docker found: {stdout.strip()}")
    
    # Check if Docker daemon is running
    success, stdout, stderr = run_command("docker ps")
    if not success:
        print("❌ Docker daemon is not running")
        print("Please start Docker Desktop")
        return False
    
    print("✅ Docker daemon is running")
    return True

def setup_local_postgres():
    """Set up local PostgreSQL container"""
    print("\n🗄️  Setting up local PostgreSQL...")
    
    # Stop and remove existing container if it exists
    print("Cleaning up existing container...")
    run_command("docker stop postgres-local")
    run_command("docker rm postgres-local")
    
    # Start new PostgreSQL container
    db_password = os.getenv('DB_PASSWORD', 'jazzu2024')
    db_name = os.getenv('DB_NAME', 'loan_eligibility_db')
    
    command = f"""docker run --name postgres-local \
        -e POSTGRES_PASSWORD={db_password} \
        -e POSTGRES_DB={db_name} \
        -p 5432:5432 \
        -d postgres:13"""
    
    print("Starting PostgreSQL container...")
    success, stdout, stderr = run_command(command)
    
    if not success:
        print(f"❌ Failed to start PostgreSQL container: {stderr}")
        return False
    
    print("✅ PostgreSQL container started")
    
    # Wait for PostgreSQL to be ready
    print("Waiting for PostgreSQL to be ready...")
    for i in range(30):
        success, stdout, stderr = run_command(
            f"docker exec postgres-local pg_isready -U postgres"
        )
        if success:
            print("✅ PostgreSQL is ready!")
            break
        time.sleep(1)
        print(f"⏳ Waiting... ({i+1}/30)")
    else:
        print("❌ PostgreSQL failed to start within 30 seconds")
        return False
    
    return True

def update_env_file():
    """Update .env file to use local database"""
    print("\n📝 Updating .env file for local database...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Read current content
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Update DB_HOST to localhost
    content = content.replace(
        'DB_HOST=loan-eligibility-db.cluster-c9qmykwogxuf.ap-south-1.rds.amazonaws.com',
        'DB_HOST=localhost'
    )
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ .env file updated to use localhost")
    return True

def test_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    # Add src to path
    sys.path.append(str(Path(__file__).parent / 'src'))
    
    try:
        from models.database import get_database_session
        from sqlalchemy import text
        
        session = get_database_session()
        result = session.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()[0]
        session.close()
        
        if test_value == 1:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection test failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    print("🚀 Local Database Setup")
    print("=" * 40)
    
    # Check Docker
    if not check_docker():
        return False
    
    # Setup PostgreSQL
    if not setup_local_postgres():
        return False
    
    # Update .env file
    if not update_env_file():
        return False
    
    # Test connection
    if not test_connection():
        return False
    
    print("\n🎉 Local database setup complete!")
    print("\nNext steps:")
    print("1. Run: python scripts/setup_database.py")
    print("2. Run: docker-compose up -d (to start n8n)")
    print("3. Run: python api_server.py")
    
    return True

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)
