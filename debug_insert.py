#!/usr/bin/env python3
"""Debug transaction insertion"""

from src.components.database.db_analyzer import DatabaseAnalyzer
import json
from datetime import datetime, timedelta

db = DatabaseAnalyzer()

# First check if tables exist
result = db.execute_safe_query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
print("Tables in database:")
if result['success']:
    for row in result['data']:
        print(f"  - {row['table_name']}")
else:
    print(f"Error: {result.get('error')}")

# Try a simple insert
test_transaction = {
    'transaction_id': f'TEST_{datetime.now().strftime("%Y%m%d%H%M%S")}',
    'contract_id': 1,
    'merchant': 'DBS BANK',
    'transaction_type': 'ATM_WITHDRAWAL',
    'transaction_amount': 100.00,
    'currency': 'USD',
    'applied_fees': json.dumps({'processing_fee': 0.005, 'network_fee': 0.025}),
    'total_fees_applied': 0.030,
    'contract_party': 'DBS BANK',
    'processing_date': datetime.now().date(),
    'settlement_date': (datetime.now() + timedelta(days=1)).date(),
    'status': 'PROCESSED',
    'reference_number': 'REF_TEST123',
    'terminal_id': 'T12345',
    'location': 'NEW YORK NY'
}

# Build INSERT query
insert_query = f"""
INSERT INTO transactions (
    transaction_id, contract_id, merchant, transaction_type, transaction_amount,
    currency, applied_fees, total_fees_applied, contract_party, processing_date,
    settlement_date, status, reference_number, terminal_id, location
) VALUES (
    '{test_transaction['transaction_id']}', {test_transaction['contract_id']}, '{test_transaction['merchant']}', 
    '{test_transaction['transaction_type']}', {test_transaction['transaction_amount']},
    '{test_transaction['currency']}', '{test_transaction['applied_fees']}', {test_transaction['total_fees_applied']}, 
    '{test_transaction['contract_party']}', '{test_transaction['processing_date']}',
    '{test_transaction['settlement_date']}', '{test_transaction['status']}', '{test_transaction['reference_number']}', 
    '{test_transaction['terminal_id']}', '{test_transaction['location']}'
)
ON CONFLICT (transaction_id) DO NOTHING
"""

print("\nTrying to insert test transaction...")
result = db.execute_safe_query(insert_query)
if result['success']:
    print("✅ Insert successful!")
    print(f"Result: {result}")
else:
    print(f"❌ Insert failed: {result.get('error')}")

# Check if it was inserted
check_query = f"SELECT * FROM transactions WHERE transaction_id = '{test_transaction['transaction_id']}'"
result = db.execute_safe_query(check_query)
if result['success'] and result['data']:
    print(f"✅ Transaction found in database: {result['data'][0]['transaction_id']}")
else:
    print("❌ Transaction not found after insert")