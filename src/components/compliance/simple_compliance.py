import os
import gradio as gr
import pandas as pd
from typing import List, Dict, Any
import json
from datetime import datetime, timedelta
import random


class SimpleComplianceMonitor:
    """
    Simple Contract Compliance Monitor
    Clean 3-section layout: Contract Info | Transactions | Discrepancies
    """
    
    def __init__(self):
        # Generate sample transaction data
        self.sample_transactions = self._create_sample_transactions()
        
    def _create_sample_transactions(self):
        """Create sample transaction data"""
        transactions = []
        merchants = ['DBS BANK', 'VISA', 'MASTERCARD']
        types = ['ATM_WITHDRAWAL', 'CARD_PAYMENT', 'BALANCE_INQUIRY']
        
        for i in range(30):
            tx_id = f"TXN_{datetime.now().strftime('%Y%m%d')}_{i:03d}"
            merchant = random.choice(merchants)
            tx_type = random.choice(types)
            amount = round(random.uniform(10, 1000), 2)
            
            # Create fees with some discrepancies
            if random.random() < 0.3:  # 30% have discrepancies
                processing_fee = 0.015  # Wrong fee
                network_fee = 0.000     # Missing fee
            else:
                processing_fee = 0.005  # Correct fee
                network_fee = 0.025     # Correct fee
            
            transactions.append({
                'Transaction ID': tx_id,
                'Merchant': merchant,
                'Type': tx_type,
                'Amount': f"${amount:.2f}",
                'Processing Fee': f"${processing_fee:.3f}",
                'Network Fee': f"${network_fee:.3f}",
                'Time': datetime.now().strftime('%H:%M:%S')
            })
        
        return transactions
    
    def get_contract_info(self, query=""):
        """Get contract information"""
        if query and 'fee' in query.lower():
            return """**💰 Fee Information**

**Standard Fees:**
- ATM Withdrawal: $0.005 processing + $0.025 network
- Card Payment: $0.150 processing + 1.2% interchange
- Balance Inquiry: $0.010 processing

**Discounted Rates (DBS Bank):**
- 50% discount on processing fees
- Fraud protection waived ($200 value)
- Volume discounts available"""
        
        elif query and 'visa' in query.lower():
            return """**💳 VISA Contract**

**Agreement:** DBS-VISA-2020-001
**Effective:** September 13, 2020
**Status:** Active

**Key Terms:**
- Processing: $0.005 per transaction
- Network access: $0.025 per transaction  
- Interchange: 1.2% + $0.10
- Settlement: T+1 processing"""
        
        else:
            return """**📋 Contract Overview**

**Active Contracts:**
- DBS-VISA-2020-001 (VISA Partnership)
- DBS-MC-2021-001 (MasterCard Agreement)  
- PULSE-DBS-2020-ADD (Network Access)

**Key Terms:**
- Processing fees: $0.005-0.015 per transaction
- Network fees: $0.025 per transaction
- Fraud protection: Waived for DBS Bank
- Settlement: T+1 business day processing"""
    
    def get_transactions_data(self):
        """Get transaction data as DataFrame"""
        return pd.DataFrame(self.sample_transactions)
    
    def check_discrepancies(self):
        """Simple discrepancy checking"""
        discrepancies = []
        
        for tx in self.sample_transactions:
            tx_id = tx['Transaction ID']
            processing_fee = float(tx['Processing Fee'].replace('$', ''))
            network_fee = float(tx['Network Fee'].replace('$', ''))
            
            # Check for overcharge
            if processing_fee > 0.005:
                discrepancies.append({
                    'id': tx_id,
                    'issue': 'Processing fee overcharge',
                    'expected': '$0.005',
                    'actual': f"${processing_fee:.3f}",
                    'severity': 'HIGH'
                })
            
            # Check for missing network fee
            if network_fee == 0.000:
                discrepancies.append({
                    'id': tx_id,
                    'issue': 'Missing network fee',
                    'expected': '$0.025',
                    'actual': '$0.000',
                    'severity': 'HIGH'
                })
        
        return discrepancies
    
    def format_discrepancies(self, discrepancies):
        """Format discrepancies for display"""
        if not discrepancies:
            return "✅ **No discrepancies found**\n\nAll transactions comply with contract terms."
        
        output = f"🚨 **{len(discrepancies)} Issues Found**\n\n"
        
        for disc in discrepancies[:5]:  # Show top 5
            severity_emoji = "🔴" if disc['severity'] == 'HIGH' else "🟡"
            output += f"{severity_emoji} **{disc['id']}**\n"
            output += f"   Issue: {disc['issue']}\n"
            output += f"   Expected: {disc['expected']} | Actual: {disc['actual']}\n\n"
        
        if len(discrepancies) > 5:
            output += f"... and {len(discrepancies) - 5} more issues"
        
        return output
    
    def create_interface(self):
        """Create the simple 3-section interface"""
        
        with gr.Row():
            # LEFT: Contract Information
            with gr.Column(scale=1):
                gr.Markdown("## 📋 Contract Info")
                
                contract_query = gr.Textbox(
                    label="Ask about contracts",
                    placeholder="e.g., 'fee information' or 'VISA terms'",
                    lines=1
                )
                
                query_btn = gr.Button("🔍 Query", variant="primary")
                
                contract_display = gr.Markdown(
                    value=self.get_contract_info(),
                    label="Contract Details"
                )
            
            # CENTER: Transactions
            with gr.Column(scale=2):
                gr.Markdown("## 💳 Live Transactions")
                
                refresh_btn = gr.Button("🔄 Refresh Transactions")
                
                transactions_table = gr.Dataframe(
                    value=self.get_transactions_data(),
                    label="Recent Transactions"
                )
            
            # RIGHT: Discrepancies
            with gr.Column(scale=1):
                gr.Markdown("## 🚨 Compliance Issues")
                
                check_btn = gr.Button("🔍 Check Compliance", variant="primary")
                
                discrepancies_display = gr.Markdown(
                    value="Click 'Check Compliance' to scan for issues...",
                    label="Flagged Issues"
                )
        
        # Event handlers
        def handle_query(query):
            return self.get_contract_info(query)
        
        def handle_refresh():
            # Generate new sample data
            self.sample_transactions = self._create_sample_transactions()
            return self.get_transactions_data()
        
        def handle_discrepancy_check():
            discrepancies = self.check_discrepancies()
            return self.format_discrepancies(discrepancies)
        
        # Wire up events
        query_btn.click(
            fn=handle_query,
            inputs=[contract_query],
            outputs=[contract_display]
        )
        
        refresh_btn.click(
            fn=handle_refresh,
            outputs=[transactions_table]
        )
        
        check_btn.click(
            fn=handle_discrepancy_check,
            outputs=[discrepancies_display]
        )
        
        return {
            'contract_display': contract_display,
            'transactions_table': transactions_table,
            'discrepancies_display': discrepancies_display
        }