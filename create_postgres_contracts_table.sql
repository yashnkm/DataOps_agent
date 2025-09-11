-- PostgreSQL Script to Create Contracts Table
-- Based on the dashboard SQLite structure

-- Drop table if exists (optional - uncomment if needed)
-- DROP TABLE IF EXISTS contracts;

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

-- Create indexes for better performance
CREATE INDEX idx_contracts_bank_name ON contracts(bank_name);
CREATE INDEX idx_contracts_contract_id ON contracts(contract_id);
CREATE INDEX idx_contracts_effective_date ON contracts(effective_date);

-- Insert sample contract data
INSERT INTO contracts (
    contract_id, bank_name, service_provider, effective_date, 
    standard_transaction_fee, fixed_fee_component, us_issuer_atm_fee, 
    network_security_fee, acquirer_atm_fee, monthly_service_charge, 
    annual_fee, interchange_fee_percent
) VALUES

-- DBS Bank Contract
('DBS-VISA-2020-001', 'DBS Bank', 'VISA', '2020-09-13', -0.005, -0.025, -0.150, 200.00, 0.005, 0.00, 0.00, 0.00),

-- Bank of America Contract  
('BOA-VISA-2025-001', 'Bank of America', 'VISA', '2025-03-18', -0.001, -0.001, -0.010, 0.00, 0.000, 50.00, 0.00, 0.00),

-- SC Bank Contract
('SCB-VISA-2023-002', 'SC Bank', 'VISA', '2023-08-29', 0.050, 0.000, 0.000, 0.00, 0.000, 500.00, 1000.00, 1.75);

-- Create view for contract summary
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
    CASE 
        WHEN monthly_service_charge > 0 THEN monthly_service_charge
        ELSE 0
    END as monthly_charges,
    CASE 
        WHEN annual_fee > 0 THEN annual_fee
        ELSE 0  
    END as annual_charges,
    interchange_fee_percent
FROM contracts
ORDER BY bank_name;

-- Display contract information
SELECT 'CONTRACTS SUMMARY' as info;
SELECT * FROM contracts_summary;

-- Show table structure
SELECT 'CONTRACTS TABLE STRUCTURE' as info;
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'contracts'
ORDER BY ordinal_position;