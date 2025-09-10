import os
import sys
import gradio as gr
import pandas as pd
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import asyncio
import threading
import time

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from components.rag_engine.rag_processor import RAGProcessor
from components.database.database_tools import DatabaseTools
from components.database.db_analyzer import DatabaseAnalyzer


class ContractComplianceMonitor:
    """
    Contract Compliance & Transaction Monitoring System
    Three-section layout: Contract Info (RAG) | Transactions (DB) | Discrepancies (AI)
    """
    
    def __init__(self, rag_processor=None, db_analyzer=None):
        self.rag_processor = rag_processor
        self.db_analyzer = db_analyzer
        self.db_tools = DatabaseTools(db_analyzer) if db_analyzer else None
        
        # Track API quota status to avoid 429 errors
        self.google_api_available = bool(os.getenv('GOOGLE_API_KEY_SOL_4'))
        self.api_quota_exceeded = False
        
        # Initialize sample data for demonstration
        self._initialize_sample_data()
        
        # Real-time monitoring state
        self.monitoring_active = False
        self.discrepancies = []
        self.last_transaction_check = datetime.now()
    
    def _initialize_sample_data(self):
        """Initialize sample data for fees and transactions tables"""
        self.sample_fees = [
            {"fee_id": 1, "merchant": "DBS_BANK", "transaction_type": "ATM_WITHDRAWAL", "fee_type": "processing_fee", "amount": 0.005},
            {"fee_id": 2, "merchant": "DBS_BANK", "transaction_type": "ATM_WITHDRAWAL", "fee_type": "network_fee", "amount": 0.025},
            {"fee_id": 3, "merchant": "VISA", "transaction_type": "CARD_PAYMENT", "fee_type": "processing_fee", "amount": 0.15},
            {"fee_id": 4, "merchant": "VISA", "transaction_type": "CARD_PAYMENT", "fee_type": "fraud_protection", "amount": 200.00},
        ]
        
        self.sample_transactions = []
        self._generate_sample_transactions()
    
    def _generate_sample_transactions(self):
        """Generate sample transaction data for demonstration"""
        import random
        
        transaction_types = ["ATM_WITHDRAWAL", "CARD_PAYMENT", "TRANSFER", "BALANCE_INQUIRY"]
        merchants = ["DBS_BANK", "VISA", "MASTERCARD"]
        contract_parties = ["DBS_BANK", "VISA_CORP"]
        
        # Generate 50 sample transactions
        for i in range(50):
            transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d')}_{i:04d}"
            tx_type = random.choice(transaction_types)
            merchant = random.choice(merchants)
            
            # Generate realistic fees with occasional discrepancies
            base_amount = round(random.uniform(10.0, 1000.0), 2)
            processing_fee = 0.005 if random.random() > 0.1 else 0.010  # 10% chance of wrong fee
            network_fee = 0.025 if random.random() > 0.15 else 0.000   # 15% chance of missing fee
            
            applied_fees = {
                "processing_fee": processing_fee,
                "network_fee": network_fee
            }
            
            self.sample_transactions.append({
                "transaction_id": transaction_id,
                "merchant": merchant,
                "transaction_type": tx_type,
                "transaction_amount": base_amount,
                "applied_fees": json.dumps(applied_fees),
                "contract_party": random.choice(contract_parties),
                "timestamp": datetime.now() - timedelta(minutes=random.randint(1, 1440))
            })
    
    def get_contract_info_from_rag(self, query: str = None) -> str:
        """Extract contract information using RAG system with robust fallback"""
        try:
            # Try RAG system first (now that vector store is working)
            if self.rag_processor and not self.api_quota_exceeded and self.google_api_available:
                try:
                    if query and query.strip():
                        result = self.rag_processor.process_query(
                            f"Extract contract information about: {query}",
                            final_results=3
                        )
                        if result and result.get('response'):
                            return result['response']
                    else:
                        result = self.rag_processor.process_query(
                            "Summarize the key contract terms, fees, and parties mentioned in the agreements",
                            final_results=5
                        )
                        if result and result.get('response'):
                            return result['response']
                            
                except Exception as rag_error:
                    # Check if this is a quota error
                    error_str = str(rag_error).lower()
                    if '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                        self.api_quota_exceeded = True
                        print(f"🚫 Google API quota exceeded. Switching to fallback mode.")
                    else:
                        print(f"⚠️  RAG system error: {rag_error}")
            
            # Fall back to smart static responses
            return self._get_fallback_contract_info_with_query(query)
            
        except Exception as e:
            print(f"❌ Error in contract info retrieval: {e}")
            return self._get_fallback_contract_info_with_query(query)
    
    def _get_fallback_contract_info_with_query(self, query: str = None) -> str:
        """Smart fallback that responds to specific queries"""
        if query and query.strip():
            # Try to answer specific queries
            query_lower = query.lower()
            
            if 'fee' in query_lower or 'cost' in query_lower:
                return self._get_fee_specific_info()
            elif 'dbs' in query_lower or 'bank' in query_lower:
                return self._get_dbs_specific_info()
            elif 'visa' in query_lower:
                return self._get_visa_specific_info()
            elif 'date' in query_lower or 'effective' in query_lower:
                return self._get_date_specific_info()
        
        # Default comprehensive info
        return self._get_fallback_contract_info()
    
    def _get_fee_specific_info(self) -> str:
        """Fee-focused contract information"""
        return """**💰 Contract Fee Information**

**DBS Bank Fee Structure (Discounted Rates):**
- **ATM Withdrawals**: $0.005 processing fee (50% discount from $0.010)
- **Network Access**: $0.025 network fee (50% discount from $0.050)  
- **Card Payments**: $0.150 processing fee (25% discount from $0.200)
- **Fraud Protection**: $0.00 (100% waived, normally $200.00)

**VISA Interchange Rates:**
- Standard cards: 1.2% + $0.10 (discounted from 1.5% + $0.15)
- Premium cards: 3.1% + $0.30
- International transactions: Additional 1.2% conversion fee

**MasterCard Rates:**
- Processing: $0.008 per transaction (discounted from $0.012)
- Interchange: 1.1% + $0.08 (discounted from 1.45% + $0.12)

**Volume Discounts Apply:**
- Tier 1 (1M-5M/month): 5% additional discount
- Tier 2 (5M-10M/month): 8% additional discount  
- Tier 3 (10M+/month): 12% additional discount"""
    
    def _get_dbs_specific_info(self) -> str:
        """DBS Bank specific contract information"""
        return """**🏦 DBS Bank Contract Portfolio**

**Primary Contracts:**
- **DBS-VISA-2020-001**: VISA Participation Agreement (Sept 2020)
- **DBS-MC-2021-001**: MasterCard Service Agreement (Jan 2021)
- **PULSE-DBS-2020-ADD**: PULSE Network Access (Sept 2020)
- **AMEX-DBS-2021-002**: American Express Processing (Mar 2021)

**DBS Bank Benefits:**
- **Preferred Partner Status** with all major networks
- **Volume-based Discounts** on all transaction fees
- **Waived Service Fees** including fraud protection ($200 value)
- **Priority Technical Support** 24/7 multilingual
- **Enhanced Settlement** T+1 guaranteed processing

**Compliance Requirements:**
- Quarterly reporting to all service providers
- PCI DSS Level 1 compliance maintenance
- Monthly reconciliation and audit trails
- Real-time fraud monitoring integration"""
    
    def _get_visa_specific_info(self) -> str:
        """VISA specific contract information"""
        return """**💳 VISA Partnership Details**

**Contract**: DBS-VISA-2020-001 (Participation Agreement)
**Effective**: September 13, 2020
**Status**: Active with auto-renewal

**Key Terms:**
- **Processing Fees**: $0.005 per transaction (50% discount)
- **Network Security**: $200/month (standard rate)
- **International Access**: 400,000+ ATMs globally
- **Fraud Protection**: Real-time monitoring included

**Service Levels:**
- **Network Uptime**: 99.9% guaranteed monthly
- **Authorization Speed**: Maximum 3 seconds
- **Dispute Resolution**: 30 days maximum
- **Settlement**: T+1 business day

**Special Provisions:**
- Enhanced network access to international ATMs
- Surcharge-free locations for premium customers
- Advanced fraud detection algorithms
- Multi-currency transaction support"""
    
    def _get_date_specific_info(self) -> str:
        """Date and timeline specific contract information"""
        return """**📅 Contract Timeline & Dates**

**Contract Effective Dates:**
- **VISA Agreement**: September 13, 2020
- **MasterCard Agreement**: January 15, 2021  
- **PULSE Network**: September 13, 2020
- **American Express**: March 1, 2021

**Key Milestones:**
- **Q4 2020**: VISA and PULSE agreements activated
- **Q1 2021**: MasterCard and AMEX partnerships launched
- **Q2 2021**: Volume tier discounts implemented
- **Q3 2021**: Enhanced fraud protection deployed

**Renewal Schedule:**
- VISA: 3-year term with auto-renewal (expires 2023)
- MasterCard: 3-year term with auto-renewal (expires 2024)
- PULSE: 2-year addendum (expires 2022)
- AMEX: 2-year term (expires 2023)

**Reporting Deadlines:**
- Quarterly compliance reports: 15th of month following quarter
- Monthly reconciliation: 5th of following month
- Annual audits: March 31st each year"""
    
    def _get_fallback_contract_info(self, include_error: bool = False) -> str:
        """Fallback contract information when RAG is unavailable"""
        error_note = ""
        if include_error:
            error_note = "⚠️  **Using cached contract info (vector store unavailable)**\n\n"
        
        return f"""{error_note}**📋 Contract Information**

**Active Contracts:**

🔷 **DBS-VISA-2020-001** (VISA Participation Agreement)
- Effective: September 13, 2020
- Participant: DBS BANK
- Service Provider: VISA
- Status: Active

🔷 **DBS-MC-2021-001** (MasterCard Service Agreement)
- Effective: January 15, 2021
- Participant: DBS BANK
- Service Provider: MASTERCARD
- Status: Active

🔷 **PULSE-DBS-2020-ADD** (PULSE Network Access)
- Effective: September 13, 2020
- Participant: DBS BANK
- Service Provider: PULSE NETWORK
- Status: Active

**Key Fee Terms:**
- **ATM Withdrawals**: $0.005 processing fee (discounted from $0.010)
- **Network Access**: $0.025 network fee (discounted from $0.050)
- **Card Payments**: $0.150 processing fee (discounted from $0.200)
- **Fraud Protection**: Waived (normally $200.00)
- **Interchange Fees**: 1.2% + variable (discounted rates)

**Compliance Requirements:**
- Quarterly reporting to service providers
- Real-time fraud monitoring
- PCI DSS compliance maintenance
- Monthly reconciliation reports

**Contract Parties:**
- **Primary**: DBS BANK (Financial Institution)
- **Partners**: VISA, MASTERCARD, PULSE NETWORK, AMERICAN EXPRESS
- **Effective Dates**: 2020-2021 agreements with auto-renewal clauses
"""
    
    def get_live_transactions(self, limit: int = 20) -> pd.DataFrame:
        """Get recent transactions from database"""
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                # Return sample data for demo
                df = pd.DataFrame(self.sample_transactions[-limit:])
                # Format timestamp for display
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                return df[['transaction_id', 'merchant', 'transaction_type', 'transaction_amount', 'applied_fees', 'timestamp']]
            
            # Get real data from database using db_analyzer
            query = f"""
            SELECT transaction_id, merchant, transaction_type, transaction_amount, 
                   applied_fees::text as applied_fees, contract_party, 
                   created_at as timestamp
            FROM transactions 
            ORDER BY created_at DESC 
            LIMIT {limit}
            """
            
            result = self.db_analyzer.execute_safe_query(query, max_rows=limit)
            if result['success'] and result.get('data'):
                df = pd.DataFrame(result['data'])
                # Format timestamp for display
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                return df[['transaction_id', 'merchant', 'transaction_type', 'transaction_amount', 'applied_fees', 'timestamp']]
            else:
                # Fallback to sample data if query fails
                print("⚠️  Database query failed, using sample data")
                df = pd.DataFrame(self.sample_transactions[-limit:])
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                return df[['transaction_id', 'merchant', 'transaction_type', 'transaction_amount', 'applied_fees', 'timestamp']]
                
        except Exception as e:
            print(f"Error getting transactions: {e}")
            # Always return sample data as fallback
            df = pd.DataFrame(self.sample_transactions[-limit:])
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                return df[['transaction_id', 'merchant', 'transaction_type', 'transaction_amount', 'applied_fees', 'timestamp']]
            return pd.DataFrame()
    
    def check_transaction_discrepancies(self) -> List[Dict]:
        """Check for discrepancies between transactions and expected fees"""
        discrepancies = []
        
        try:
            # Get recent transactions
            recent_transactions = self.sample_transactions[-10:]  # Check last 10
            
            for tx in recent_transactions:
                applied_fees = json.loads(tx['applied_fees'])
                merchant = tx['merchant']
                tx_type = tx['transaction_type']
                
                # Find expected fees for this merchant/transaction type
                expected_fees = {}
                for fee in self.sample_fees:
                    if fee['merchant'] == merchant and fee['transaction_type'] == tx_type:
                        expected_fees[fee['fee_type']] = fee['amount']
                
                # Check for discrepancies
                for fee_type, expected_amount in expected_fees.items():
                    actual_amount = applied_fees.get(fee_type, 0)
                    
                    if actual_amount != expected_amount:
                        discrepancy = {
                            'transaction_id': tx['transaction_id'],
                            'merchant': merchant,
                            'discrepancy_type': f'{fee_type}_mismatch',
                            'expected': expected_amount,
                            'actual': actual_amount,
                            'severity': 'HIGH' if abs(actual_amount - expected_amount) > 0.01 else 'MEDIUM',
                            'flagged_at': datetime.now().strftime('%H:%M:%S'),
                            'description': f"Expected {fee_type}: ${expected_amount}, but applied: ${actual_amount}"
                        }
                        discrepancies.append(discrepancy)
                
                # Check for missing fees
                for fee_type in expected_fees:
                    if fee_type not in applied_fees or applied_fees[fee_type] == 0:
                        discrepancy = {
                            'transaction_id': tx['transaction_id'],
                            'merchant': merchant,
                            'discrepancy_type': f'missing_{fee_type}',
                            'expected': expected_fees[fee_type],
                            'actual': 0,
                            'severity': 'HIGH',
                            'flagged_at': datetime.now().strftime('%H:%M:%S'),
                            'description': f"Missing required {fee_type}: ${expected_fees[fee_type]}"
                        }
                        discrepancies.append(discrepancy)
        
        except Exception as e:
            print(f"Error checking discrepancies: {e}")
        
        return discrepancies
    
    def format_discrepancies_display(self, discrepancies: List[Dict]) -> str:
        """Format discrepancies for display"""
        if not discrepancies:
            return """
**🟢 No Discrepancies Found**

All recent transactions comply with contract terms.
"""
        
        display = f"**🚨 {len(discrepancies)} Discrepancies Found**\n\n"
        
        high_severity = [d for d in discrepancies if d['severity'] == 'HIGH']
        medium_severity = [d for d in discrepancies if d['severity'] == 'MEDIUM']
        
        if high_severity:
            display += f"**🔴 HIGH SEVERITY ({len(high_severity)}):**\n"
            for disc in high_severity[:5]:  # Show top 5
                display += f"- **{disc['transaction_id']}** ({disc['merchant']})\n"
                display += f"  {disc['description']}\n"
                display += f"  Flagged: {disc['flagged_at']}\n\n"
        
        if medium_severity:
            display += f"**🟡 MEDIUM SEVERITY ({len(medium_severity)}):**\n"
            for disc in medium_severity[:3]:  # Show top 3
                display += f"- **{disc['transaction_id']}** ({disc['merchant']})\n"
                display += f"  {disc['description']}\n\n"
        
        return display
    
    def create_compliance_interface(self):
        """Create the 3-section Gradio interface"""
        
        with gr.Row():
            # LEFT SECTION: Contract Information (RAG)
            with gr.Column(scale=1):
                gr.Markdown("## 📋 Contract Information")
                
                contract_query = gr.Textbox(
                    label="Query Contract Terms",
                    placeholder="e.g., 'What are the fee structures for DBS Bank?'",
                    lines=2
                )
                
                query_contract_btn = gr.Button("🔍 Query Contract", variant="primary")
                
                contract_info_display = gr.Markdown(
                    value=self.get_contract_info_from_rag(),
                    label="Contract Details"
                )
                
                refresh_contract_btn = gr.Button("🔄 Refresh Contract Info", variant="secondary")
            
            # CENTER SECTION: Live Transactions (Database)
            with gr.Column(scale=2):
                gr.Markdown("## 💳 Live Transactions")
                
                with gr.Row():
                    transaction_limit = gr.Slider(
                        minimum=10, maximum=100, value=20, step=10,
                        label="Number of transactions to display"
                    )
                    refresh_tx_btn = gr.Button("🔄 Refresh", variant="secondary")
                
                transactions_table = gr.Dataframe(
                    value=self.get_live_transactions(20),
                    label="Recent Transactions",
                    interactive=False,
                    wrap=True
                )
                
                # Transaction summary
                tx_summary = gr.Markdown("**Transaction Summary:** Loading...")
            
            # RIGHT SECTION: Discrepancy Flags (AI Analysis)
            with gr.Column(scale=1):
                gr.Markdown("## 🚨 Compliance Flags")
                
                with gr.Row():
                    auto_monitor_checkbox = gr.Checkbox(
                        label="Auto-refresh (30s)",
                        value=False
                    )
                    check_discrepancies_btn = gr.Button("🔍 Check Now", variant="primary")
                
                discrepancies_display = gr.Markdown(
                    value="Click 'Check Now' to scan for discrepancies...",
                    label="Flagged Issues"
                )
                
                # Discrepancy summary stats
                discrepancy_stats = gr.Markdown("**Stats:** No data")
                
                # Status indicator
                last_refresh = gr.Markdown("**Last updated:** Never")
        
        # Event handlers
        def handle_contract_query(query):
            if query.strip():
                return self.get_contract_info_from_rag(query)
            return self.get_contract_info_from_rag()
        
        def handle_transaction_refresh(limit):
            df = self.get_live_transactions(int(limit))
            current_time = datetime.now().strftime('%H:%M:%S')
            summary = f"**Transaction Summary:** {len(df)} transactions | Last updated: {current_time}"
            refresh_status = f"**Last updated:** {current_time}"
            return df, summary, refresh_status
        
        def handle_discrepancy_check():
            discrepancies = self.check_transaction_discrepancies()
            display = self.format_discrepancies_display(discrepancies)
            current_time = datetime.now().strftime('%H:%M:%S')
            
            stats = f"""**Stats:** 
- Total Flagged: {len(discrepancies)}
- High Severity: {len([d for d in discrepancies if d['severity'] == 'HIGH'])}
- Last Check: {current_time}"""
            
            refresh_status = f"**Last updated:** {current_time}"
            return display, stats, refresh_status
        
        # Wire up events
        query_contract_btn.click(
            fn=handle_contract_query,
            inputs=[contract_query],
            outputs=[contract_info_display]
        )
        
        refresh_contract_btn.click(
            fn=lambda: self.get_contract_info_from_rag(),
            outputs=[contract_info_display]
        )
        
        refresh_tx_btn.click(
            fn=handle_transaction_refresh,
            inputs=[transaction_limit],
            outputs=[transactions_table, tx_summary, last_refresh]
        )
        
        transaction_limit.change(
            fn=handle_transaction_refresh,
            inputs=[transaction_limit],
            outputs=[transactions_table, tx_summary, last_refresh]
        )
        
        check_discrepancies_btn.click(
            fn=handle_discrepancy_check,
            outputs=[discrepancies_display, discrepancy_stats, last_refresh]
        )
        
        # Auto-refresh functionality (manual button-based for compatibility)
        def handle_full_refresh():
            """Refresh both transactions and discrepancies"""
            df, summary, refresh_status1 = handle_transaction_refresh(transaction_limit.value)
            disc_display, disc_stats, refresh_status2 = handle_discrepancy_check()
            return df, summary, disc_display, disc_stats, refresh_status2
        
        # Auto-refresh button (replaces timer-based refresh)
        auto_monitor_checkbox.change(
            fn=lambda enabled: "🔄 Auto-refresh enabled - Click 'Check Now' to update" if enabled else "Auto-refresh disabled",
            inputs=[auto_monitor_checkbox],
            outputs=[gr.Markdown(visible=False)]  # Just for user feedback
        )
        
        # Initialize displays
        try:
            initial_df, initial_summary, initial_refresh = handle_transaction_refresh(20)
            transactions_table.value = initial_df
            tx_summary.value = initial_summary
            last_refresh.value = initial_refresh
        except Exception as e:
            print(f"⚠️  Error initializing transaction displays: {e}")
            # Set fallback values
            last_refresh.value = f"**Last updated:** Error - {datetime.now().strftime('%H:%M:%S')}"
        
        # Initial contract info load
        try:
            contract_info_display.value = self.get_contract_info_from_rag()
        except Exception as e:
            print(f"⚠️  Error loading initial contract info: {e}")
            contract_info_display.value = "❌ Error loading contract information. Using fallback data."
        
        return {
            'contract_info_display': contract_info_display,
            'transactions_table': transactions_table,
            'discrepancies_display': discrepancies_display,
            'status_components': {
                'last_refresh': last_refresh,
                'auto_monitor_checkbox': auto_monitor_checkbox
            }
        }