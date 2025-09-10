#!/usr/bin/env python3
"""Quick script to check transaction data in database"""

from src.components.database.db_analyzer import DatabaseAnalyzer

db = DatabaseAnalyzer()

# Check total transactions
result = db.execute_safe_query('SELECT COUNT(*) as total FROM transactions')
if result['success']:
    print(f"✅ Total transactions in database: {result['data'][0]['total']}")
else:
    print(f"❌ Error: {result.get('error', 'Unknown')}")

# Check latest transactions
result = db.execute_safe_query('SELECT * FROM transactions ORDER BY created_at DESC LIMIT 5')
if result['success'] and result['data']:
    print(f"\n📊 Latest 5 transactions:")
    for txn in result['data']:
        print(f"  - {txn['transaction_id']}: {txn['merchant']} - ${txn['transaction_amount']}")
else:
    print("No transactions found or error occurred")

# Check today's transactions
result = db.execute_safe_query("SELECT COUNT(*) as today_count FROM transactions WHERE DATE(created_at) = CURRENT_DATE")
if result['success']:
    print(f"\n📅 Transactions created today: {result['data'][0]['today_count']}")