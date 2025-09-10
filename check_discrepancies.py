#!/usr/bin/env python3
"""
Check which transactions have discrepancies
Shows both what was applied vs what was expected
"""

from src.components.database.db_analyzer import DatabaseAnalyzer
import json
import pandas as pd

db = DatabaseAnalyzer()

# Query to compare actual vs expected fees
query = """
WITH transaction_fees AS (
    SELECT 
        t.transaction_id,
        t.merchant,
        t.transaction_type,
        t.transaction_amount,
        t.applied_fees::text as applied_fees,
        t.total_fees_applied,
        t.contract_id,
        t.created_at
    FROM transactions t
    ORDER BY t.created_at DESC
    LIMIT 20
),
expected_fees AS (
    SELECT 
        f.contract_id,
        f.merchant,
        f.transaction_type,
        f.fee_type,
        f.discounted_amount as expected_amount,
        f.is_waived
    FROM fees f
    WHERE f.effective_from <= CURRENT_DATE 
    AND (f.effective_to IS NULL OR f.effective_to >= CURRENT_DATE)
)
SELECT 
    tf.*,
    COALESCE(
        json_agg(
            json_build_object(
                'fee_type', ef.fee_type,
                'expected_amount', ef.expected_amount,
                'is_waived', ef.is_waived
            )
        ) FILTER (WHERE ef.fee_type IS NOT NULL),
        '[]'::json
    ) as expected_fees_json
FROM transaction_fees tf
LEFT JOIN expected_fees ef
    ON tf.contract_id = ef.contract_id
    AND tf.merchant = ef.merchant
    AND tf.transaction_type = ef.transaction_type
GROUP BY tf.transaction_id, tf.merchant, tf.transaction_type,
         tf.transaction_amount, tf.applied_fees, tf.total_fees_applied,
         tf.contract_id, tf.created_at
ORDER BY tf.created_at DESC
"""

result = db.execute_safe_query(query)

if result['success'] and result['data']:
    print("\n" + "="*80)
    print("TRANSACTION DISCREPANCY CHECK")
    print("="*80 + "\n")
    
    discrepancy_count = 0
    
    for row in result['data']:
        transaction_id = row['transaction_id']
        merchant = row['merchant']
        tx_type = row['transaction_type']
        
        # Parse fees
        applied_fees = json.loads(row['applied_fees']) if row['applied_fees'] else {}
        
        # Handle expected_fees_json - it might already be a list or dict
        expected_fees_json = row['expected_fees_json']
        if isinstance(expected_fees_json, str):
            expected_fees_list = json.loads(expected_fees_json) if expected_fees_json else []
        elif isinstance(expected_fees_json, (list, dict)):
            expected_fees_list = expected_fees_json if isinstance(expected_fees_json, list) else [expected_fees_json]
        else:
            expected_fees_list = []
        
        # Convert expected fees to dict
        expected_fees = {}
        for fee in expected_fees_list:
            if not fee.get('is_waived', False):
                expected_fees[fee['fee_type']] = float(fee['expected_amount'])
        
        # Check for discrepancies
        has_discrepancy = False
        discrepancies = []
        
        # Check for missing fees
        for fee_type, expected_amount in expected_fees.items():
            if fee_type not in applied_fees:
                discrepancies.append(f"  ❌ MISSING: {fee_type} (expected ${expected_amount:.4f})")
                has_discrepancy = True
        
        # Check for incorrect amounts
        for fee_type, applied_amount in applied_fees.items():
            applied_amount = float(applied_amount)
            if fee_type in expected_fees:
                expected_amount = expected_fees[fee_type]
                if abs(applied_amount - expected_amount) > 0.0001:
                    discrepancies.append(
                        f"  ⚠️  MISMATCH: {fee_type} - Applied: ${applied_amount:.4f}, Expected: ${expected_amount:.4f}"
                    )
                    has_discrepancy = True
            else:
                discrepancies.append(f"  🚫 UNEXPECTED: {fee_type} charged ${applied_amount:.4f}")
                has_discrepancy = True
        
        # Print transaction details
        if has_discrepancy:
            discrepancy_count += 1
            print(f"Transaction: {transaction_id}")
            print(f"  Merchant: {merchant}")
            print(f"  Type: {tx_type}")
            print(f"  Issues Found:")
            for disc in discrepancies:
                print(disc)
            print()
        else:
            print(f"✅ Transaction: {transaction_id} - COMPLIANT")
    
    print("\n" + "="*80)
    print(f"SUMMARY: {discrepancy_count} transactions with discrepancies out of {len(result['data'])} checked")
    print("="*80)
    
    # Create a simple report
    if discrepancy_count > 0:
        print("\nTo investigate further:")
        print("1. Run the Gradio app: python src/apps/main_app_full.py")
        print("2. Go to Contract Compliance tab")
        print("3. Use the right section to analyze discrepancies")
else:
    print("Error fetching data or no transactions found")