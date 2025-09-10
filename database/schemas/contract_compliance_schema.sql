-- Contract Compliance Database Schema
-- Tables: contracts, fees, transactions, discrepancies

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS discrepancies CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS fees CASCADE;
DROP TABLE IF EXISTS contracts CASCADE;

-- Contracts table (stores contract metadata)
CREATE TABLE contracts (
    contract_id SERIAL PRIMARY KEY,
    contract_number VARCHAR(50) UNIQUE NOT NULL,
    contract_name VARCHAR(200) NOT NULL,
    participant VARCHAR(100) NOT NULL,
    service_provider VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    termination_date DATE,
    contract_type VARCHAR(50) NOT NULL, -- 'PARTICIPATION', 'ADDENDUM', 'AMENDMENT'
    status VARCHAR(20) DEFAULT 'ACTIVE', -- 'ACTIVE', 'TERMINATED', 'SUSPENDED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fees table (static reference data for expected fees)
CREATE TABLE fees (
    fee_id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES contracts(contract_id),
    merchant VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    fee_type VARCHAR(50) NOT NULL, -- 'processing_fee', 'network_fee', 'interchange_fee', etc.
    base_amount DECIMAL(10,4) NOT NULL,
    discounted_amount DECIMAL(10,4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_waived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table (high-volume real-time data)
CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    contract_id INTEGER REFERENCES contracts(contract_id),
    merchant VARCHAR(100) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    transaction_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    applied_fees JSONB NOT NULL, -- JSON object with fee_type: amount pairs
    total_fees_applied DECIMAL(10,4) NOT NULL,
    contract_party VARCHAR(100) NOT NULL,
    processing_date DATE NOT NULL,
    settlement_date DATE,
    status VARCHAR(20) DEFAULT 'PROCESSED', -- 'PROCESSED', 'PENDING', 'FAILED'
    reference_number VARCHAR(100),
    terminal_id VARCHAR(50),
    location VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Discrepancies table (stores flagged compliance issues)
CREATE TABLE discrepancies (
    discrepancy_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) REFERENCES transactions(transaction_id),
    contract_id INTEGER REFERENCES contracts(contract_id),
    discrepancy_type VARCHAR(100) NOT NULL, -- 'fee_mismatch', 'missing_fee', 'overcharge', etc.
    expected_value DECIMAL(10,4),
    actual_value DECIMAL(10,4),
    variance_amount DECIMAL(10,4),
    severity VARCHAR(20) NOT NULL, -- 'HIGH', 'MEDIUM', 'LOW'
    description TEXT NOT NULL,
    resolution_status VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'RESOLVED', 'DISPUTED'
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_transactions_contract_id ON transactions(contract_id);
CREATE INDEX idx_transactions_merchant ON transactions(merchant);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_date ON transactions(processing_date);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);

CREATE INDEX idx_fees_contract_merchant_type ON fees(contract_id, merchant, transaction_type);
CREATE INDEX idx_fees_effective_dates ON fees(effective_from, effective_to);

CREATE INDEX idx_discrepancies_transaction ON discrepancies(transaction_id);
CREATE INDEX idx_discrepancies_severity ON discrepancies(severity);
CREATE INDEX idx_discrepancies_status ON discrepancies(resolution_status);
CREATE INDEX idx_discrepancies_flagged_at ON discrepancies(flagged_at);

-- Insert sample contracts
INSERT INTO contracts (contract_number, contract_name, participant, service_provider, effective_date, contract_type) VALUES
('DBS-VISA-2020-001', 'DBS Bank VISA Participation Agreement', 'DBS BANK', 'VISA', '2020-09-13', 'PARTICIPATION'),
('DBS-MC-2021-001', 'DBS Bank MasterCard Service Agreement', 'DBS BANK', 'MASTERCARD', '2021-01-15', 'PARTICIPATION'),
('PULSE-DBS-2020-ADD', 'PULSE Network Access Addendum', 'DBS BANK', 'PULSE NETWORK', '2020-09-13', 'ADDENDUM'),
('AMEX-DBS-2021-002', 'American Express Processing Agreement', 'DBS BANK', 'AMERICAN EXPRESS', '2021-03-01', 'PARTICIPATION');

-- Insert sample fee structures
INSERT INTO fees (contract_id, merchant, transaction_type, fee_type, base_amount, discounted_amount, effective_from) VALUES
-- DBS-VISA Contract Fees
(1, 'DBS BANK', 'ATM_WITHDRAWAL', 'processing_fee', 0.010, 0.005, '2020-09-13'),
(1, 'DBS BANK', 'ATM_WITHDRAWAL', 'network_fee', 0.050, 0.025, '2020-09-13'),
(1, 'DBS BANK', 'CARD_PAYMENT', 'processing_fee', 0.200, 0.150, '2020-09-13'),
(1, 'DBS BANK', 'CARD_PAYMENT', 'fraud_protection_fee', 200.000, 0.000, '2020-09-13'), -- Waived
(1, 'VISA', 'CARD_PAYMENT', 'interchange_fee', 1.500, 1.200, '2020-09-13'),
(1, 'VISA', 'INTERNATIONAL_TXN', 'cross_border_fee', 2.000, 1.500, '2020-09-13'),

-- DBS-MasterCard Contract Fees  
(2, 'DBS BANK', 'ATM_WITHDRAWAL', 'processing_fee', 0.012, 0.008, '2021-01-15'),
(2, 'DBS BANK', 'CARD_PAYMENT', 'processing_fee', 0.180, 0.140, '2021-01-15'),
(2, 'MASTERCARD', 'CARD_PAYMENT', 'interchange_fee', 1.450, 1.100, '2021-01-15'),

-- PULSE Network Fees
(3, 'DBS BANK', 'ATM_WITHDRAWAL', 'network_access_fee', 0.075, 0.050, '2020-09-13'),
(3, 'PULSE NETWORK', 'ATM_WITHDRAWAL', 'switch_fee', 0.025, 0.020, '2020-09-13'),

-- American Express Fees
(4, 'DBS BANK', 'CARD_PAYMENT', 'processing_fee', 0.300, 0.250, '2021-03-01'),
(4, 'AMERICAN EXPRESS', 'CARD_PAYMENT', 'merchant_fee', 2.500, 2.200, '2021-03-01');

-- Update fees to mark fraud protection as waived
UPDATE fees SET is_waived = TRUE WHERE fee_type = 'fraud_protection_fee';