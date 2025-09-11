-- Complete PostgreSQL Database Setup Script
-- Creates both contracts and transactions tables with sample data

-- ====================
-- 1. CONTRACTS TABLE
-- ====================

-- Drop table if exists (optional - uncomment if needed)
-- DROP TABLE IF EXISTS contracts CASCADE;

-- Create contracts table
CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    contract_id VARCHAR(50) NOT NULL UNIQUE,
    bank_name VARCHAR(100) NOT NULL,
    service_provider VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    standard_transaction_fee DECIMAL(10,3) NOT NULL,
    fixed_fee_component DECIMAL(10,3) NOT NULL,
    us_issuer_atm_fee DECIMAL(10,3) NOT NULL,
    network_security_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    acquirer_atm_fee DECIMAL(10,3) NOT NULL DEFAULT 0.000,
    monthly_service_charge DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    annual_fee DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    interchange_fee_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================
-- 2. TRANSACTIONS TABLE  
-- ====================

-- Drop table if exists (optional - uncomment if needed)
-- DROP TABLE IF EXISTS transactions CASCADE;

-- Create transactions table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    contract_id VARCHAR(50) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(100) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    fee_charged DECIMAL(10,3) NOT NULL,
    expected_fee DECIMAL(10,3) NOT NULL,
    discrepancy TEXT,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    CONSTRAINT fk_transactions_contract 
        FOREIGN KEY (contract_id) 
        REFERENCES contracts(contract_id)
);

-- ====================
-- 3. INDEXES
-- ====================

-- Contracts indexes
CREATE INDEX idx_contracts_bank_name ON contracts(bank_name);
CREATE INDEX idx_contracts_contract_id ON contracts(contract_id);
CREATE INDEX idx_contracts_effective_date ON contracts(effective_date);

-- Transactions indexes  
CREATE INDEX idx_transactions_bank_name ON transactions(bank_name);
CREATE INDEX idx_transactions_contract_id ON transactions(contract_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);

-- ====================
-- 4. INSERT SAMPLE DATA
-- ====================

-- Insert contract data
INSERT INTO contracts (
    contract_id, bank_name, service_provider, effective_date, 
    standard_transaction_fee, fixed_fee_component, us_issuer_atm_fee, 
    network_security_fee, acquirer_atm_fee, monthly_service_charge, 
    annual_fee, interchange_fee_percent
) VALUES
('DBS-VISA-2020-001', 'DBS Bank', 'VISA', '2020-09-13', -0.005, -0.025, -0.150, 200.00, 0.005, 0.00, 0.00, 0.00),
('BOA-VISA-2025-001', 'Bank of America', 'VISA', '2025-03-18', -0.001, -0.001, -0.010, 0.00, 0.000, 50.00, 0.00, 0.00),
('SCB-VISA-2023-002', 'SC Bank', 'VISA', '2023-08-29', 0.050, 0.000, 0.000, 0.00, 0.000, 500.00, 1000.00, 1.75);

-- Insert transaction data (mix of good and bad records for demo)
INSERT INTO transactions (contract_id, bank_name, transaction_type, amount, fee_charged, expected_fee, discrepancy, transaction_date) VALUES

-- DBS Bank transactions (10 total: 8 good, 2 bad)
('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 100.00, -0.005, -0.005, '', '2024-01-05'),
('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 250.00, -0.005, -0.005, '', '2024-01-08'),
('DBS-VISA-2020-001', 'DBS Bank', 'Fixed Fee Component', 0.00, -0.025, -0.025, '', '2024-01-10'),
('DBS-VISA-2020-001', 'DBS Bank', 'ATM Transaction', 80.00, -0.150, -0.150, '', '2024-01-12'),
('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 150.00, -0.005, -0.005, '', '2024-01-14'),
('DBS-VISA-2020-001', 'DBS Bank', 'Acquirer ATM Fee', 45.00, 0.005, 0.005, '', '2024-01-16'),
('DBS-VISA-2020-001', 'DBS Bank', 'Network Security Fee', 0.00, 200.000, 200.000, '', '2024-01-18'),
('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 320.00, -0.005, -0.005, '', '2024-01-20'),
-- BAD transactions (2)
('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 100.00, 0.010, -0.005, 'Fee charged +$0.01 instead of -$0.005 discount', '2024-01-22'),
('DBS-VISA-2020-001', 'DBS Bank', 'ATM Transaction', 60.00, 0.200, -0.150, 'ATM fee charged +$0.20 instead of -$0.15 discount', '2024-01-24'),

-- Bank of America transactions (8 total: 6 good, 2 bad)
('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 200.00, -0.001, -0.001, '', '2024-01-05'),
('BOA-VISA-2025-001', 'Bank of America', 'Fixed Fee Component', 0.00, -0.001, -0.001, '', '2024-01-07'),
('BOA-VISA-2025-001', 'Bank of America', 'ATM Transaction', 75.00, -0.010, -0.010, '', '2024-01-09'),
('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 180.00, -0.001, -0.001, '', '2024-01-11'),
('BOA-VISA-2025-001', 'Bank of America', 'Monthly Service', 0.00, 50.000, 50.000, '', '2024-01-13'),
('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 300.00, -0.001, -0.001, '', '2024-01-15'),
-- BAD transactions (2)
('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 200.00, 0.005, -0.001, 'Fee charged +$0.005 instead of -$0.001 discount', '2024-01-17'),
('BOA-VISA-2025-001', 'Bank of America', 'Monthly Service', 0.00, 75.000, 50.000, 'Monthly service charged $75 instead of $50', '2024-01-19'),

-- SC Bank transactions (7 total: 5 good, 2 bad)
('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 1000.00, 50.000, 50.000, '', '2024-01-05'),
('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 5000.00, 87.500, 87.500, '', '2024-01-07'),
('SCB-VISA-2023-002', 'SC Bank', 'Service Charges', 0.00, 500.000, 500.000, '', '2024-01-09'),
('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 800.00, 40.000, 40.000, '', '2024-01-11'),
('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 3000.00, 52.500, 52.500, '', '2024-01-13'),
-- BAD transactions (2)
('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 1000.00, 75.000, 50.000, 'Processing fee $75 instead of $50 (0.05 per transaction)', '2024-01-15'),
('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 10000.00, 200.000, 175.000, 'Interchange 2.0% instead of 1.75%', '2024-01-17');

-- ====================
-- 5. USEFUL VIEWS
-- ====================

-- Contracts summary view
CREATE VIEW contracts_summary AS
SELECT 
    contract_id,
    bank_name,
    service_provider,
    effective_date,
    CASE 
        WHEN standard_transaction_fee < 0 THEN 'Discount'
        WHEN standard_transaction_fee > 0 THEN 'Charge'
        ELSE 'No Fee'
    END as transaction_fee_type,
    monthly_service_charge,
    annual_fee,
    interchange_fee_percent
FROM contracts
ORDER BY bank_name;

-- Transactions summary view
CREATE VIEW transactions_summary AS
SELECT 
    bank_name,
    COUNT(*) as total_transactions,
    COUNT(CASE WHEN discrepancy != '' THEN 1 END) as transactions_with_errors,
    COUNT(CASE WHEN discrepancy = '' THEN 1 END) as good_transactions,
    ROUND(
        (COUNT(CASE WHEN discrepancy != '' THEN 1 END)::DECIMAL / COUNT(*)) * 100, 
        2
    ) as error_rate_percent,
    SUM(fee_charged - expected_fee) as total_overcharge
FROM transactions 
GROUP BY bank_name
ORDER BY bank_name;

-- Transaction errors view
CREATE VIEW transaction_errors AS
SELECT 
    id,
    contract_id,
    bank_name,
    transaction_type,
    amount,
    fee_charged,
    expected_fee,
    (fee_charged - expected_fee) as variance,
    discrepancy,
    transaction_date
FROM transactions 
WHERE discrepancy != ''
ORDER BY bank_name, transaction_date;

-- ====================
-- 6. DISPLAY SUMMARY
-- ====================

SELECT 'DATABASE SETUP COMPLETE!' as status;

SELECT 'CONTRACTS SUMMARY' as info;
SELECT * FROM contracts_summary;

SELECT 'TRANSACTIONS SUMMARY' as info;
SELECT * FROM transactions_summary;

SELECT 'ERROR ANALYSIS' as info; 
SELECT * FROM transaction_errors;

-- Table counts
SELECT 'TABLE COUNTS' as info;
SELECT 
    'contracts' as table_name, 
    COUNT(*) as record_count 
FROM contracts
UNION ALL
SELECT 
    'transactions' as table_name, 
    COUNT(*) as record_count 
FROM transactions;