-- PostgreSQL Script to Create Transactions Table
-- Based on the dashboard SQLite structure

-- Drop table if exists (optional - uncomment if needed)
-- DROP TABLE IF EXISTS transactions;

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_transactions_bank_name ON transactions(bank_name);
CREATE INDEX idx_transactions_contract_id ON transactions(contract_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);

-- Insert sample data (same as SQLite dashboard data)
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

-- Create a view for easy analysis
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

-- Create a view for error analysis
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

-- Display summary information
SELECT 'TRANSACTIONS SUMMARY' as info;
SELECT * FROM transactions_summary;

SELECT 'ERROR ANALYSIS' as info; 
SELECT * FROM transaction_errors;

-- Show table structure
SELECT 'TABLE STRUCTURE' as info;
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'transactions'
ORDER BY ordinal_position;