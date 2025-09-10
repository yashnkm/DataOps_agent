import sqlite3
import os
from datetime import datetime, timedelta
import random

# Connect to database
try:
    conn = sqlite3.connect('dashboard_contracts.db')
    cursor = conn.cursor()
    
    # Clear existing transactions
    cursor.execute('DELETE FROM transactions')
    
    # Generate more realistic transaction data with mix of good and bad records
    base_date = datetime(2024, 1, 1)
    
    # DBS Bank transactions (10 total: 8 good, 2 bad)
    dbs_transactions = [
        # GOOD transactions (8)
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 100.0, -0.005, -0.005, '', '2024-01-05'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 250.0, -0.005, -0.005, '', '2024-01-08'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Fixed Fee Component', 0.0, -0.025, -0.025, '', '2024-01-10'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'ATM Transaction', 80.0, -0.15, -0.15, '', '2024-01-12'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 150.0, -0.005, -0.005, '', '2024-01-14'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Acquirer ATM Fee', 45.0, 0.005, 0.005, '', '2024-01-16'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Network Security Fee', 0.0, 200.0, 200.0, '', '2024-01-18'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 320.0, -0.005, -0.005, '', '2024-01-20'),
        
        # BAD transactions (2)
        ('DBS-VISA-2020-001', 'DBS Bank', 'Standard Transaction', 100.0, 0.01, -0.005, 'Fee charged +$0.01 instead of -$0.005 discount', '2024-01-22'),
        ('DBS-VISA-2020-001', 'DBS Bank', 'ATM Transaction', 60.0, 0.20, -0.15, 'ATM fee charged +$0.20 instead of -$0.15 discount', '2024-01-24'),
    ]
    
    # Bank of America transactions (8 total: 6 good, 2 bad)
    boa_transactions = [
        # GOOD transactions (6)
        ('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 200.0, -0.001, -0.001, '', '2024-01-05'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Fixed Fee Component', 0.0, -0.001, -0.001, '', '2024-01-07'),
        ('BOA-VISA-2025-001', 'Bank of America', 'ATM Transaction', 75.0, -0.01, -0.01, '', '2024-01-09'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 180.0, -0.001, -0.001, '', '2024-01-11'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Monthly Service', 0.0, 50.0, 50.0, '', '2024-01-13'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 300.0, -0.001, -0.001, '', '2024-01-15'),
        
        # BAD transactions (2)
        ('BOA-VISA-2025-001', 'Bank of America', 'Standard Transaction', 200.0, 0.005, -0.001, 'Fee charged +$0.005 instead of -$0.001 discount', '2024-01-17'),
        ('BOA-VISA-2025-001', 'Bank of America', 'Monthly Service', 0.0, 75.0, 50.0, 'Monthly service charged $75 instead of $50', '2024-01-19'),
    ]
    
    # SC Bank transactions (7 total: 5 good, 2 bad)
    sc_transactions = [
        # GOOD transactions (5)
        ('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 1000.0, 50.0, 50.0, '', '2024-01-05'),
        ('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 5000.0, 87.5, 87.5, '', '2024-01-07'),  # 1.75% of 5000
        ('SCB-VISA-2023-002', 'SC Bank', 'Service Charges', 0.0, 500.0, 500.0, '', '2024-01-09'),
        ('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 800.0, 40.0, 40.0, '', '2024-01-11'),  # 0.05 * 800
        ('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 3000.0, 52.5, 52.5, '', '2024-01-13'),  # 1.75% of 3000
        
        # BAD transactions (2)
        ('SCB-VISA-2023-002', 'SC Bank', 'Transaction Processing', 1000.0, 75.0, 50.0, 'Processing fee $75 instead of $50 (0.05 per transaction)', '2024-01-15'),
        ('SCB-VISA-2023-002', 'SC Bank', 'Interchange Fee', 10000.0, 200.0, 175.0, 'Interchange 2.0% instead of 1.75%', '2024-01-17'),
    ]
    
    # Combine all transactions
    all_transactions = dbs_transactions + boa_transactions + sc_transactions
    
    # Insert all transactions
    cursor.executemany('''
        INSERT INTO transactions 
        (contract_id, bank_name, transaction_type, amount, fee_charged, expected_fee, discrepancy, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', all_transactions)
    
    conn.commit()
    
    # Verify the data
    print('✅ Database updated successfully!')
    print('\n📊 Transaction Summary by Bank:')
    
    for bank in ['DBS Bank', 'Bank of America', 'SC Bank']:
        cursor.execute('''
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN discrepancy != '' THEN 1 END) as bad,
                   COUNT(CASE WHEN discrepancy = '' THEN 1 END) as good
            FROM transactions WHERE bank_name = ?
        ''', (bank,))
        
        total, bad, good = cursor.fetchone()
        print(f'  {bank}: {total} total ({good} good, {bad} with issues)')
    
    print('\n💰 Sample Transaction Data:')
    cursor.execute('''
        SELECT bank_name, transaction_type, fee_charged, expected_fee, 
               CASE WHEN discrepancy = '' THEN 'OK' ELSE 'ERROR' END as status
        FROM transactions 
        ORDER BY bank_name, transaction_date
        LIMIT 15
    ''')
    
    for row in cursor.fetchall():
        bank, trans_type, charged, expected, status = row
        print(f'  {bank[:3]}: {trans_type[:20]:<20} ${charged:>6.3f} (exp: ${expected:>6.3f}) [{status}]')
        
    conn.close()
    
except Exception as e:
    print(f'❌ Error updating database: {e}')