#!/usr/bin/env python3
"""
Transaction Data Generator with Discrepancies
Generates realistic transaction data with intentional compliance issues for testing
"""

import os
import sys
import random
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import signal
from typing import Dict, List, Any

# Add src to path for database components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from components.database.db_analyzer import DatabaseAnalyzer


class TransactionGenerator:
    """
    Generates realistic transaction data with built-in discrepancies for compliance testing
    """
    
    def __init__(self):
        self.db_analyzer = DatabaseAnalyzer()
        self.is_running = False
        self.transaction_count = 0
        
        # Transaction patterns and merchants
        self.merchants = [
            'DBS BANK', 'VISA', 'MASTERCARD', 'PULSE NETWORK', 'AMERICAN EXPRESS',
            'CITIBANK', 'WELLS FARGO', 'CHASE BANK', 'BOA'
        ]
        
        self.transaction_types = [
            'ATM_WITHDRAWAL', 'CARD_PAYMENT', 'INTERNATIONAL_TXN', 
            'BALANCE_INQUIRY', 'TRANSFER', 'CASH_ADVANCE'
        ]
        
        self.locations = [
            'NEW YORK NY', 'LOS ANGELES CA', 'CHICAGO IL', 'HOUSTON TX',
            'SINGAPORE SG', 'LONDON UK', 'TOKYO JP', 'SYDNEY AU'
        ]
        
        # Fee structures (expected values from database)
        self.expected_fees = {}
        self._load_expected_fees()
        
        # Discrepancy patterns (what percentage of each type of error to inject)
        self.discrepancy_rates = {
            'fee_overcharge': 0.08,      # 8% of transactions overcharged
            'fee_undercharge': 0.05,     # 5% of transactions undercharged  
            'missing_fee': 0.12,         # 12% missing required fees
            'extra_fee': 0.03,           # 3% have unexpected fees
            'wrong_fee_type': 0.04,      # 4% have wrong fee types applied
        }
        
    def _load_expected_fees(self):
        """Load expected fees from database"""
        try:
            if self.db_analyzer.connection_status == "connected":
                query = """
                SELECT contract_id, merchant, transaction_type, fee_type, 
                       discounted_amount, is_waived
                FROM fees 
                WHERE effective_from <= CURRENT_DATE 
                AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
                """
                
                result = self.db_analyzer.execute_safe_query(query)
                if result['success']:
                    for row in result['data']:
                        key = (row['merchant'], row['transaction_type'])
                        if key not in self.expected_fees:
                            self.expected_fees[key] = {}
                        
                        self.expected_fees[key][row['fee_type']] = {
                            'amount': float(row['discounted_amount']),
                            'waived': row['is_waived'],
                            'contract_id': row['contract_id']
                        }
        except Exception as e:
            print(f"⚠️  Could not load fees from database: {e}")
            # Fallback to hardcoded fees
            self._load_fallback_fees()
    
    def _load_fallback_fees(self):
        """Fallback fee structure if database is not available"""
        self.expected_fees = {
            ('DBS BANK', 'ATM_WITHDRAWAL'): {
                'processing_fee': {'amount': 0.005, 'waived': False, 'contract_id': 1},
                'network_fee': {'amount': 0.025, 'waived': False, 'contract_id': 1}
            },
            ('DBS BANK', 'CARD_PAYMENT'): {
                'processing_fee': {'amount': 0.150, 'waived': False, 'contract_id': 1},
                'fraud_protection_fee': {'amount': 0.000, 'waived': True, 'contract_id': 1}
            },
            ('VISA', 'CARD_PAYMENT'): {
                'interchange_fee': {'amount': 1.200, 'waived': False, 'contract_id': 1}
            },
            ('MASTERCARD', 'CARD_PAYMENT'): {
                'interchange_fee': {'amount': 1.100, 'waived': False, 'contract_id': 2}
            }
        }
    
    def generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = random.randint(1000, 9999)
        return f"TXN_{timestamp}_{random_suffix}"
    
    def get_base_transaction_amount(self, transaction_type: str) -> Decimal:
        """Generate realistic transaction amounts based on type"""
        amounts = {
            'ATM_WITHDRAWAL': (20.00, 500.00),
            'CARD_PAYMENT': (5.00, 2000.00),
            'INTERNATIONAL_TXN': (50.00, 5000.00),
            'BALANCE_INQUIRY': (0.00, 0.00),
            'TRANSFER': (100.00, 10000.00),
            'CASH_ADVANCE': (50.00, 1000.00)
        }
        
        min_amt, max_amt = amounts.get(transaction_type, (10.00, 1000.00))
        if min_amt == max_amt == 0.00:
            return Decimal('0.00')
        
        amount = random.uniform(min_amt, max_amt)
        return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_correct_fees(self, merchant: str, transaction_type: str) -> Dict[str, Decimal]:
        """Calculate what the fees SHOULD be according to contracts"""
        key = (merchant, transaction_type)
        correct_fees = {}
        
        if key in self.expected_fees:
            for fee_type, fee_info in self.expected_fees[key].items():
                if not fee_info['waived']:
                    correct_fees[fee_type] = Decimal(str(fee_info['amount']))
                # Waived fees are not included (should be 0 or absent)
        
        return correct_fees
    
    def inject_discrepancies(self, correct_fees: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """Inject various types of discrepancies into fees"""
        applied_fees = correct_fees.copy()
        discrepancy_injected = False
        
        for discrepancy_type, rate in self.discrepancy_rates.items():
            if random.random() < rate:
                discrepancy_injected = True
                
                if discrepancy_type == 'fee_overcharge' and applied_fees:
                    # Overcharge an existing fee
                    fee_to_modify = random.choice(list(applied_fees.keys()))
                    multiplier = random.uniform(1.5, 3.0)  # 50% to 200% overcharge
                    applied_fees[fee_to_modify] *= Decimal(str(multiplier)).quantize(Decimal('0.0001'))
                
                elif discrepancy_type == 'fee_undercharge' and applied_fees:
                    # Undercharge an existing fee
                    fee_to_modify = random.choice(list(applied_fees.keys()))
                    multiplier = random.uniform(0.3, 0.8)  # 20% to 70% undercharge
                    applied_fees[fee_to_modify] *= Decimal(str(multiplier)).quantize(Decimal('0.0001'))
                
                elif discrepancy_type == 'missing_fee' and applied_fees:
                    # Remove a required fee
                    fee_to_remove = random.choice(list(applied_fees.keys()))
                    del applied_fees[fee_to_remove]
                
                elif discrepancy_type == 'extra_fee':
                    # Add an unexpected fee
                    extra_fees = ['admin_fee', 'service_charge', 'convenience_fee', 'handling_fee']
                    extra_fee_type = random.choice(extra_fees)
                    extra_amount = Decimal(str(random.uniform(0.50, 5.00))).quantize(Decimal('0.01'))
                    applied_fees[extra_fee_type] = extra_amount
                
                elif discrepancy_type == 'wrong_fee_type' and applied_fees:
                    # Change fee type name but keep amount
                    if applied_fees:
                        old_fee = random.choice(list(applied_fees.keys()))
                        amount = applied_fees[old_fee]
                        del applied_fees[old_fee]
                        
                        wrong_names = ['misc_fee', 'other_charge', 'system_fee', 'legacy_fee']
                        new_fee_name = random.choice(wrong_names)
                        applied_fees[new_fee_name] = amount
                
                # Only inject one type of discrepancy per transaction
                break
        
        return applied_fees
    
    def generate_transaction(self) -> Dict[str, Any]:
        """Generate a single transaction with potential discrepancies"""
        transaction_id = self.generate_transaction_id()
        merchant = random.choice(self.merchants)
        transaction_type = random.choice(self.transaction_types)
        transaction_amount = self.get_base_transaction_amount(transaction_type)
        
        # Get contract ID for this merchant/type combination
        contract_id = 1  # Default
        key = (merchant, transaction_type)
        if key in self.expected_fees:
            fee_info = list(self.expected_fees[key].values())[0]
            contract_id = fee_info.get('contract_id', 1)
        
        # Calculate correct fees
        correct_fees = self.calculate_correct_fees(merchant, transaction_type)
        
        # Apply discrepancies with some probability
        should_have_discrepancy = random.random() < 0.25  # 25% of transactions have issues
        if should_have_discrepancy:
            applied_fees = self.inject_discrepancies(correct_fees)
        else:
            applied_fees = correct_fees
        
        # Calculate total fees
        total_fees = sum(applied_fees.values())
        
        # Create transaction record
        transaction = {
            'transaction_id': transaction_id,
            'contract_id': contract_id,
            'merchant': merchant,
            'transaction_type': transaction_type,
            'transaction_amount': float(transaction_amount),
            'currency': 'USD',
            'applied_fees': {k: float(v) for k, v in applied_fees.items()},
            'total_fees_applied': float(total_fees),
            'contract_party': merchant if merchant in ['DBS BANK'] else f"{merchant}_CORP",
            'processing_date': datetime.now().date(),
            'settlement_date': (datetime.now() + timedelta(days=1)).date(),
            'status': 'PROCESSED',
            'reference_number': f"REF_{random.randint(100000, 999999)}",
            'terminal_id': f"T{random.randint(10000, 99999)}",
            'location': random.choice(self.locations)
        }
        
        return transaction
    
    def insert_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Insert transaction into database"""
        try:
            if self.db_analyzer.connection_status != "connected":
                print(f"❌ Database not connected, cannot insert transaction {transaction['transaction_id']}")
                return False
            
            # Convert applied_fees to JSON string
            applied_fees_json = json.dumps(transaction['applied_fees'])
            
            # Use direct connection since execute_safe_query blocks INSERT
            from sqlalchemy import text
            
            insert_query = text("""
            INSERT INTO transactions (
                transaction_id, contract_id, merchant, transaction_type, transaction_amount,
                currency, applied_fees, total_fees_applied, contract_party, processing_date,
                settlement_date, status, reference_number, terminal_id, location
            ) VALUES (
                :transaction_id, :contract_id, :merchant, :transaction_type, :transaction_amount,
                :currency, :applied_fees, :total_fees_applied, :contract_party, :processing_date,
                :settlement_date, :status, :reference_number, :terminal_id, :location
            )
            ON CONFLICT (transaction_id) DO NOTHING
            """)
            
            with self.db_analyzer.engine.connect() as conn:
                result = conn.execute(insert_query, {
                    'transaction_id': transaction['transaction_id'],
                    'contract_id': transaction['contract_id'],
                    'merchant': transaction['merchant'],
                    'transaction_type': transaction['transaction_type'],
                    'transaction_amount': transaction['transaction_amount'],
                    'currency': transaction['currency'],
                    'applied_fees': applied_fees_json,
                    'total_fees_applied': transaction['total_fees_applied'],
                    'contract_party': transaction['contract_party'],
                    'processing_date': transaction['processing_date'],
                    'settlement_date': transaction['settlement_date'],
                    'status': transaction['status'],
                    'reference_number': transaction['reference_number'],
                    'terminal_id': transaction['terminal_id'],
                    'location': transaction['location']
                })
                conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error inserting transaction {transaction['transaction_id']}: {e}")
            return False
    
    def generate_batch_transactions(self, count: int = 10) -> List[Dict]:
        """Generate a batch of transactions"""
        transactions = []
        
        print(f"🔄 Generating {count} transactions...")
        
        for i in range(count):
            transaction = self.generate_transaction()
            transactions.append(transaction)
            
            # Insert into database
            success = self.insert_transaction(transaction)
            if success:
                self.transaction_count += 1
                if (i + 1) % 10 == 0:
                    print(f"✅ Generated {i + 1}/{count} transactions")
            else:
                print(f"❌ Failed to insert transaction {i + 1}")
        
        print(f"📊 Batch complete: {len(transactions)} transactions generated")
        return transactions
    
    def start_continuous_generation(self, transactions_per_minute: int = 60):
        """Start continuous transaction generation"""
        self.is_running = True
        interval = 60.0 / transactions_per_minute  # seconds between transactions
        
        print(f"🚀 Starting continuous generation: {transactions_per_minute} transactions/minute")
        print(f"   Interval: {interval:.2f} seconds between transactions")
        print("   Press Ctrl+C to stop")
        
        try:
            while self.is_running:
                transaction = self.generate_transaction()
                success = self.insert_transaction(transaction)
                
                if success:
                    self.transaction_count += 1
                    if self.transaction_count % 10 == 0:
                        print(f"📈 Generated {self.transaction_count} total transactions")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Stopping generation. Total transactions created: {self.transaction_count}")
            self.is_running = False
    
    def stop_generation(self):
        """Stop continuous generation"""
        self.is_running = False
    
    def get_transaction_summary(self) -> Dict[str, Any]:
        """Get summary of generated transactions"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(DISTINCT merchant) as unique_merchants,
                COUNT(DISTINCT transaction_type) as unique_types,
                AVG(transaction_amount) as avg_amount,
                SUM(total_fees_applied) as total_fees,
                MAX(created_at) as last_transaction
            FROM transactions
            WHERE DATE(created_at) = CURRENT_DATE
            """
            
            result = self.db_analyzer.execute_safe_query(query)
            if result['success'] and result['data']:
                return result['data'][0]
            
        except Exception as e:
            print(f"Error getting summary: {e}")
        
        return {
            'total_transactions': self.transaction_count,
            'unique_merchants': len(self.merchants),
            'unique_types': len(self.transaction_types),
            'avg_amount': 0,
            'total_fees': 0,
            'last_transaction': datetime.now()
        }


def main():
    """Main function to run transaction generation"""
    generator = TransactionGenerator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--continuous':
            # Continuous generation mode
            tpm = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            
            def signal_handler(signum, frame):
                print(f"\n🛑 Received signal {signum}, stopping...")
                generator.stop_generation()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            generator.start_continuous_generation(tpm)
            
        elif sys.argv[1] == '--batch':
            # Batch generation mode
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            transactions = generator.generate_batch_transactions(count)
            
            # Print summary
            summary = generator.get_transaction_summary()
            print(f"\n📊 Transaction Summary:")
            print(f"   Total transactions today: {summary['total_transactions']}")
            avg_amount = summary.get('avg_amount', 0)
            if avg_amount is not None:
                print(f"   Average amount: ${avg_amount:.2f}")
            else:
                print(f"   Average amount: $0.00")
            total_fees = summary.get('total_fees', 0)
            if total_fees is not None:
                print(f"   Total fees: ${total_fees:.2f}")
            else:
                print(f"   Total fees: $0.00")
            
        elif sys.argv[1] == '--setup-db':
            # Setup database tables
            print("🔧 Setting up database tables...")
            schema_file = os.path.join(os.path.dirname(__file__), '..', 'database', 'schemas', 'contract_compliance_schema.sql')
            
            if os.path.exists(schema_file):
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()
                
                result = generator.db_analyzer.execute_safe_query(schema_sql)
                if result['success']:
                    print("✅ Database tables created successfully")
                else:
                    print(f"❌ Database setup failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Schema file not found: {schema_file}")
    
    else:
        print("📚 Transaction Data Generator")
        print("Usage:")
        print("  python generate_transaction_data.py --setup-db")
        print("  python generate_transaction_data.py --batch [count]")
        print("  python generate_transaction_data.py --continuous [transactions_per_minute]")
        print()
        print("Examples:")
        print("  python generate_transaction_data.py --setup-db")
        print("  python generate_transaction_data.py --batch 100")
        print("  python generate_transaction_data.py --continuous 120")


if __name__ == "__main__":
    main()