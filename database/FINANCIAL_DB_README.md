# Financial Services Database for RAG Testing

## 🏦 Database Overview

This database contains a comprehensive financial services data model with **13 core tables** and **3 views**, designed to test complex RAG queries in banking and investment scenarios.

## 📊 Database Schema

### Core Entities
- **Branches** (5 records) - Bank branch locations and management
- **Employees** (8 records) - Staff across different departments  
- **Customers** (7 records) - Client profiles with KYC and risk data
- **Products** (10 records) - Financial products (accounts, loans, investments)
- **Accounts** (11 records) - Customer deposit accounts
- **Portfolios** (5 records) - Investment portfolios
- **Loans** (5 records) - Various loan types (mortgage, auto, personal, business)

### Transaction Tables  
- **Portfolio Holdings** (19 records) - Individual securities in portfolios
- **Investment Transactions** (6 records) - Buy/sell/dividend transactions
- **Loan Payments** (7 records) - Loan payment history

### Compliance & Risk
- **Risk Assessments** (7 records) - Credit, investment, AML risk scores
- **Compliance Reports** (5 records) - Regulatory reporting status
- **Audit Logs** (5 records) - System activity tracking

### Views
- **customer_portfolio_summary** - Portfolio overview by customer
- **loan_payment_status** - Payment due status analysis  
- **high_value_customers** - Customers by total assets

## 🚀 Setup Instructions

### 1. Configure Environment
```bash
# Copy template and configure
cp .env.template .env

# Edit .env with your PostgreSQL credentials:
DB_HOST=localhost
DB_PORT=5432  
DB_NAME=financial_services_db
DB_USER=postgres
DB_PASSWORD=your_password
```

### 2. Run Setup Script
```bash
# Make script executable
chmod +x setup_financial_db.py

# Run setup (creates database + schema + data)
python setup_financial_db.py
```

### 3. Manual Setup (Alternative)
```bash
# Create database manually
createdb financial_services_db

# Run SQL script
psql -d financial_services_db -f financial_db_setup.sql
```

## 💬 Example RAG Queries to Test

### Customer Analysis
- "Who are our highest value customers?"
- "Show me customers with credit scores above 750"
- "Find customers in the aggressive risk category"
- "Which customers have multiple loan products?"

### Portfolio Management  
- "What's the performance of our growth portfolios?"
- "Show me all technology stock holdings across portfolios"
- "Which portfolios have the highest YTD returns?"
- "Find portfolios that need rebalancing"

### Loan Management
- "What loans have payments due this week?"
- "Show me mortgage loans with high LTV ratios" 
- "Find customers with multiple active loans"
- "What's our total outstanding loan balance?"

### Risk & Compliance
- "Show me recent risk assessments for high-risk customers"
- "What compliance reports are pending submission?"
- "Find customers with expired KYC status"
- "Show audit activity for the past month"

### Complex Financial Analysis
- "Compare investment performance vs loan profitability by customer"
- "Show customers with both high-value portfolios and active mortgages"
- "Analyze customer distribution across branches and risk profiles"
- "Find correlation between customer income and investment portfolio size"

## 🔍 Key Relationships

The database includes realistic financial relationships:
- **Customer ↔ Multiple Accounts** (checking, savings, business)
- **Customer ↔ Multiple Loans** (mortgage, auto, personal, business)  
- **Customer ↔ Investment Portfolios** with detailed holdings
- **Portfolio ↔ Securities Holdings** with current valuations
- **Loans ↔ Payment History** with principal/interest breakdown
- **Employee ↔ Customer Assignment** (advisors, loan officers)
- **Branch ↔ Customer/Account** geographic relationships
- **Compliance ↔ Risk Management** regulatory tracking

## 💡 Data Highlights

- **Realistic Financial Data**: Market prices, interest rates, credit scores
- **Multiple Asset Classes**: Stocks, ETFs, bonds, mutual funds
- **Comprehensive Loan Types**: Mortgages, auto, personal, business loans
- **Risk Management**: Credit scores, risk assessments, compliance tracking
- **Audit Trail**: Complete activity logging for compliance
- **Geographic Distribution**: Multiple branch locations
- **Time-based Data**: Historical transactions and future payment schedules

## 🧪 Testing Your RAG System

This database is perfect for testing:
1. **Complex Joins** - Multi-table relationships
2. **Financial Calculations** - Portfolio values, loan balances, returns
3. **Date-based Queries** - Payment schedules, compliance deadlines
4. **Aggregations** - Customer totals, portfolio summaries
5. **Conditional Logic** - Risk categories, account statuses
6. **JSON Data** - Risk factors, fee structures (stored as JSONB)

The data represents a mid-size financial institution with realistic complexity for comprehensive RAG system testing.