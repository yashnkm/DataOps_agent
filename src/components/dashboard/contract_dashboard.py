import os
import sqlite3
import pandas as pd
import gradio as gr
from typing import Dict, List, Tuple, Any
from datetime import datetime

class ContractDashboard:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "dashboard_contracts.db")
        self.contracts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "contracts")
        
        # Contract file mapping
        self.contract_files = {
            "DBS Bank": "DBS_Bank_VISA_Contract_2020.txt",
            "Bank of America": "Bank_of_America_VISA_Contract_2025.txt", 
            "SC Bank": "SC_Bank_VISA_Contract_2023.txt"
        }
        
        # Initialize components
        self.left_components = {}
        self.center_components = {}
        self.right_components = {}
    
    def get_contract_list(self) -> List[str]:
        """Get list of available contracts"""
        return list(self.contract_files.keys())
    
    def load_contract_content(self, bank_name: str) -> str:
        """Load contract content from file"""
        if not bank_name:
            return "Please select a contract"
        
        try:
            file_path = os.path.join(self.contracts_dir, self.contract_files[bank_name])
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error loading contract: {str(e)}"
    
    def get_contract_billing_info(self, bank_name: str) -> str:
        """Extract and format billing information from contract"""
        if not bank_name:
            return "Please select a contract"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT contract_id, effective_date, standard_transaction_fee, 
                       fixed_fee_component, us_issuer_atm_fee, network_security_fee,
                       monthly_service_charge, annual_fee, interchange_fee_percent
                FROM contracts WHERE bank_name = ?
            ''', (bank_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                contract_id, date, std_fee, fixed_fee, atm_fee, network_fee, monthly_fee, annual_fee, interchange = result
                
                billing_info = f"""## 📋 **{bank_name} Contract Billing Information**

**Contract ID:** `{contract_id}`
**Effective Date:** {date}

### 💰 **Fee Structure:**

| Fee Type | Amount |
|----------|--------|
| Standard Transaction Fee | ${std_fee:+.3f} |
| Fixed Fee Component | ${fixed_fee:+.3f} |
| US Issuer ATM Fee | ${atm_fee:+.3f} |
| Network Security Fee | ${network_fee:.2f} |
| Monthly Service Charge | ${monthly_fee:.2f} |
| Annual Fee | ${annual_fee:.2f} |
| Interchange Fee | {interchange:.2f}% |

### 📊 **Fee Summary:**
- **Discount Fees:** {3 if std_fee < 0 or fixed_fee < 0 or atm_fee < 0 else 0} items
- **Fixed Charges:** {1 if network_fee > 0 else 0} + {1 if monthly_fee > 0 else 0} + {1 if annual_fee > 0 else 0} items
- **Variable Charges:** {1 if interchange > 0 else 0} items
"""
                return billing_info
            else:
                return f"❌ No billing information found for {bank_name}"
                
        except Exception as e:
            return f"❌ Error loading billing info: {str(e)}"
    
    def get_transaction_data(self, bank_name: str) -> pd.DataFrame:
        """Get transaction data with errors from database"""
        if not bank_name:
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            df = pd.read_sql_query('''
                SELECT transaction_type, amount, fee_charged, expected_fee, 
                       discrepancy, transaction_date
                FROM transactions 
                WHERE bank_name = ?
                ORDER BY transaction_date DESC
            ''', conn, params=(bank_name,))
            
            conn.close()
            
            # Format the data for better display
            if not df.empty:
                df['amount'] = df['amount'].apply(lambda x: f"${x:.2f}")
                df['fee_charged'] = df['fee_charged'].apply(lambda x: f"${x:.3f}")
                df['expected_fee'] = df['expected_fee'].apply(lambda x: f"${x:.3f}")
                df.columns = ['Transaction Type', 'Amount', 'Fee Charged', 'Expected Fee', 'Discrepancy', 'Date']
            
            return df
            
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return pd.DataFrame()
    
    def get_transaction_summary(self, bank_name: str) -> str:
        """Get simple transaction header for the selected bank"""
        if not bank_name:
            return "Please select a contract"
        
        return f"## 🗄️ **{bank_name} - Transaction Records**"
    
    def generate_fake_ai_discrepancy_analysis(self, bank_name: str) -> Tuple[str, pd.DataFrame]:
        """Generate fake AI-powered discrepancy analysis"""
        if not bank_name:
            return "Please select a contract", pd.DataFrame()
        
        # Fake AI analysis based on the bank
        ai_analyses = {
            "DBS Bank": {
                "summary": """## 🤖 **AI Discrepancy Analysis - DBS Bank**

**Key Findings:**
- ❌ **Standard Transaction Fee Mismatch**: Expected discount of $0.005, but charged $0.01
- ❌ **ATM Fee Error**: Expected discount of $0.15, but charged $0.20  
- 📈 **Impact**: Customer overcharged by $0.365 across 2 transactions

### 🎯 **Root Cause Analysis:**
1. **Fee calculation logic** appears inverted (charging instead of discounting)
2. **Contract amendment** from Sept 2020 may not be implemented in billing system
3. **Recommendation**: Update billing configuration to reflect contract terms""",
                "details": pd.DataFrame({
                    'Issue Type': ['Standard Transaction Fee', 'ATM Fee Discount'],
                    'Contract Amount': ['-$0.005', '-$0.150'],
                    'Charged Amount': ['$0.010', '$0.200'], 
                    'Variance': ['+$0.015', '+$0.350'],
                    'Confidence': ['98%', '96%'],
                    'Priority': ['High', 'Critical']
                })
            },
            "Bank of America": {
                "summary": """## 🤖 **AI Discrepancy Analysis - Bank of America**

**Key Findings:**
- ❌ **Standard Transaction Fee**: Expected discount of $0.001, but charged $0.005
- ❌ **Monthly Service Charge**: Expected $50, but charged $75
- 📈 **Impact**: Customer overcharged by $25.004 per month

### 🎯 **Root Cause Analysis:**
1. **Contract amendment** dated March 2025 not reflected in billing
2. **Service charge multiplier** seems to be using old rates (1.5x)
3. **Recommendation**: Verify March 2025 amendment implementation""",
                "details": pd.DataFrame({
                    'Issue Type': ['Standard Transaction Fee', 'Monthly Service Charge'],
                    'Contract Amount': ['-$0.001', '$50.00'],
                    'Charged Amount': ['$0.005', '$75.00'],
                    'Variance': ['+$0.006', '+$25.00'],
                    'Confidence': ['92%', '94%'],
                    'Priority': ['Medium', 'High']
                })
            },
            "SC Bank": {
                "summary": """## 🤖 **AI Discrepancy Analysis - SC Bank**

**Key Findings:**
- ❌ **Transaction Processing Fee**: Expected $50 (0.05 per 1000 transactions), but charged $75
- ❌ **Interchange Fee**: Expected 1.75%, but charged 2.0%
- 📈 **Impact**: Customer overcharged by $50 on processing + $25 on interchange

### 🎯 **Root Cause Analysis:**
1. **Processing fee calculation** using wrong multiplier (1.5x instead of 1.0x)
2. **Interchange rate** appears to be using standard 2% instead of negotiated 1.75%
3. **Recommendation**: Audit fee calculation algorithms for SC Bank contract""",
                "details": pd.DataFrame({
                    'Issue Type': ['Transaction Processing', 'Interchange Fee Rate'],
                    'Contract Amount': ['$50.00', '1.75%'],
                    'Charged Amount': ['$75.00', '2.00%'],
                    'Variance': ['+$25.00', '+0.25%'],
                    'Confidence': ['95%', '93%'],
                    'Priority': ['High', 'High']
                })
            }
        }
        
        analysis = ai_analyses.get(bank_name, {
            "summary": f"No AI analysis available for {bank_name}",
            "details": pd.DataFrame()
        })
        
        return analysis["summary"], analysis["details"]
    
    def create_left_section_interface(self):
        """Create the left section - Contract Viewer"""
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Contract Information")
            gr.Markdown("")  # Spacing
            
            # Contract selection dropdown
            self.left_components['contract_dropdown'] = gr.Dropdown(
                label="Select Contract",
                choices=self.get_contract_list(),
                value=None,
                interactive=True
            )
            
            gr.Markdown("")  # Spacing
            
            # Contract billing information display
            self.left_components['billing_info'] = gr.Markdown(
                value="Please select a contract to view billing information",
                label="Contract Billing Details"
            )
            
            gr.Markdown("")  # Spacing
            
            # Contract actions
            with gr.Row():
                self.left_components['refresh_btn'] = gr.Button("🔄 Refresh", variant="secondary", scale=1)
                self.left_components['view_contract_btn'] = gr.Button("📄 View Full Contract", variant="primary", scale=2)
            
            # Full contract content (collapsible)
            self.left_components['contract_content'] = gr.Textbox(
                label="Full Contract Content",
                lines=8,
                interactive=False,
                visible=False
            )
        
        # Event handlers for left section
        self.left_components['contract_dropdown'].change(
            fn=self._on_contract_selection_change,
            inputs=[self.left_components['contract_dropdown']],
            outputs=[
                self.left_components['billing_info'],
                self.left_components['contract_content']
            ]
        )
        
        self.left_components['view_contract_btn'].click(
            fn=self._toggle_contract_view,
            inputs=[self.left_components['contract_dropdown']],
            outputs=[self.left_components['contract_content']]
        )
        
        self.left_components['refresh_btn'].click(
            fn=self._refresh_contract_data,
            inputs=[self.left_components['contract_dropdown']],
            outputs=[self.left_components['billing_info']]
        )
    
    def create_center_section_interface(self):
        """Create the center section - Database Transactions"""
        with gr.Column(scale=1):
            gr.Markdown("### 🗄️ Transaction Records")
            gr.Markdown("")  # Spacing
            
            # Transaction summary header
            self.center_components['transaction_summary'] = gr.Markdown(
                value="Please select a contract to view transactions"
            )
            
            gr.Markdown("")  # Spacing
            
            # Transaction data table with better sizing
            self.center_components['transaction_table'] = gr.Dataframe(
                interactive=False,
                wrap=True
            )
            
            gr.Markdown("")  # Spacing
            
            # Transaction actions
            with gr.Row():
                self.center_components['refresh_transactions_btn'] = gr.Button("🔄 Refresh Data", variant="secondary")
                self.center_components['export_btn'] = gr.Button("📊 Export CSV", variant="primary")
    
    def create_right_section_interface(self):
        """Create the right section - AI Discrepancy Detection"""
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Discrepancy Analysis")
            gr.Markdown("")  # Spacing
            
            # AI analysis results
            self.right_components['ai_analysis'] = gr.Markdown(
                value="Please select a contract to view AI analysis"
            )
            
            gr.Markdown("")  # Spacing
            
            # AI detailed findings with better sizing
            self.right_components['ai_details_table'] = gr.Dataframe(
                label="Detailed Findings",
                interactive=False,
                wrap=True
            )
            
            # AI actions - removed buttons, auto-display analysis
    
    def create_full_dashboard_interface(self):
        """Create the complete 3-section dashboard"""
        with gr.Row():
            # LEFT SECTION: Contract Information
            self.create_left_section_interface()
            
            # CENTER SECTION: Transaction Records  
            self.create_center_section_interface()
            
            # RIGHT SECTION: AI Analysis
            self.create_right_section_interface()
        
        # Connect center and right sections to contract selection
        if 'contract_dropdown' in self.left_components:
            self.left_components['contract_dropdown'].change(
                fn=self._update_all_sections,
                inputs=[self.left_components['contract_dropdown']],
                outputs=[
                    self.center_components['transaction_summary'],
                    self.center_components['transaction_table'],
                    self.right_components['ai_analysis'], 
                    self.right_components['ai_details_table']
                ]
            )
    
    def _on_contract_selection_change(self, bank_name: str) -> Tuple[str, str]:
        """Handle contract selection change"""
        billing_info = self.get_contract_billing_info(bank_name)
        contract_content = self.load_contract_content(bank_name) if bank_name else ""
        return billing_info, contract_content
    
    def _toggle_contract_view(self, bank_name: str) -> gr.update:
        """Toggle contract content visibility"""
        return gr.update(visible=True)
    
    def _refresh_contract_data(self, bank_name: str) -> str:
        """Refresh contract billing information"""
        return self.get_contract_billing_info(bank_name)
    
    def _update_all_sections(self, bank_name: str) -> Tuple[str, pd.DataFrame, str, pd.DataFrame]:
        """Update center and right sections when contract changes"""
        # Update transaction section
        transaction_summary = self.get_transaction_summary(bank_name)
        transaction_data = self.get_transaction_data(bank_name)
        
        # Update AI analysis section
        ai_analysis, ai_details = self.generate_fake_ai_discrepancy_analysis(bank_name)
        
        return transaction_summary, transaction_data, ai_analysis, ai_details