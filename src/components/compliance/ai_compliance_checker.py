"""
AI-Powered Compliance Checker
Combines RAG contract knowledge with live transactions for intelligent discrepancy detection
"""

import os
import json
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class AIComplianceChecker:
    def __init__(self, vector_store=None, db_analyzer=None):
        """
        Initialize AI Compliance Checker
        
        Args:
            vector_store: Vector store with contract documents
            db_analyzer: Database analyzer for transaction queries
        """
        self.vector_store = vector_store
        self.db_analyzer = db_analyzer
        self.last_check_timestamp = None
        self.gemini_model = None
        
        # Configure Gemini
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def get_new_transactions(self, since_timestamp: Optional[datetime] = None) -> List[Dict]:
        """
        Fetch transactions added since last check
        
        Args:
            since_timestamp: Get transactions after this time
            
        Returns:
            List of new transaction records
        """
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                return []
            
            # Default to last 5 minutes if no timestamp
            if not since_timestamp:
                since_timestamp = datetime.now() - timedelta(minutes=5)
            
            query = f"""
            SELECT 
                t.transaction_id,
                t.contract_id,
                t.merchant,
                t.transaction_type,
                t.transaction_amount,
                t.applied_fees::text as applied_fees,
                t.total_fees_applied,
                t.contract_party,
                t.processing_date,
                t.created_at,
                c.contract_number,
                c.contract_name
            FROM transactions t
            LEFT JOIN contracts c ON t.contract_id = c.contract_id
            WHERE t.created_at > '{since_timestamp.isoformat()}'
            ORDER BY t.created_at DESC
            LIMIT 50
            """
            
            result = self.db_analyzer.execute_safe_query(query)
            
            if result.get('success') and result.get('data'):
                return result['data']
            
            return []
            
        except Exception as e:
            print(f"Error fetching new transactions: {e}")
            return []
    
    def get_contract_context_for_transaction(self, transaction: Dict) -> str:
        """
        Get relevant contract information for a transaction using RAG
        
        Args:
            transaction: Transaction record
            
        Returns:
            Relevant contract context
        """
        if not self.vector_store:
            return "No contract information available"
        
        # Build search query based on transaction
        search_queries = [
            f"{transaction['merchant']} {transaction['transaction_type']} fees",
            f"contract {transaction.get('contract_number', '')} fees",
            f"{transaction['merchant']} processing fee network fee",
            f"{transaction['transaction_type']} charges costs"
        ]
        
        all_context = []
        for query in search_queries:
            results = self.vector_store.search_similar_documents(query, k=2)
            for result in results:
                if result['similarity_score'] > 0.7:  # Only high relevance
                    all_context.append(result['text'])
        
        # Deduplicate and combine
        unique_contexts = list(set(all_context))
        combined_context = "\n\n".join(unique_contexts[:3])  # Top 3 unique contexts
        
        return combined_context if combined_context else "No specific contract terms found"
    
    def get_database_fee_context(self, transaction: Dict) -> Dict:
        """
        Get expected fees from database for this transaction type
        
        Args:
            transaction: Transaction record
            
        Returns:
            Dictionary with database fee information
        """
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                return {"error": "Database not connected"}
            
            # Query to get expected fees from database
            query = f"""
            SELECT 
                f.fee_type,
                f.base_amount,
                f.discounted_amount,
                f.is_waived,
                f.currency,
                f.effective_from,
                f.effective_to,
                c.contract_number,
                c.contract_name
            FROM fees f
            JOIN contracts c ON f.contract_id = c.contract_id
            WHERE f.contract_id = {transaction.get('contract_id', 0)}
                AND f.merchant = '{transaction['merchant']}'
                AND f.transaction_type = '{transaction['transaction_type']}'
                AND f.effective_from <= CURRENT_DATE
                AND (f.effective_to IS NULL OR f.effective_to >= CURRENT_DATE)
            """
            
            result = self.db_analyzer.execute_safe_query(query)
            
            if result.get('success') and result.get('data'):
                fee_context = {
                    "expected_fees": [],
                    "contract_info": None
                }
                
                for row in result['data']:
                    fee_info = {
                        "fee_type": row['fee_type'],
                        "base_amount": float(row['base_amount']),
                        "discounted_amount": float(row['discounted_amount']),
                        "is_waived": row['is_waived'],
                        "currency": row['currency']
                    }
                    fee_context["expected_fees"].append(fee_info)
                    
                    if not fee_context["contract_info"]:
                        fee_context["contract_info"] = {
                            "contract_number": row['contract_number'],
                            "contract_name": row['contract_name']
                        }
                
                return fee_context
            else:
                # Try to get general fee structure for this merchant/type
                fallback_query = f"""
                SELECT DISTINCT
                    f.fee_type,
                    AVG(f.discounted_amount) as avg_amount,
                    COUNT(*) as occurrences
                FROM fees f
                WHERE f.merchant = '{transaction['merchant']}'
                    AND f.transaction_type = '{transaction['transaction_type']}'
                GROUP BY f.fee_type
                """
                
                fallback_result = self.db_analyzer.execute_safe_query(fallback_query)
                if fallback_result.get('success') and fallback_result.get('data'):
                    return {
                        "expected_fees": fallback_result['data'],
                        "note": "Using average fees as specific contract not found"
                    }
                
                return {"error": "No fee data found in database"}
                
        except Exception as e:
            return {"error": f"Database query failed: {str(e)}"}
    
    def analyze_transaction_with_ai(self, transaction: Dict, contract_context: str, database_fee_context: Dict) -> Dict:
        """
        Use AI to analyze a transaction against contract terms
        
        Args:
            transaction: Transaction record
            contract_context: Relevant contract information from RAG
            database_fee_context: Expected fees from database
            
        Returns:
            AI analysis result with discrepancies
        """
        if not self.gemini_model:
            return {"error": "AI model not configured"}
        
        # Parse applied fees
        applied_fees = json.loads(transaction['applied_fees']) if transaction['applied_fees'] else {}
        
        # Format database fee context for prompt
        db_fee_text = ""
        if database_fee_context and "expected_fees" in database_fee_context:
            db_fee_text = "\n\nEXPECTED FEES FROM DATABASE:\n"
            for fee in database_fee_context["expected_fees"]:
                if isinstance(fee, dict):
                    fee_type = fee.get('fee_type', 'unknown')
                    amount = fee.get('discounted_amount', fee.get('avg_amount', 0))
                    waived = fee.get('is_waived', False)
                    db_fee_text += f"- {fee_type}: ${amount:.4f} {'(WAIVED)' if waived else ''}\n"
            
            if database_fee_context.get("contract_info"):
                db_fee_text += f"\nContract: {database_fee_context['contract_info']['contract_number']} - {database_fee_context['contract_info']['contract_name']}\n"
        
        prompt = f"""You are a financial compliance expert. Analyze this transaction against the contract terms and database fee structure.

TRANSACTION DETAILS:
- Transaction ID: {transaction['transaction_id']}
- Merchant: {transaction['merchant']}
- Type: {transaction['transaction_type']}
- Amount: ${transaction['transaction_amount']}
- Applied Fees: {json.dumps(applied_fees, indent=2)}
- Total Fees: ${transaction['total_fees_applied']}
- Date: {transaction['processing_date']}
{db_fee_text}

CONTRACT CONTEXT (from document search):
{contract_context}

ANALYSIS REQUIRED:
1. Check if all fees match the contract terms
2. Identify any missing fees that should be applied
3. Identify any overcharges or undercharges
4. Flag any fees that shouldn't be there
5. Calculate what the correct total should be

Return ONLY a JSON object with this structure:
{{
  "compliant": true/false,
  "issues": [
    {{
      "type": "Missing Fee|Overcharge|Undercharge|Unexpected Fee|Contract Violation",
      "description": "Clear description of the issue",
      "fee_type": "specific fee name",
      "expected_amount": 0.00,
      "actual_amount": 0.00,
      "variance": 0.00,
      "severity": "HIGH|MEDIUM|LOW",
      "contract_reference": "reference to contract clause if found"
    }}
  ],
  "correct_total": 0.00,
  "recommendation": "Brief action recommendation"
}}

Be precise with numbers. If the contract context doesn't clearly specify a fee, note it as "Contract terms unclear".
"""
        
        try:
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(response_text)
            analysis['transaction_id'] = transaction['transaction_id']
            analysis['merchant'] = transaction['merchant']
            analysis['transaction_type'] = transaction['transaction_type']
            
            return analysis
            
        except Exception as e:
            print(f"AI analysis error for {transaction['transaction_id']}: {e}")
            return {
                "transaction_id": transaction['transaction_id'],
                "error": str(e),
                "compliant": None,
                "issues": []
            }
    
    def check_recent_transactions(self, check_last_minutes: int = 10) -> pd.DataFrame:
        """
        Check recent transactions using AI and RAG
        
        Args:
            check_last_minutes: Check transactions from last N minutes
            
        Returns:
            DataFrame with AI-detected discrepancies
        """
        # Get recent transactions
        since_time = datetime.now() - timedelta(minutes=check_last_minutes)
        new_transactions = self.get_new_transactions(since_time)
        
        if not new_transactions:
            return pd.DataFrame({
                'Status': ['No new transactions'],
                'Period': [f'Last {check_last_minutes} minutes'],
                'Checked At': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            })
        
        all_discrepancies = []
        
        for transaction in new_transactions:
            # Get contract context from RAG
            contract_context = self.get_contract_context_for_transaction(transaction)
            
            # Get database fee context
            database_fee_context = self.get_database_fee_context(transaction)
            
            # Analyze with AI using both contexts
            analysis = self.analyze_transaction_with_ai(transaction, contract_context, database_fee_context)
            
            # Process results
            if analysis.get('issues'):
                for issue in analysis['issues']:
                    all_discrepancies.append({
                        'Transaction ID': transaction['transaction_id'],
                        'Merchant': transaction['merchant'],
                        'Type': transaction['transaction_type'],
                        'Issue Type': issue.get('type', 'Unknown'),
                        'Description': issue.get('description', ''),
                        'Expected': f"${issue.get('expected_amount', 0):.4f}",
                        'Actual': f"${issue.get('actual_amount', 0):.4f}",
                        'Variance': f"${issue.get('variance', 0):.4f}",
                        'Severity': issue.get('severity', 'MEDIUM'),
                        'Contract Ref': issue.get('contract_reference', 'N/A'),
                        'AI Confidence': 'High' if contract_context != "No contract information available" else 'Low',
                        'Timestamp': transaction['created_at']
                    })
        
        # Update last check timestamp
        self.last_check_timestamp = datetime.now()
        
        if all_discrepancies:
            return pd.DataFrame(all_discrepancies)
        else:
            return pd.DataFrame({
                'Status': ['✅ All transactions compliant'],
                'Transactions Checked': [len(new_transactions)],
                'Period': [f'Last {check_last_minutes} minutes'],
                'AI Analysis': ['Complete'],
                'Checked At': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            })
    
    def continuous_monitoring(self, callback_fn=None):
        """
        Continuously monitor for new transactions and check compliance
        
        Args:
            callback_fn: Function to call when discrepancies are found
        """
        import time
        
        print("🤖 AI Compliance Monitor Started")
        print("Checking for new transactions every 30 seconds...")
        
        while True:
            try:
                # Check transactions from last 1 minute
                df = self.check_recent_transactions(check_last_minutes=1)
                
                # If discrepancies found and callback provided
                if not df.empty and 'Severity' in df.columns and callback_fn:
                    high_severity = df[df['Severity'] == 'HIGH']
                    if not high_severity.empty:
                        callback_fn(high_severity)
                        print(f"⚠️ Found {len(high_severity)} HIGH severity issues!")
                
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                print("\n🛑 AI Compliance Monitor Stopped")
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(30)
    
    def generate_compliance_report(self, transaction_ids: List[str]) -> str:
        """
        Generate detailed AI compliance report for specific transactions
        
        Args:
            transaction_ids: List of transaction IDs to analyze
            
        Returns:
            Detailed compliance report
        """
        if not self.gemini_model:
            return "AI model not configured"
        
        # Fetch transaction details
        id_list = "','".join(transaction_ids)
        query = f"""
        SELECT t.*, c.contract_name, c.contract_number
        FROM transactions t
        LEFT JOIN contracts c ON t.contract_id = c.contract_id
        WHERE t.transaction_id IN ('{id_list}')
        """
        
        result = self.db_analyzer.execute_safe_query(query)
        if not result.get('success') or not result.get('data'):
            return "Could not fetch transaction data"
        
        transactions = result['data']
        
        # Get contract context and database fees for all
        all_contexts = []
        all_db_fees = []
        for txn in transactions:
            context = self.get_contract_context_for_transaction(txn)
            db_fees = self.get_database_fee_context(txn)
            all_contexts.append(context)
            all_db_fees.append(db_fees)
        
        # Create comprehensive prompt
        prompt = f"""Generate a detailed compliance report for these transactions.

TRANSACTIONS:
{json.dumps(transactions, indent=2, default=str)}

DATABASE FEE STRUCTURES:
{json.dumps(all_db_fees, indent=2, default=str)}

CONTRACT CONTEXTS (from documents):
{chr(10).join(all_contexts)}

Create a professional compliance report including:
1. Executive Summary
2. Transaction-by-transaction analysis
3. Identified discrepancies and their impact
4. Risk assessment
5. Recommendations for remediation
6. Estimated financial impact

Format the report in markdown."""
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating report: {e}"


# Example usage function
def create_ai_compliance_interface(vector_store, db_analyzer):
    """
    Create Gradio interface for AI compliance checking
    """
    import gradio as gr
    
    ai_checker = AIComplianceChecker(vector_store, db_analyzer)
    
    with gr.Column():
        gr.Markdown("## 🤖 AI-Powered Compliance Check")
        
        with gr.Row():
            time_range = gr.Slider(
                minimum=1,
                maximum=60,
                value=10,
                step=1,
                label="Check transactions from last N minutes"
            )
            
            check_btn = gr.Button("🔍 AI Analysis", variant="primary")
        
        # Results
        ai_results = gr.Dataframe(
            label="AI Discrepancy Detection Results",
            wrap=True
        )
        
        # Report generation
        with gr.Row():
            transaction_ids_input = gr.Textbox(
                label="Transaction IDs for detailed report (comma-separated)",
                placeholder="TXN_001, TXN_002"
            )
            generate_report_btn = gr.Button("📄 Generate Report")
        
        report_output = gr.Markdown(label="Compliance Report")
        
        # Event handlers
        def run_ai_check(minutes):
            df = ai_checker.check_recent_transactions(int(minutes))
            return df
        
        def generate_report(ids_text):
            if not ids_text:
                return "Please enter transaction IDs"
            ids = [id.strip() for id in ids_text.split(',')]
            report = ai_checker.generate_compliance_report(ids)
            return report
        
        check_btn.click(
            fn=run_ai_check,
            inputs=[time_range],
            outputs=[ai_results]
        )
        
        generate_report_btn.click(
            fn=generate_report,
            inputs=[transaction_ids_input],
            outputs=[report_output]
        )
        
        return ai_results