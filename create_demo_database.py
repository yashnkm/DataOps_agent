import sqlite3
import os
from datetime import datetime

# Connect to database (assuming SQLite for demo)
try:
    conn = sqlite3.connect('dashboard_contracts.db')
    cursor = conn.cursor()
    
    # Create contracts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY,
            contract_id TEXT,
            bank_name TEXT,
            service_provider TEXT,
            effective_date DATE,
            standard_transaction_fee REAL,
            fixed_fee_component REAL,
            us_issuer_atm_fee REAL,
            network_security_fee REAL,
            acquirer_atm_fee REAL,
            monthly_service_charge REAL,
            annual_fee REAL,
            interchange_fee_percent REAL
        )
    ''')
    
    # Create transactions table with intentional errors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            contract_id TEXT,
            bank_name TEXT,
            transaction_type TEXT,
            amount REAL,
            fee_charged REAL,
            expected_fee REAL,
            discrepancy TEXT,
            transaction_date DATE
        )
    ''')
    
    # Insert contract data (correct data)
    contracts = [
        ('DBS-VISA-2020-001', 'DBS Bank', 'VISA', '2020-09-13', -0.005, -0.025, -0.15, 200.0, 0.005, 0.0, 0.0, 0.0),
        ('BOA-VISA-2025-001', 'Bank of America', 'VISA', '2025-03-18', -0.001, -0.001, -0.01, 0.0, 0.0, 50.0, 0.0, 0.0),
        ('SCB-VISA-2023-002', 'SC Bank', 'VISA', '2023-08-29', 0.05, 0.0, 0.0, 0.0, 0.0, 500.0, 1000.0, 1.75)
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO contracts 
        (contract_id, bank_name, service_provider, effective_date, standard_transaction_fee, 
         fixed_fee_component, us_issuer_atm_fee, network_security_fee, acquirer_atm_fee, 
         monthly_service_charge, annual_fee, interchange_fee_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', contracts)
    
    # Insert transaction data with INTENTIONAL ERRORS for demo
    transactions = [
        # DBS Bank transactions - ERROR: Wrong standard transaction fee
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 100.0, 0.01, -0.005, 'Fee charged +$0.01 instead of -$0.005 discount', '2024-01-15'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'ATM Transaction', 50.0, 0.20, -0.15, 'ATM fee charged +$0.20 instead of -$0.15 discount', '2024-01-16'),
        
        # Bank of America transactions - ERROR: Wrong fixed fee component  
        ('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 200.0, 0.005, -0.001, 'Fee charged +$0.005 instead of -$0.001 discount', '2024-01-17'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Monthly Service', 0.0, 75.0, 50.0, 'Monthly service charged $75 instead of $50', '2024-01-18'),
        
        # SC Bank transactions - ERROR: Wrong interchange fee percentage
        ('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 1000.0, 75.0, 50.0, 'Processing fee $75 instead of $50 (0.05 per transaction)', '2024-01-19'),
        ('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 10000.0, 200.0, 175.0, 'Interchange 2.0% instead of 1.75%', '2024-01-20')
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO transactions 
        (contract_id, bank_name, transaction_type, amount, fee_charged, expected_fee, discrepancy, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', transactions)
    
    conn.commit()
    
    print('✅ Database created successfully with contract and transaction data')
    print('📊 Intentional discrepancies added for demo purposes')
    
    # Verify data
    print('\n📋 CONTRACTS TABLE:')
    cursor.execute('SELECT contract_id, bank_name, standard_transaction_fee, monthly_service_charge FROM contracts')
    for row in cursor.fetchall():
        print(f'  {row}')
    
    print('\n💰 TRANSACTIONS TABLE (with intentional errors):')  
    cursor.execute('SELECT contract_id, bank_name, transaction_type, fee_charged, expected_fee FROM transactions LIMIT 6')
    for row in cursor.fetchall():
        print(f'  {row}')
        
    conn.close()
    
except Exception as e:
    print(f'❌ Error creating database: {e}')