-- Fee Billing Excellence (FBE) POC schema
-- Contracts between banks and payment networks, plus simulated transactions
-- that the agent can cross-check against the contract's fee schedule.

-- Nuke the entire public schema so we start from a clean slate.
-- This removes any leftover tables from prior seeds (financial services DB, etc.)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

CREATE TABLE contracts (
    contract_id       TEXT PRIMARY KEY,
    participant       TEXT NOT NULL,           -- e.g. 'DBS BANK'
    service_provider  TEXT NOT NULL,           -- e.g. 'VISA', 'MASTERCARD', 'PULSE'
    contract_type     TEXT,                    -- 'Participation Agreement', 'Service Agreement', 'Addendum'
    effective_date    DATE NOT NULL,
    term_months       INT,                     -- NULL if open-ended
    source_file       TEXT                     -- filename under data/contracts/
);

CREATE TABLE fee_schedules (
    fee_id          SERIAL PRIMARY KEY,
    contract_id     TEXT REFERENCES contracts(contract_id) ON DELETE CASCADE,
    fee_category    TEXT NOT NULL,             -- 'atm_withdrawal', 'pos', 'online_cnp', 'monthly_service', ...
    fee_amount      NUMERIC(12,6),             -- fixed amount (per txn or per month)
    fee_percentage  NUMERIC(6,4),              -- percentage (0.0175 = 1.75%)
    fee_unit        TEXT NOT NULL,             -- 'per_transaction' | 'per_month' | 'percentage' | 'per_year' | 'per_case'
    notes           TEXT
);

CREATE TABLE transactions (
    transaction_id     SERIAL PRIMARY KEY,
    contract_id        TEXT REFERENCES contracts(contract_id),
    transaction_date   TIMESTAMP NOT NULL,
    transaction_type   TEXT NOT NULL,          -- matches fee_category values
    transaction_amount NUMERIC(12,2) NOT NULL, -- txn amount in USD
    fee_charged        NUMERIC(12,6) NOT NULL, -- what the processor actually charged
    currency           TEXT DEFAULT 'USD',
    merchant_name      TEXT
);

CREATE INDEX idx_transactions_contract_date ON transactions(contract_id, transaction_date DESC);
CREATE INDEX idx_fee_schedules_contract ON fee_schedules(contract_id);
CREATE INDEX idx_fee_schedules_category ON fee_schedules(fee_category);
