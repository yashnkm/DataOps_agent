-- Financial Services Database Schema
-- Complex database structure for testing RAG system with financial data

-- Drop existing tables (if any)
DROP TABLE IF EXISTS loan_payments CASCADE;
DROP TABLE IF EXISTS investment_transactions CASCADE;
DROP TABLE IF EXISTS portfolio_holdings CASCADE;
DROP TABLE IF EXISTS loans CASCADE;
DROP TABLE IF EXISTS portfolios CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS branches CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS risk_assessments CASCADE;
DROP TABLE IF EXISTS compliance_reports CASCADE;

-- 1. BRANCHES TABLE
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    branch_code VARCHAR(10) UNIQUE NOT NULL,
    branch_name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(30) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    country VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    manager_name VARCHAR(100),
    established_date DATE,
    branch_type VARCHAR(20) CHECK (branch_type IN ('main', 'regional', 'local', 'digital')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. EMPLOYEES TABLE
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    employee_code VARCHAR(15) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    job_title VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    branch_id INTEGER REFERENCES branches(branch_id),
    hire_date DATE NOT NULL,
    salary DECIMAL(12,2),
    manager_id INTEGER REFERENCES employees(employee_id),
    security_level INTEGER DEFAULT 1 CHECK (security_level BETWEEN 1 AND 5),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. CUSTOMERS TABLE
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    customer_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    ssn VARCHAR(11) UNIQUE, -- XXX-XX-XXXX format
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    address TEXT NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(30) NOT NULL,
    postal_code VARCHAR(10) NOT NULL,
    country VARCHAR(50) DEFAULT 'USA',
    occupation VARCHAR(100),
    annual_income DECIMAL(12,2),
    credit_score INTEGER CHECK (credit_score BETWEEN 300 AND 850),
    risk_profile VARCHAR(20) CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive')),
    preferred_branch_id INTEGER REFERENCES branches(branch_id),
    assigned_advisor_id INTEGER REFERENCES employees(employee_id),
    customer_since DATE NOT NULL,
    kyc_status VARCHAR(20) DEFAULT 'pending' CHECK (kyc_status IN ('pending', 'verified', 'rejected', 'expired')),
    kyc_expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. PRODUCTS TABLE
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_code VARCHAR(20) UNIQUE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    product_category VARCHAR(50) NOT NULL, -- savings, checking, loan, investment, insurance
    product_type VARCHAR(50) NOT NULL,
    description TEXT,
    minimum_balance DECIMAL(12,2) DEFAULT 0,
    interest_rate DECIMAL(5,4), -- Annual percentage rate
    fees_structure JSONB, -- Store fee details as JSON
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high')),
    regulatory_requirements TEXT,
    eligibility_criteria TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    launch_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. ACCOUNTS TABLE
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    branch_id INTEGER REFERENCES branches(branch_id),
    account_status VARCHAR(20) DEFAULT 'active' CHECK (account_status IN ('active', 'inactive', 'closed', 'frozen', 'dormant')),
    balance DECIMAL(15,2) DEFAULT 0.00,
    available_balance DECIMAL(15,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    interest_rate DECIMAL(5,4),
    overdraft_limit DECIMAL(12,2) DEFAULT 0,
    monthly_fee DECIMAL(8,2) DEFAULT 0,
    last_transaction_date DATE,
    opened_date DATE NOT NULL,
    closed_date DATE,
    maturity_date DATE,
    auto_renewal BOOLEAN DEFAULT FALSE,
    statement_frequency VARCHAR(20) DEFAULT 'monthly',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. PORTFOLIOS TABLE
CREATE TABLE portfolios (
    portfolio_id SERIAL PRIMARY KEY,
    portfolio_name VARCHAR(100) NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    portfolio_type VARCHAR(30) CHECK (portfolio_type IN ('retirement', 'growth', 'income', 'balanced', 'aggressive')),
    risk_tolerance VARCHAR(20) CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive')),
    investment_objective TEXT,
    total_value DECIMAL(15,2) DEFAULT 0.00,
    cash_balance DECIMAL(12,2) DEFAULT 0.00,
    unrealized_gains_losses DECIMAL(12,2) DEFAULT 0.00,
    ytd_return_pct DECIMAL(5,4),
    inception_date DATE NOT NULL,
    last_rebalance_date DATE,
    next_review_date DATE,
    management_fee_pct DECIMAL(4,4) DEFAULT 0.0075, -- 0.75% annual
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. LOANS TABLE
CREATE TABLE loans (
    loan_id SERIAL PRIMARY KEY,
    loan_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    loan_type VARCHAR(30) NOT NULL, -- mortgage, personal, auto, business, student
    loan_purpose VARCHAR(100),
    principal_amount DECIMAL(12,2) NOT NULL,
    outstanding_balance DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,4) NOT NULL,
    term_months INTEGER NOT NULL,
    monthly_payment DECIMAL(10,2) NOT NULL,
    loan_status VARCHAR(20) DEFAULT 'active' CHECK (loan_status IN ('pending', 'approved', 'active', 'paid_off', 'defaulted', 'foreclosed')),
    origination_date DATE NOT NULL,
    first_payment_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    last_payment_date DATE,
    next_payment_date DATE,
    late_fees DECIMAL(8,2) DEFAULT 0.00,
    escrow_balance DECIMAL(10,2) DEFAULT 0.00,
    loan_officer_id INTEGER REFERENCES employees(employee_id),
    collateral_description TEXT,
    ltv_ratio DECIMAL(5,4), -- Loan-to-value ratio
    dti_ratio DECIMAL(5,4), -- Debt-to-income ratio
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. PORTFOLIO HOLDINGS TABLE
CREATE TABLE portfolio_holdings (
    holding_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(portfolio_id),
    symbol VARCHAR(10) NOT NULL, -- Stock/Fund symbol
    security_name VARCHAR(100) NOT NULL,
    security_type VARCHAR(30) NOT NULL, -- stock, bond, mutual_fund, etf, reit
    sector VARCHAR(50),
    quantity DECIMAL(12,4) NOT NULL,
    average_cost DECIMAL(10,4) NOT NULL,
    current_price DECIMAL(10,4) NOT NULL,
    market_value DECIMAL(12,2) NOT NULL,
    unrealized_gain_loss DECIMAL(12,2) DEFAULT 0.00,
    dividend_yield DECIMAL(5,4),
    last_dividend_date DATE,
    purchase_date DATE NOT NULL,
    allocation_percentage DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. INVESTMENT TRANSACTIONS TABLE
CREATE TABLE investment_transactions (
    transaction_id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(portfolio_id),
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    symbol VARCHAR(10),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('buy', 'sell', 'dividend', 'split', 'transfer', 'fee')),
    quantity DECIMAL(12,4),
    price_per_share DECIMAL(10,4),
    total_amount DECIMAL(12,2) NOT NULL,
    fees DECIMAL(8,2) DEFAULT 0.00,
    transaction_date DATE NOT NULL,
    settlement_date DATE NOT NULL,
    description TEXT,
    executed_by_id INTEGER REFERENCES employees(employee_id),
    order_type VARCHAR(20) CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit') OR order_type IS NULL),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. LOAN PAYMENTS TABLE
CREATE TABLE loan_payments (
    payment_id SERIAL PRIMARY KEY,
    loan_id INTEGER NOT NULL REFERENCES loans(loan_id),
    payment_number INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    scheduled_amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2) NOT NULL,
    principal_amount DECIMAL(10,2) NOT NULL,
    interest_amount DECIMAL(10,2) NOT NULL,
    escrow_amount DECIMAL(8,2) DEFAULT 0.00,
    late_fee DECIMAL(6,2) DEFAULT 0.00,
    payment_method VARCHAR(30) DEFAULT 'auto_debit',
    payment_status VARCHAR(20) DEFAULT 'completed' CHECK (payment_status IN ('scheduled', 'completed', 'failed', 'partial')),
    remaining_balance DECIMAL(12,2) NOT NULL,
    processed_by_id INTEGER REFERENCES employees(employee_id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. RISK ASSESSMENTS TABLE
CREATE TABLE risk_assessments (
    assessment_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    assessment_type VARCHAR(30) NOT NULL, -- credit, investment, aml, kyc
    assessment_date DATE NOT NULL,
    risk_score INTEGER CHECK (risk_score BETWEEN 1 AND 100),
    risk_category VARCHAR(20) CHECK (risk_category IN ('low', 'medium', 'high', 'critical')),
    factors_considered JSONB, -- Store risk factors as JSON
    assessment_model VARCHAR(50),
    assessed_by_id INTEGER REFERENCES employees(employee_id),
    review_date DATE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'superseded')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. COMPLIANCE REPORTS TABLE
CREATE TABLE compliance_reports (
    report_id SERIAL PRIMARY KEY,
    report_type VARCHAR(50) NOT NULL, -- aml, bsa, ofac, sox, mifid
    report_period_start DATE NOT NULL,
    report_period_end DATE NOT NULL,
    generated_date DATE NOT NULL,
    generated_by_id INTEGER REFERENCES employees(employee_id),
    reviewed_by_id INTEGER REFERENCES employees(employee_id),
    status VARCHAR(30) DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'approved', 'submitted', 'filed')),
    findings_count INTEGER DEFAULT 0,
    exceptions_count INTEGER DEFAULT 0,
    file_path TEXT,
    regulatory_body VARCHAR(50), -- SEC, FINRA, OCC, etc.
    submission_deadline DATE,
    submitted_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. AUDIT LOGS TABLE
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action_type VARCHAR(20) NOT NULL CHECK (action_type IN ('INSERT', 'UPDATE', 'DELETE', 'SELECT')),
    old_values JSONB,
    new_values JSONB,
    changed_by_id INTEGER REFERENCES employees(employee_id),
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

-- Create indexes for performance
CREATE INDEX idx_customers_customer_number ON customers(customer_number);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_branch ON customers(preferred_branch_id);
CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_status ON accounts(account_status);
CREATE INDEX idx_loans_customer ON loans(customer_id);
CREATE INDEX idx_loans_status ON loans(loan_status);
CREATE INDEX idx_portfolio_customer ON portfolios(customer_id);
CREATE INDEX idx_holdings_portfolio ON portfolio_holdings(portfolio_id);
CREATE INDEX idx_holdings_symbol ON portfolio_holdings(symbol);
CREATE INDEX idx_transactions_portfolio ON investment_transactions(portfolio_id);
CREATE INDEX idx_transactions_date ON investment_transactions(transaction_date);
CREATE INDEX idx_payments_loan ON loan_payments(loan_id);
CREATE INDEX idx_payments_date ON loan_payments(payment_date);
CREATE INDEX idx_risk_customer ON risk_assessments(customer_id);
CREATE INDEX idx_risk_date ON risk_assessments(assessment_date);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_table_record ON audit_logs(table_name, record_id);

-- Insert Sample Data
-- NOTE: Insert order is important due to foreign key constraints
-- Order: branches -> employees -> products -> customers -> accounts -> portfolios/loans -> holdings/transactions

-- 1. Branches (no dependencies)
INSERT INTO branches (branch_code, branch_name, address, city, state, postal_code, country, phone, manager_name, established_date, branch_type) VALUES
('HQ001', 'Downtown Financial Center', '100 Wall Street', 'New York', 'NY', '10005', 'USA', '212-555-0100', 'Sarah Johnson', '1995-03-15', 'main'),
('BR002', 'Midtown Business Hub', '450 Park Avenue', 'New York', 'NY', '10022', 'USA', '212-555-0200', 'Michael Chen', '2001-07-20', 'regional'),
('BR003', 'Silicon Valley Branch', '1 Infinite Loop', 'Cupertino', 'CA', '95014', 'USA', '408-555-0300', 'Lisa Rodriguez', '2010-11-12', 'regional'),
('BR004', 'Miami International', '1450 Brickell Avenue', 'Miami', 'FL', '33131', 'USA', '305-555-0400', 'David Martinez', '2008-05-30', 'regional'),
('DG001', 'Digital Banking Center', '500 Cloud Drive', 'Austin', 'TX', '73301', 'USA', '512-555-0500', 'Jennifer Kim', '2020-01-15', 'digital');

-- 2. Employees (depends on branches)
INSERT INTO employees (employee_code, first_name, last_name, email, phone, job_title, department, branch_id, hire_date, salary, security_level) VALUES
('EMP001', 'Sarah', 'Johnson', 'sarah.johnson@finbank.com', '212-555-1001', 'Branch Manager', 'Operations', 1, '2020-01-15', 125000.00, 4),
('EMP002', 'Michael', 'Chen', 'michael.chen@finbank.com', '212-555-1002', 'Senior Financial Advisor', 'Wealth Management', 2, '2019-03-20', 95000.00, 3),
('EMP003', 'Lisa', 'Rodriguez', 'lisa.rodriguez@finbank.com', '408-555-1003', 'Investment Specialist', 'Investment Services', 3, '2021-06-10', 88000.00, 3),
('EMP004', 'David', 'Martinez', 'david.martinez@finbank.com', '305-555-1004', 'Loan Officer', 'Lending', 4, '2018-09-05', 78000.00, 2),
('EMP005', 'Jennifer', 'Kim', 'jennifer.kim@finbank.com', '512-555-1005', 'Digital Operations Manager', 'Technology', 5, '2020-02-01', 110000.00, 4),
('EMP006', 'Robert', 'Taylor', 'robert.taylor@finbank.com', '212-555-1006', 'Risk Analyst', 'Risk Management', 1, '2022-01-12', 72000.00, 3),
('EMP007', 'Amanda', 'Wilson', 'amanda.wilson@finbank.com', '212-555-1007', 'Compliance Officer', 'Compliance', 1, '2019-11-08', 85000.00, 4),
('EMP008', 'James', 'Brown', 'james.brown@finbank.com', '408-555-1008', 'Portfolio Manager', 'Investment Services', 3, '2017-04-25', 135000.00, 3);

-- 3. Products (no dependencies)
INSERT INTO products (product_code, product_name, product_category, product_type, description, minimum_balance, interest_rate, risk_level, launch_date) VALUES
('SAV001', 'Premium Savings Account', 'savings', 'savings_account', 'High-yield savings with tiered interest rates', 1000.00, 0.0425, 'low', '2015-01-01'),
('CHK001', 'Business Checking Pro', 'checking', 'business_checking', 'Full-service business checking with no monthly fees', 5000.00, 0.0050, 'low', '2016-03-15'),
('CHK002', 'Personal Checking Plus', 'checking', 'personal_checking', 'Premium checking with overdraft protection', 500.00, 0.0025, 'low', '2014-06-01'),
('MTG001', 'Fixed Rate Mortgage 30Y', 'loan', 'mortgage', '30-year fixed rate home mortgage', 0.00, 0.0675, 'medium', '2010-01-01'),
('MTG002', 'Adjustable Rate Mortgage 5/1', 'loan', 'mortgage', '5-year ARM with 30-year amortization', 0.00, 0.0525, 'medium', '2012-05-01'),
('PRS001', 'Personal Loan Express', 'loan', 'personal_loan', 'Unsecured personal loan up to $50K', 0.00, 0.1250, 'medium', '2018-02-01'),
('AUTO001', 'New Auto Loan', 'loan', 'auto_loan', 'Financing for new vehicle purchases', 0.00, 0.0475, 'low', '2015-09-01'),
('INV001', 'Growth Portfolio Fund', 'investment', 'mutual_fund', 'Diversified growth-focused mutual fund', 10000.00, 0.0000, 'medium', '2016-11-01'),
('INV002', 'Conservative Bond Fund', 'investment', 'bond_fund', 'Government and corporate bond portfolio', 5000.00, 0.0000, 'low', '2014-08-01'),
('RET001', '401k Retirement Plan', 'investment', 'retirement_plan', 'Employer-sponsored retirement savings', 0.00, 0.0000, 'medium', '2013-01-01');

-- 4. Customers (depends on branches, employees)
INSERT INTO customers (customer_number, first_name, last_name, date_of_birth, ssn, email, phone, address, city, state, postal_code, occupation, annual_income, credit_score, risk_profile, preferred_branch_id, assigned_advisor_id, customer_since, kyc_status, kyc_expiry_date) VALUES
('CUST000001', 'John', 'Smith', '1975-03-20', '123-45-6789', 'john.smith@email.com', '555-0101', '123 Oak Street', 'New York', 'NY', '10001', 'Software Engineer', 125000.00, 720, 'moderate', 1, 2, '2018-05-15', 'verified', '2025-05-15'),
('CUST000002', 'Emily', 'Davis', '1982-11-08', '234-56-7890', 'emily.davis@email.com', '555-0102', '456 Pine Avenue', 'Los Angeles', 'CA', '90210', 'Marketing Director', 98000.00, 685, 'moderate', 3, 3, '2019-02-10', 'verified', '2025-02-10'),
('CUST000003', 'Robert', 'Wilson', '1965-07-14', '345-67-8901', 'robert.wilson@email.com', '555-0103', '789 Maple Drive', 'Chicago', 'IL', '60601', 'Financial Consultant', 185000.00, 780, 'aggressive', 2, 2, '2016-09-22', 'verified', '2024-09-22'),
('CUST000004', 'Maria', 'Garcia', '1988-12-03', '456-78-9012', 'maria.garcia@email.com', '555-0104', '321 Elm Street', 'Miami', 'FL', '33101', 'Doctor', 220000.00, 745, 'conservative', 4, 8, '2020-01-08', 'verified', '2026-01-08'),
('CUST000005', 'William', 'Anderson', '1978-09-25', '567-89-0123', 'william.anderson@email.com', '555-0105', '654 Cedar Lane', 'Austin', 'TX', '73301', 'Business Owner', 310000.00, 695, 'aggressive', 5, 3, '2017-11-30', 'verified', '2025-11-30'),
('CUST000006', 'Jennifer', 'Taylor', '1990-04-17', '678-90-1234', 'jennifer.taylor@email.com', '555-0106', '987 Birch Road', 'San Francisco', 'CA', '94102', 'Data Scientist', 145000.00, 710, 'moderate', 3, 3, '2021-08-12', 'verified', '2027-08-12'),
('CUST000007', 'Thomas', 'Moore', '1970-01-30', '789-01-2345', 'thomas.moore@email.com', '555-0107', '147 Spruce Street', 'Boston', 'MA', '02101', 'Investment Banker', 275000.00, 765, 'aggressive', 1, 2, '2015-04-18', 'verified', '2025-04-18');

-- 5. Accounts (depends on customers, products, branches)
INSERT INTO accounts (account_number, customer_id, product_id, branch_id, balance, available_balance, interest_rate, opened_date, last_transaction_date) VALUES
('ACC-SAV-001001', 1, 1, 1, 25500.75, 25500.75, 0.0425, '2018-05-20', '2024-08-28'),
('ACC-CHK-001002', 1, 3, 1, 3200.50, 2950.50, 0.0025, '2018-05-20', '2024-08-30'),
('ACC-SAV-002001', 2, 1, 3, 18750.25, 18750.25, 0.0425, '2019-02-15', '2024-08-29'),
('ACC-CHK-002002', 2, 3, 3, 4580.00, 4580.00, 0.0025, '2019-02-15', '2024-08-30'),
('ACC-BUS-003001', 3, 2, 2, 127500.00, 125000.00, 0.0050, '2016-09-25', '2024-08-30'),
('ACC-SAV-003002', 3, 1, 2, 85000.00, 85000.00, 0.0425, '2016-10-01', '2024-08-25'),
('ACC-SAV-004001', 4, 1, 4, 95000.00, 95000.00, 0.0425, '2020-01-10', '2024-08-27'),
('ACC-CHK-004002', 4, 3, 4, 12500.00, 12500.00, 0.0025, '2020-01-10', '2024-08-30'),
('ACC-BUS-005001', 5, 2, 5, 458000.00, 450000.00, 0.0050, '2017-12-05', '2024-08-30'),
('ACC-SAV-006001', 6, 1, 3, 62000.00, 62000.00, 0.0425, '2021-08-15', '2024-08-26'),
('ACC-SAV-007001', 7, 1, 1, 185000.00, 185000.00, 0.0425, '2015-04-20', '2024-08-29');

-- 6. Portfolios (depends on customers, accounts)
INSERT INTO portfolios (portfolio_name, customer_id, account_id, portfolio_type, risk_tolerance, investment_objective, total_value, cash_balance, ytd_return_pct, inception_date, management_fee_pct) VALUES
('Growth Portfolio', 3, 6, 'growth', 'aggressive', 'Long-term capital appreciation with 15+ year horizon', 285000.00, 15000.00, 0.0850, '2016-10-15', 0.0075),
('Retirement 401k', 4, 7, 'retirement', 'conservative', 'Retirement savings with capital preservation focus', 420000.00, 25000.00, 0.0625, '2020-02-01', 0.0050),
('Executive Portfolio', 5, 9, 'balanced', 'aggressive', 'Balanced growth and income for high net worth client', 1250000.00, 75000.00, 0.0920, '2018-01-10', 0.0100),
('Tech Growth Fund', 6, 10, 'growth', 'moderate', 'Technology-focused growth portfolio', 195000.00, 8000.00, 0.1150, '2021-09-01', 0.0075),
('Conservative Income', 7, 11, 'income', 'conservative', 'Income generation with low volatility', 350000.00, 20000.00, 0.0485, '2015-06-01', 0.0060);

-- 7. Loans (depends on customers, products, employees)
INSERT INTO loans (loan_number, customer_id, product_id, loan_type, loan_purpose, principal_amount, outstanding_balance, interest_rate, term_months, monthly_payment, loan_status, origination_date, first_payment_date, maturity_date, loan_officer_id, ltv_ratio, dti_ratio) VALUES
('LOAN-MTG-001', 1, 4, 'mortgage', 'Primary residence purchase', 485000.00, 456200.50, 0.0675, 360, 3145.82, 'active', '2019-06-01', '2019-07-01', '2049-06-01', 4, 0.8500, 0.2800),
('LOAN-AUTO-001', 2, 7, 'auto_loan', 'New vehicle purchase', 35000.00, 28750.00, 0.0475, 60, 651.25, 'active', '2022-03-15', '2022-04-15', '2027-03-15', 4, 0.9000, 0.1850),
('LOAN-PRS-001', 6, 6, 'personal_loan', 'Home renovation', 25000.00, 18500.00, 0.1250, 48, 658.33, 'active', '2023-01-10', '2023-02-10', '2027-01-10', 4, 0.0000, 0.2200),
('LOAN-MTG-002', 7, 4, 'mortgage', 'Investment property', 650000.00, 624500.00, 0.0725, 360, 4425.50, 'active', '2018-11-01', '2018-12-01', '2048-11-01', 4, 0.7500, 0.3200),
('LOAN-BUS-001', 5, 6, 'business_loan', 'Equipment financing', 150000.00, 98500.00, 0.0850, 84, 2145.75, 'active', '2021-05-01', '2021-06-01', '2028-05-01', 4, 0.0000, 0.1500);

-- 8. Portfolio Holdings (depends on portfolios)
INSERT INTO portfolio_holdings (portfolio_id, symbol, security_name, security_type, sector, quantity, average_cost, current_price, market_value, unrealized_gain_loss, dividend_yield, purchase_date, allocation_percentage) VALUES
-- Growth Portfolio (Robert Wilson)
(1, 'AAPL', 'Apple Inc.', 'stock', 'Technology', 150.0000, 145.50, 175.25, 26287.50, 4462.50, 0.0044, '2020-03-15', 0.0921),
(1, 'MSFT', 'Microsoft Corporation', 'stock', 'Technology', 100.0000, 285.75, 325.80, 32580.00, 4005.00, 0.0072, '2019-11-20', 0.1143),
(1, 'TSLA', 'Tesla Inc.', 'stock', 'Automotive', 75.0000, 220.30, 245.60, 18420.00, 1897.50, 0.0000, '2021-06-10', 0.0646),
(1, 'VTI', 'Vanguard Total Stock Market ETF', 'etf', 'Diversified', 200.0000, 185.25, 195.75, 39150.00, 2100.00, 0.0158, '2017-08-01', 0.1374),
(1, 'SPY', 'SPDR S&P 500 ETF', 'etf', 'Large Cap', 180.0000, 390.50, 425.80, 76644.00, 6354.00, 0.0131, '2018-01-15', 0.2690),

-- Retirement 401k (Maria Garcia)
(2, 'VTI', 'Vanguard Total Stock Market ETF', 'etf', 'Diversified', 350.0000, 180.25, 195.75, 68512.50, 5425.00, 0.0158, '2020-03-01', 0.1631),
(2, 'VXUS', 'Vanguard Total International Stock ETF', 'etf', 'International', 200.0000, 52.80, 55.90, 11180.00, 620.00, 0.0285, '2020-03-01', 0.0266),
(2, 'BND', 'Vanguard Total Bond Market ETF', 'etf', 'Fixed Income', 500.0000, 78.50, 76.25, 38125.00, -1125.00, 0.0445, '2020-03-01', 0.0908),
(2, 'VTEB', 'Vanguard Tax-Exempt Bond ETF', 'etf', 'Municipal Bonds', 300.0000, 51.75, 52.10, 15630.00, 105.00, 0.0425, '2021-01-15', 0.0372),

-- Executive Portfolio (William Anderson)
(3, 'BRK.A', 'Berkshire Hathaway Inc.', 'stock', 'Conglomerate', 2.0000, 485000.00, 525000.00, 1050000.00, 80000.00, 0.0000, '2018-02-01', 0.8400),
(3, 'JNJ', 'Johnson & Johnson', 'stock', 'Healthcare', 500.0000, 165.25, 172.80, 86400.00, 3775.00, 0.0289, '2019-05-10', 0.0691),
(3, 'PG', 'Procter & Gamble Co.', 'stock', 'Consumer Goods', 200.0000, 135.50, 148.75, 29750.00, 2650.00, 0.0247, '2020-01-20', 0.0238),

-- Tech Growth Fund (Jennifer Taylor)
(4, 'GOOGL', 'Alphabet Inc.', 'stock', 'Technology', 80.0000, 125.50, 138.25, 11060.00, 1020.00, 0.0000, '2021-09-15', 0.0567),
(4, 'AMZN', 'Amazon.com Inc.', 'stock', 'E-commerce', 45.0000, 145.75, 152.90, 6880.50, 321.75, 0.0000, '2021-10-01', 0.0353),
(4, 'META', 'Meta Platforms Inc.', 'stock', 'Social Media', 60.0000, 285.50, 298.75, 17925.00, 795.00, 0.0000, '2022-01-10', 0.0919),
(4, 'NVDA', 'NVIDIA Corporation', 'stock', 'Semiconductors', 35.0000, 425.80, 465.25, 16283.75, 1380.75, 0.0038, '2021-12-05', 0.0834),

-- Conservative Income (Thomas Moore)
(5, 'T', 'AT&T Inc.', 'stock', 'Telecommunications', 1000.0000, 18.50, 17.25, 17250.00, -1250.00, 0.0725, '2016-01-01', 0.0493),
(5, 'VZ', 'Verizon Communications', 'stock', 'Telecommunications', 800.0000, 42.75, 41.85, 33480.00, -720.00, 0.0635, '2016-02-15', 0.0957),
(5, 'JNJ', 'Johnson & Johnson', 'stock', 'Healthcare', 600.0000, 158.25, 172.80, 103680.00, 8730.00, 0.0289, '2017-03-10', 0.2962),
(5, 'KO', 'The Coca-Cola Company', 'stock', 'Consumer Staples', 700.0000, 55.80, 58.45, 40915.00, 1855.00, 0.0307, '2018-06-01', 0.1169),
(5, 'PFE', 'Pfizer Inc.', 'stock', 'Pharmaceuticals', 900.0000, 35.50, 33.90, 30510.00, -1440.00, 0.0598, '2019-01-15', 0.0871);

-- 9. Investment Transactions (depends on portfolios, accounts, employees)
INSERT INTO investment_transactions (portfolio_id, account_id, symbol, transaction_type, quantity, price_per_share, total_amount, fees, transaction_date, settlement_date, executed_by_id, order_type) VALUES
(1, 6, 'AAPL', 'buy', 25.0000, 175.25, 4381.25, 9.95, '2024-08-15', '2024-08-17', 3, 'market'),
(1, 6, 'MSFT', 'buy', 15.0000, 325.80, 4887.00, 9.95, '2024-08-20', '2024-08-22', 3, 'limit'),
(2, 7, 'VTI', 'buy', 50.0000, 195.75, 9787.50, 0.00, '2024-08-10', '2024-08-12', 8, 'market'),
(3, 9, 'JNJ', 'buy', 100.0000, 172.80, 17280.00, 25.00, '2024-07-25', '2024-07-27', 2, 'market'),
(4, 10, 'NVDA', 'sell', 10.0000, 465.25, 4652.50, 15.00, '2024-08-22', '2024-08-24', 3, 'market'),
(5, 11, 'T', 'dividend', 1000.0000, 0.2775, 277.50, 0.00, '2024-08-01', '2024-08-01', null, null);

-- 10. Loan Payments (depends on loans)
INSERT INTO loan_payments (loan_id, payment_number, payment_date, scheduled_amount, actual_amount, principal_amount, interest_amount, payment_status, remaining_balance) VALUES
(1, 62, '2024-08-01', 3145.82, 3145.82, 1548.25, 1597.57, 'completed', 456200.50),
(1, 63, '2024-09-01', 3145.82, 3145.82, 1556.95, 1588.87, 'completed', 454643.55),
(2, 29, '2024-08-15', 651.25, 651.25, 540.85, 110.40, 'completed', 28750.00),
(2, 30, '2024-09-15', 651.25, 651.25, 542.70, 108.55, 'completed', 28207.30),
(3, 20, '2024-08-10', 658.33, 658.33, 466.15, 192.18, 'completed', 18500.00),
(4, 70, '2024-08-01', 4425.50, 4425.50, 1650.75, 2774.75, 'completed', 624500.00),
(5, 39, '2024-08-01', 2145.75, 2145.75, 1456.25, 689.50, 'completed', 98500.00);

-- 11. Risk Assessments (depends on customers, employees)
INSERT INTO risk_assessments (customer_id, assessment_type, assessment_date, risk_score, risk_category, factors_considered, assessment_model, assessed_by_id, review_date, status) VALUES
(1, 'credit', '2024-01-15', 72, 'medium', '{"credit_history": "good", "debt_to_income": 0.28, "employment_stability": "stable"}', 'FICO_v9', 6, '2025-01-15', 'active'),
(2, 'investment', '2024-03-20', 65, 'medium', '{"risk_tolerance": "moderate", "investment_experience": "intermediate", "time_horizon": "long"}', 'Risk_Profile_v2', 3, '2025-03-20', 'active'),
(3, 'aml', '2024-02-10', 25, 'low', '{"transaction_patterns": "normal", "geographic_risk": "low", "occupation_risk": "low"}', 'AML_Screen_v3', 7, '2024-08-10', 'active'),
(4, 'credit', '2024-04-05', 78, 'medium', '{"credit_history": "excellent", "debt_to_income": 0.15, "assets": "substantial"}', 'FICO_v9', 6, '2025-04-05', 'active'),
(5, 'investment', '2024-01-30', 85, 'high', '{"net_worth": "high", "investment_experience": "expert", "risk_capacity": "high"}', 'Risk_Profile_v2', 2, '2025-01-30', 'active'),
(6, 'kyc', '2024-07-12', 45, 'low', '{"identity_verification": "passed", "address_verification": "passed", "income_verification": "passed"}', 'KYC_Enhanced_v1', 7, '2025-07-12', 'active'),
(7, 'credit', '2023-12-01', 88, 'low', '{"credit_history": "exceptional", "debt_to_income": 0.22, "assets": "very_high"}', 'FICO_v9', 6, '2024-12-01', 'active');

-- 12. Compliance Reports (depends on employees)
INSERT INTO compliance_reports (report_type, report_period_start, report_period_end, generated_date, generated_by_id, status, findings_count, exceptions_count, regulatory_body, submission_deadline) VALUES
('aml', '2024-07-01', '2024-07-31', '2024-08-05', 7, 'submitted', 0, 0, 'FinCEN', '2024-08-15'),
('bsa', '2024-04-01', '2024-06-30', '2024-07-10', 7, 'filed', 2, 0, 'OCC', '2024-07-30'),
('sox', '2024-04-01', '2024-06-30', '2024-07-15', 7, 'approved', 1, 1, 'SEC', '2024-08-14'),
('mifid', '2024-07-01', '2024-07-31', '2024-08-01', 7, 'review', 0, 0, 'FCA', '2024-08-20'),
('ofac', '2024-08-01', '2024-08-31', '2024-09-01', 7, 'draft', 0, 0, 'OFAC', '2024-09-15');

-- 13. Audit Logs (depends on employees)
INSERT INTO audit_logs (table_name, record_id, action_type, old_values, new_values, changed_by_id, ip_address, session_id, reason) VALUES
('customers', 1, 'UPDATE', '{"credit_score": 715}', '{"credit_score": 720}', 6, '192.168.1.100', 'sess_12345', 'Credit score update from bureau'),
('accounts', 1, 'UPDATE', '{"balance": 25200.75}', '{"balance": 25500.75}', 2, '192.168.1.101', 'sess_12346', 'Interest payment posting'),
('loan_payments', 1, 'INSERT', null, '{"payment_id": 1, "amount": 3145.82, "status": "completed"}', 4, '192.168.1.102', 'sess_12347', 'Automated loan payment processing'),
('portfolio_holdings', 1, 'UPDATE', '{"current_price": 170.25, "market_value": 25537.50}', '{"current_price": 175.25, "market_value": 26287.50}', 3, '192.168.1.103', 'sess_12348', 'End-of-day price update'),
('risk_assessments', 1, 'INSERT', null, '{"assessment_id": 1, "risk_score": 72}', 6, '192.168.1.104', 'sess_12349', 'Annual risk assessment review');

-- Create views for common queries
CREATE VIEW customer_portfolio_summary AS
SELECT 
    c.customer_number,
    c.first_name,
    c.last_name,
    p.portfolio_name,
    p.portfolio_type,
    p.total_value,
    p.ytd_return_pct,
    COUNT(ph.holding_id) as holdings_count
FROM customers c
JOIN portfolios p ON c.customer_id = p.customer_id
LEFT JOIN portfolio_holdings ph ON p.portfolio_id = ph.portfolio_id
GROUP BY c.customer_id, c.customer_number, c.first_name, c.last_name, 
         p.portfolio_name, p.portfolio_type, p.total_value, p.ytd_return_pct;

CREATE VIEW loan_payment_status AS
SELECT 
    c.customer_number,
    c.first_name,
    c.last_name,
    l.loan_number,
    l.loan_type,
    l.outstanding_balance,
    l.monthly_payment,
    l.next_payment_date,
    CASE 
        WHEN l.next_payment_date < CURRENT_DATE THEN 'OVERDUE'
        WHEN l.next_payment_date <= CURRENT_DATE + INTERVAL '5 days' THEN 'DUE_SOON'
        ELSE 'CURRENT'
    END as payment_status
FROM customers c
JOIN loans l ON c.customer_id = l.customer_id
WHERE l.loan_status = 'active';

CREATE VIEW high_value_customers AS
SELECT 
    c.customer_number,
    c.first_name,
    c.last_name,
    c.annual_income,
    COALESCE(SUM(a.balance), 0) as total_deposits,
    COALESCE(SUM(p.total_value), 0) as total_investments,
    COALESCE(SUM(l.outstanding_balance), 0) as total_loans,
    COUNT(DISTINCT a.account_id) as account_count
FROM customers c
LEFT JOIN accounts a ON c.customer_id = a.customer_id
LEFT JOIN portfolios p ON c.customer_id = p.customer_id
LEFT JOIN loans l ON c.customer_id = l.customer_id AND l.loan_status = 'active'
GROUP BY c.customer_id, c.customer_number, c.first_name, c.last_name, c.annual_income
HAVING (COALESCE(SUM(a.balance), 0) + COALESCE(SUM(p.total_value), 0)) > 100000
ORDER BY (COALESCE(SUM(a.balance), 0) + COALESCE(SUM(p.total_value), 0)) DESC;

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_user;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO rag_user;