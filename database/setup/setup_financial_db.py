#!/usr/bin/env python3
"""
Financial Services Database Setup Script
Creates PostgreSQL database with comprehensive financial data for RAG testing
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

def create_database():
    """Create the financial services database"""
    # Load .env from project root
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    db_name = os.getenv('DB_NAME', 'financial_services_db')
    
    print(f"🔧 Setting up financial services database: {db_name}")
    print(f"📍 Connecting to PostgreSQL at {db_params['host']}:{db_params['port']}")
    
    try:
        # Connect to PostgreSQL (without database)
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if cursor.fetchone():
            print(f"📋 Database '{db_name}' already exists")
            
            # Ask user if they want to recreate
            response = input("🔄 Recreate database? This will delete all existing data (y/N): ").lower()
            if response == 'y':
                print(f"🗑️ Dropping existing database '{db_name}'...")
                cursor.execute(f'DROP DATABASE "{db_name}"')
                print(f"✅ Database '{db_name}' dropped")
            else:
                print("ℹ️ Using existing database")
                cursor.close()
                conn.close()
                return db_name
        
        # Create database
        print(f"🔨 Creating database '{db_name}'...")
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        print(f"✅ Database '{db_name}' created successfully")
        
        cursor.close()
        conn.close()
        
        return db_name
        
    except psycopg2.Error as e:
        print(f"❌ Database creation failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def setup_schema_and_data(db_name):
    """Execute the SQL setup script"""
    # Load .env from project root
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': db_name
    }
    
    # Get path to SQL file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(script_dir, '..', 'schemas', 'financial_db_setup.sql')
    
    try:
        print(f"📊 Executing schema and data setup from {sql_file}...")
        
        # Read SQL file
        with open(sql_file, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Connect to the new database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Execute SQL content
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Schema and data setup completed successfully!")

        # Get table counts for verification (using information_schema for compatibility)
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print("\n📋 Created tables:")
        for (table_name,) in tables:
            # Get row count for each table
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cursor.fetchone()[0]
            print(f"  📄 {table_name}: {count} records")
        
        cursor.close()
        conn.close()
        
        return True
        
    except FileNotFoundError:
        print(f"❌ SQL file '{sql_file}' not found in current directory")
        return False
    except psycopg2.Error as e:
        print(f"❌ SQL execution failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def verify_setup(db_name):
    """Verify the database setup"""
    # Load .env from project root
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    env_path = os.path.join(project_root, '.env')
    load_dotenv(env_path)
    
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': db_name
    }
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        print("\n🔍 Database verification:")
        
        # Test some complex queries
        test_queries = [
            ("Total customers", "SELECT COUNT(*) FROM customers WHERE is_active = true"),
            ("Active accounts", "SELECT COUNT(*) FROM accounts WHERE account_status = 'active'"), 
            ("Portfolio value", "SELECT SUM(total_value) FROM portfolios"),
            ("Outstanding loans", "SELECT SUM(outstanding_balance) FROM loans WHERE loan_status = 'active'"),
            ("Recent transactions", "SELECT COUNT(*) FROM investment_transactions WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'")
        ]
        
        for desc, query in test_queries:
            cursor.execute(query)
            result = cursor.fetchone()[0]
            print(f"  📊 {desc}: {result}")
        
        # Test complex join
        cursor.execute("""
            SELECT c.first_name, c.last_name, COUNT(a.account_id) as accounts, 
                   COALESCE(SUM(a.balance), 0) as total_balance
            FROM customers c
            LEFT JOIN accounts a ON c.customer_id = a.customer_id
            WHERE c.is_active = true
            GROUP BY c.customer_id, c.first_name, c.last_name
            ORDER BY total_balance DESC
            LIMIT 3
        """)
        
        print("\n💰 Top customers by balance:")
        for row in cursor.fetchall():
            print(f"  👤 {row[0]} {row[1]}: {row[2]} accounts, ${row[3]:,.2f}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database verification completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🏦 Financial Services Database Setup")
    print("=" * 50)
    
    # Check if .env file exists (look in project root)
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    env_path = os.path.join(project_root, '.env')
    env_template_path = os.path.join(project_root, 'config', '.env.template')
    
    if not os.path.exists(env_path):
        print("⚠️ .env file not found!")
        print(f"📝 Please copy {env_template_path} to {env_path}")
        print("💡 Required settings: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        return False
    
    # Step 1: Create database
    db_name = create_database()
    if not db_name:
        print("❌ Failed to create database. Check your PostgreSQL connection settings.")
        return False
    
    # Step 2: Setup schema and data
    if not setup_schema_and_data(db_name):
        print("❌ Failed to setup schema and data")
        return False
    
    # Step 3: Verify setup
    if not verify_setup(db_name):
        print("❌ Database verification failed")
        return False
    
    print(f"\n🎉 Financial services database '{db_name}' setup completed!")
    print("🚀 You can now test your RAG system with this financial data")
    print("\n💡 Example queries to try:")
    print("  • 'Show me all high-value customers'")
    print("  • 'What loans are due for payment soon?'")
    print("  • 'Analyze portfolio performance by customer'")
    print("  • 'Find customers with credit scores above 750'")
    print("  • 'Show recent investment transactions'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)