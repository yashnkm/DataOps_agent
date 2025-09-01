import os
import json
from typing import Dict, Any, List, Optional, Tuple
from .db_analyzer import DatabaseAnalyzer
from .database_manager import DatabaseManager
import google.generativeai as genai


class DatabaseQueryInterface:
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.query_history = []
        
        # Initialize database components with error handling
        try:
            self.db_analyzer = DatabaseAnalyzer()
            self.db_manager = DatabaseManager()
            print("✅ Database interface initialized successfully")
        except Exception as e:
            print(f"⚠️ Database interface initialization warning: {e}")
            self.db_analyzer = None
            self.db_manager = None
        
    def get_database_overview(self) -> Dict[str, Any]:
        """Get comprehensive database overview"""
        try:
            # Check if database components are available
            if not self.db_analyzer or not self.db_manager:
                return {
                    "success": False,
                    "message": "🔌 Database not configured. Set DB_HOST, DB_NAME, DB_USER, DB_PASSWORD in .env",
                    "details": {}
                }
            
            # Analyze database structure
            analysis = self.db_analyzer.analyze_database_structure()
            
            if "error" in analysis:
                return {
                    "success": False,
                    "message": f"❌ Database analysis failed: {analysis['error']}",
                    "details": {}
                }
            
            # Format overview
            overview = {
                "success": True,
                "connection_status": analysis["connection_status"],
                "table_count": len(analysis["tables"]),
                "relationship_count": len(analysis["relationships"]),
                "tables": analysis["tables"],
                "relationships": analysis["relationships"],
                "suggestions": analysis["suggestions"]
            }
            
            return overview
            
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ Error getting database overview: {str(e)}",
                "details": {}
            }
    
    def format_database_overview_display(self) -> str:
        """Format database overview for Gradio display"""
        overview = self.get_database_overview()
        
        if not overview["success"]:
            return overview["message"]
        
        display = f"""# 🗄️ Database Analysis Report

## 📊 Database Overview
- **Connection Status:** {'✅ Connected' if overview['connection_status'] == 'connected' else '❌ Disconnected'}
- **Tables:** {overview['table_count']}
- **Relationships:** {overview['relationship_count']}

## 📋 Tables Structure
"""
        
        for table_name, table_info in overview["tables"].items():
            if table_name.startswith('pg_'):
                continue
            
            display += f"\n### 📊 {table_name}\n"
            display += f"- **Type:** {table_info['type']}\n"
            display += f"- **Rows:** {table_info['row_count']}\n"
            display += f"- **Columns:** {len(table_info['columns'])}\n\n"
            
            if table_info['columns']:
                display += "**Column Details:**\n"
                for col in table_info['columns'][:5]:  # Show first 5 columns
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    display += f"- `{col['name']}` ({col['type']}) {nullable}\n"
                
                if len(table_info['columns']) > 5:
                    display += f"- ... and {len(table_info['columns']) - 5} more columns\n"
            
            display += "\n"
        
        # Show relationships
        if overview["relationships"]:
            display += "\n## 🔗 Table Relationships\n"
            for rel in overview["relationships"]:
                display += f"- `{rel['source_table']}.{rel['source_column']}` → `{rel['target_table']}.{rel['target_column']}`\n"
        
        # Show suggestions
        if overview["suggestions"]:
            display += "\n## 💡 Query Suggestions\n"
            for suggestion in overview["suggestions"][:10]:  # Show first 10
                display += f"{suggestion}\n"
        
        return display
    
    def execute_natural_language_query(self, user_query: str, session_id: str = None) -> Tuple[str, str]:
        """Execute natural language database query with session tracking"""
        try:
            # Check if database is available
            if not self.db_analyzer or not self.db_manager:
                return "🔌 Database not configured. Please set up PostgreSQL connection in .env file.", ""
            
            # Check if this is a question about database structure/schema
            if self._is_schema_question(user_query):
                response = self._answer_schema_question(user_query)
                self._log_query(session_id, user_query, "SCHEMA_QUERY", response)
                return response, "SCHEMA_QUERY"
            
            # Convert to SQL for data queries
            sql_result = self.db_analyzer.natural_language_to_sql(user_query)
            
            if not sql_result.get("success", False):
                error_msg = f"❌ SQL Generation Failed: {sql_result.get('error', 'Unknown error')}"
                self._log_query(session_id, user_query, None, error_msg)
                return error_msg, ""
            
            sql_query = sql_result["sql_query"]
            
            # Execute SQL
            query_result = self.db_analyzer.execute_safe_query(sql_query)
            
            if not query_result["success"]:
                error_msg = f"❌ Query Execution Failed: {query_result['error']}"
                self._log_query(session_id, user_query, sql_query, error_msg)
                return error_msg, sql_query
            
            # Format results in business-friendly format
            if "data" in query_result and query_result["data"]:
                response = self._format_business_friendly_results(query_result, user_query)
                
            elif "message" in query_result:
                response = f"✅ {query_result['message']}"
                if "affected_rows" in query_result:
                    response += f" (Affected rows: {query_result['affected_rows']})"
            else:
                response = "✅ Query executed successfully, no data returned"
            
            # Log successful query
            self._log_query(session_id, user_query, sql_query, response)
            
            return response, sql_query
            
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            self._log_query(session_id, user_query, None, error_msg)
            return error_msg, ""
    
    def execute_direct_sql(self, sql_query: str, session_id: str = None) -> Tuple[str, str]:
        """Execute SQL query directly with session tracking"""
        try:
            # Check if database is available
            if not self.db_analyzer or not self.db_manager:
                return "🔌 Database not configured. Please set up PostgreSQL connection in .env file.", ""
            
            query_result = self.db_analyzer.execute_safe_query(sql_query)
            
            if not query_result["success"]:
                error_msg = f"❌ SQL Execution Failed: {query_result['error']}"
                self._log_query(session_id, "Direct SQL", sql_query, error_msg)
                return error_msg, sql_query
            
            # Format results similar to natural language queries
            if "data" in query_result and query_result["data"]:
                response = f"✅ **Query Results** ({query_result['row_count']} rows)\n\n"
                
                if query_result["data"]:
                    columns = list(query_result["data"][0].keys())
                    response += "| " + " | ".join(columns) + " |\n"
                    response += "|" + "|".join(["---"] * len(columns)) + "|\n"
                    
                    for i, row in enumerate(query_result["data"][:10]):
                        values = [str(row.get(col, "")) for col in columns]
                        response += "| " + " | ".join(values) + " |\n"
                    
                    if query_result['row_count'] > 10:
                        response += f"\n*Showing first 10 of {query_result['row_count']} total rows*\n"
            else:
                response = "✅ Query executed successfully"
            
            self._log_query(session_id, "Direct SQL", sql_query, response)
            return response, sql_query
            
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            self._log_query(session_id, "Direct SQL", sql_query, error_msg)
            return error_msg, sql_query
    
    def get_crud_examples(self) -> str:
        """Get CRUD operation examples"""
        try:
            # Check if database is available
            if not self.db_analyzer or not self.db_manager:
                return "🔌 Database not configured. Please set up PostgreSQL connection in .env file."
            
            examples = self.db_analyzer.generate_crud_examples()
            
            if "error" in examples:
                return f"❌ Error generating examples: {examples['error']}"
            
            display = "# 📚 Database Query Examples\n\n"
            
            for operation, queries in examples.items():
                if queries:
                    display += f"## {operation} Operations\n"
                    for query in queries[:5]:  # Show first 5 examples
                        display += f"```sql\n{query}\n```\n"
                    display += "\n"
            
            return display
            
        except Exception as e:
            return f"❌ Error getting CRUD examples: {str(e)}"
    
    def _format_business_friendly_results(self, query_result: Dict[str, Any], user_query: str) -> str:
        """Format database results in business-friendly, human-readable format"""
        data = query_result["data"]
        row_count = query_result["row_count"]
        
        if not data:
            return "No matching records found for your query."
        
        # Detect the type of query and format accordingly
        first_row = data[0]
        table_type = self._detect_table_context(first_row.keys(), user_query)
        
        if table_type == "customers":
            return self._format_customer_results(data, row_count, user_query)
        elif table_type == "risk_assessments":
            return self._format_risk_assessment_results(data, row_count, user_query)
        elif table_type == "accounts":
            return self._format_account_results(data, row_count, user_query)
        elif table_type == "loans":
            return self._format_loan_results(data, row_count, user_query)
        elif table_type == "portfolios":
            return self._format_portfolio_results(data, row_count, user_query)
        elif table_type == "transactions":
            return self._format_transaction_results(data, row_count, user_query)
        else:
            return self._format_generic_business_results(data, row_count, user_query)
    
    def _detect_table_context(self, columns: List[str], user_query: str) -> str:
        """Detect what type of data we're dealing with"""
        columns_lower = [col.lower() for col in columns]
        query_lower = user_query.lower()
        
        if 'customer_id' in columns_lower or 'customers' in query_lower:
            return "customers"
        elif 'assessment_id' in columns_lower or 'risk' in query_lower:
            return "risk_assessments"
        elif 'account_id' in columns_lower or 'account' in query_lower:
            return "accounts"
        elif 'loan_id' in columns_lower or 'loan' in query_lower:
            return "loans"
        elif 'portfolio_id' in columns_lower or 'portfolio' in query_lower:
            return "portfolios"
        elif 'transaction' in query_lower:
            return "transactions"
        else:
            return "generic"
    
    def _format_customer_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format customer data in business terms"""
        response = f"**👥 Found {row_count} customer{'s' if row_count != 1 else ''}**\n\n"
        
        for i, customer in enumerate(data[:5], 1):
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
            email = customer.get('email', 'N/A')
            phone = customer.get('phone_number', 'N/A')
            income = customer.get('annual_income', 'N/A')
            credit_score = customer.get('credit_score', 'N/A')
            
            response += f"**{i}. {name}**\n"
            response += f"   📧 Contact: {email} | 📞 {phone}\n"
            response += f"   💰 Annual Income: ${income:,}" if isinstance(income, (int, float)) else f"   💰 Annual Income: {income}\n"
            response += f"   📊 Credit Score: {credit_score}\n\n"
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more customers*\n"
        
        return response
    
    def _format_risk_assessment_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format risk assessment data in business terms"""
        response = f"**⚠️ Found {row_count} risk assessment{'s' if row_count != 1 else ''}**\n\n"
        
        for i, assessment in enumerate(data[:5], 1):
            customer_id = assessment.get('customer_id', 'N/A')
            risk_score = assessment.get('risk_score', 'N/A')
            risk_category = assessment.get('risk_category', 'N/A').title()
            assessment_date = str(assessment.get('assessment_date', 'N/A'))[:10]
            assessment_type = assessment.get('assessment_type', 'N/A').title()
            
            response += f"**{i}. Customer #{customer_id} - {assessment_type} Risk Assessment**\n"
            response += f"   📊 Risk Score: {risk_score}/100 ({risk_category} Risk)\n"
            response += f"   📅 Assessment Date: {assessment_date}\n"
            
            # Parse factors if available
            factors = assessment.get('factors_considered')
            if factors and isinstance(factors, dict):
                response += f"   🔍 Key Factors: {', '.join(factors.keys())}\n"
            
            response += "\n"
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more assessments*\n"
        
        return response
    
    def _format_account_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format account data in business terms"""
        response = f"**🏦 Found {row_count} account{'s' if row_count != 1 else ''}**\n\n"
        
        total_balance = 0
        for i, account in enumerate(data[:5], 1):
            account_type = account.get('account_type', 'Unknown').title()
            balance = account.get('balance', 0)
            status = account.get('account_status', 'Unknown').title()
            opened_date = str(account.get('date_opened', 'N/A'))[:10]
            
            response += f"**{i}. {account_type} Account**\n"
            response += f"   💰 Balance: ${balance:,}" if isinstance(balance, (int, float)) else f"   💰 Balance: {balance}\n"
            response += f"   📊 Status: {status}\n"
            response += f"   📅 Opened: {opened_date}\n\n"
            
            if isinstance(balance, (int, float)):
                total_balance += balance
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more accounts*\n"
        
        if total_balance > 0:
            response += f"\n**💰 Total Balance Shown: ${total_balance:,}**"
        
        return response
    
    def _format_loan_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format loan data in business terms"""
        response = f"**🏠 Found {row_count} loan{'s' if row_count != 1 else ''}**\n\n"
        
        total_outstanding = 0
        for i, loan in enumerate(data[:5], 1):
            loan_type = loan.get('loan_type', 'Unknown').title()
            amount = loan.get('loan_amount', 0)
            outstanding = loan.get('outstanding_balance', 0)
            status = loan.get('loan_status', 'Unknown').title()
            
            response += f"**{i}. {loan_type} Loan**\n"
            response += f"   💰 Original Amount: ${amount:,}" if isinstance(amount, (int, float)) else f"   💰 Original Amount: {amount}\n"
            response += f"   📊 Outstanding: ${outstanding:,}" if isinstance(outstanding, (int, float)) else f"   📊 Outstanding: {outstanding}\n"
            response += f"   🔄 Status: {status}\n\n"
            
            if isinstance(outstanding, (int, float)):
                total_outstanding += outstanding
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more loans*\n"
        
        if total_outstanding > 0:
            response += f"\n**💰 Total Outstanding: ${total_outstanding:,}**"
        
        return response
    
    def _format_portfolio_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format portfolio data in business terms"""
        response = f"**📈 Found {row_count} portfolio{'s' if row_count != 1 else ''}**\n\n"
        
        total_value = 0
        for i, portfolio in enumerate(data[:5], 1):
            portfolio_name = portfolio.get('portfolio_name', 'Unknown Portfolio')
            value = portfolio.get('total_value', 0)
            risk_tolerance = portfolio.get('risk_tolerance', 'Unknown').title()
            ytd_return = portfolio.get('ytd_return_percentage', 'N/A')
            
            response += f"**{i}. {portfolio_name}**\n"
            response += f"   💰 Portfolio Value: ${value:,}" if isinstance(value, (int, float)) else f"   💰 Portfolio Value: {value}\n"
            response += f"   📊 Risk Level: {risk_tolerance}\n"
            response += f"   📈 YTD Return: {ytd_return}%" if isinstance(ytd_return, (int, float)) else f"   📈 YTD Return: {ytd_return}\n"
            response += "\n"
            
            if isinstance(value, (int, float)):
                total_value += value
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more portfolios*\n"
        
        if total_value > 0:
            response += f"\n**💰 Total Portfolio Value: ${total_value:,}**"
        
        return response
    
    def _format_transaction_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format transaction data in business terms"""
        response = f"**💳 Found {row_count} transaction{'s' if row_count != 1 else ''}**\n\n"
        
        total_amount = 0
        for i, transaction in enumerate(data[:5], 1):
            date = str(transaction.get('transaction_date', 'N/A'))[:10]
            amount = transaction.get('transaction_amount', 0)
            trans_type = transaction.get('transaction_type', 'Unknown').title()
            
            response += f"**{i}. {trans_type} Transaction**\n"
            response += f"   📅 Date: {date}\n"
            response += f"   💰 Amount: ${amount:,}" if isinstance(amount, (int, float)) else f"   💰 Amount: {amount}\n"
            response += "\n"
            
            if isinstance(amount, (int, float)):
                total_amount += amount
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more transactions*\n"
        
        if total_amount > 0:
            response += f"\n**💰 Total Transaction Value: ${total_amount:,}**"
        
        return response
    
    def _format_generic_business_results(self, data: List[Dict], row_count: int, user_query: str) -> str:
        """Format generic results in business-friendly way"""
        response = f"**📋 Found {row_count} record{'s' if row_count != 1 else ''}**\n\n"
        
        for i, record in enumerate(data[:5], 1):
            response += f"**{i}. Record Details**\n"
            
            # Show key fields in business format
            for key, value in record.items():
                # Format field names to be more readable
                readable_key = key.replace('_', ' ').title()
                
                # Format values based on type
                if isinstance(value, (int, float)) and 'amount' in key.lower() or 'balance' in key.lower() or 'value' in key.lower():
                    response += f"   💰 {readable_key}: ${value:,}\n"
                elif isinstance(value, (int, float)) and 'score' in key.lower():
                    response += f"   📊 {readable_key}: {value}\n"
                elif 'date' in key.lower():
                    date_str = str(value)[:10] if value else 'N/A'
                    response += f"   📅 {readable_key}: {date_str}\n"
                elif 'email' in key.lower():
                    response += f"   📧 {readable_key}: {value}\n"
                elif 'phone' in key.lower():
                    response += f"   📞 {readable_key}: {value}\n"
                else:
                    response += f"   📋 {readable_key}: {value}\n"
            
            response += "\n"
        
        if row_count > 5:
            response += f"*...and {row_count - 5} more records*\n"
        
        return response
    
    def _is_schema_question(self, query: str) -> bool:
        """Detect if query is asking about database structure rather than data"""
        schema_keywords = [
            'what is', 'what are', 'describe', 'explain', 'tell me about',
            'fields', 'columns', 'structure', 'schema', 'table contains',
            'what does', 'how is', 'what fields', 'what columns'
        ]
        
        table_keywords = [
            'table', 'tables', 'database', 'schema', 'structure'
        ]
        
        query_lower = query.lower()
        
        # Check for schema question patterns
        has_schema_keyword = any(keyword in query_lower for keyword in schema_keywords)
        has_table_keyword = any(keyword in query_lower for keyword in table_keywords)
        
        # Also check for specific table name mentions
        table_names = ['customers', 'accounts', 'loans', 'portfolios', 'risk_assessments', 
                      'compliance_reports', 'employees', 'branches']
        mentions_table = any(table in query_lower for table in table_names)
        
        return (has_schema_keyword and (has_table_keyword or mentions_table))
    
    def _answer_schema_question(self, query: str) -> str:
        """Answer questions about database structure in human terms"""
        try:
            overview = self.get_database_overview()
            if not overview["success"]:
                return overview["message"]
            
            tables = overview["tables"]
            relationships = overview["relationships"]
            query_lower = query.lower()
            
            # Specific table explanations
            if 'accounts' in query_lower:
                return self._explain_accounts_table(tables.get('accounts', {}))
            elif 'customers' in query_lower:
                return self._explain_customers_table(tables.get('customers', {}))
            elif 'loans' in query_lower:
                return self._explain_loans_table(tables.get('loans', {}))
            elif 'portfolios' in query_lower:
                return self._explain_portfolios_table(tables.get('portfolios', {}))
            elif 'risk' in query_lower:
                return self._explain_risk_assessments_table(tables.get('risk_assessments', {}))
            elif 'compliance' in query_lower:
                return self._explain_compliance_table(tables.get('compliance_reports', {}))
            elif 'employees' in query_lower:
                return self._explain_employees_table(tables.get('employees', {}))
            elif 'branches' in query_lower:
                return self._explain_branches_table(tables.get('branches', {}))
            elif 'database' in query_lower or 'structure' in query_lower:
                return self._explain_database_overview(tables, relationships)
            else:
                return self._explain_database_overview(tables, relationships)
                
        except Exception as e:
            return f"❌ Error explaining database structure: {str(e)}"
    
    def _explain_accounts_table(self, table_info: Dict) -> str:
        """Explain accounts table in business terms"""
        if not table_info:
            return "❌ Accounts table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 🏦 Accounts Table Explanation

**What it contains:** Customer bank accounts (like checking, savings, business accounts)

**Business Purpose:** Tracks all the different accounts our customers have with the bank, including their current balances and account status.

**Number of accounts:** {row_count} total accounts

**Key Information Stored:**
💰 **Account Balance** - How much money is currently in each account
📋 **Account Type** - Checking, savings, business, etc.
📊 **Account Status** - Active, inactive, frozen, closed
📅 **Date Opened** - When the customer opened this account
🔗 **Customer Link** - Which customer owns this account
🏢 **Branch Link** - Which branch manages this account

**Real-world use:**
- Check a customer's total balance across all accounts
- Find accounts that haven't been used recently
- See which types of accounts are most popular
- Monitor account health and status

**Example questions you can ask:**
- "How much money do customers have in savings accounts?"
- "Which accounts were opened in the last 6 months?"
- "Show me business accounts with high balances"
"""
    
    def _explain_customers_table(self, table_info: Dict) -> str:
        """Explain customers table in business terms"""
        if not table_info:
            return "❌ Customers table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 👥 Customers Table Explanation

**What it contains:** All our bank customers and their personal information

**Business Purpose:** Central record of everyone who does business with our bank, including their contact details, financial profile, and relationship status.

**Number of customers:** {row_count} total customers

**Key Information Stored:**
👤 **Personal Details** - Names, addresses, phone numbers, email
💰 **Financial Profile** - Annual income, employment status, credit score
📊 **Customer Segment** - VIP, standard, business customer classifications
📅 **Relationship History** - When they became a customer, last contact
🔒 **Compliance Status** - KYC (Know Your Customer) verification status
✅ **Account Status** - Active, inactive, suspended customers

**Real-world use:**
- Find high-value customers for special offers
- Contact customers for account updates or promotions
- Verify customer information for compliance
- Segment customers for marketing campaigns

**Example questions you can ask:**
- "Who are our VIP customers?"
- "Which customers need updated contact information?"
- "Show me customers with excellent credit scores"
- "Find customers who haven't been contacted recently"
"""
    
    def _explain_loans_table(self, table_info: Dict) -> str:
        """Explain loans table in business terms"""
        if not table_info:
            return "❌ Loans table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 🏠 Loans Table Explanation

**What it contains:** All loans the bank has given to customers

**Business Purpose:** Tracks mortgages, car loans, personal loans, and business loans including payment status and remaining balances.

**Number of loans:** {row_count} total loans

**Key Information Stored:**
💰 **Loan Details** - Original amount, current balance, interest rate
🏠 **Loan Type** - Mortgage, auto, personal, business loans
📅 **Timeline** - Start date, end date, payment schedule
📊 **Payment Status** - Current, overdue, paid off, defaulted
🔒 **Loan Terms** - Interest rate, payment amount, loan duration
👤 **Customer Link** - Which customer has this loan

**Real-world use:**
- Monitor customers who might miss payments
- Calculate total loan portfolio value
- Find loans ready for refinancing opportunities
- Track loan performance by type

**Example questions you can ask:**
- "Which customers have mortgage loans over $500,000?"
- "Show me loans with payments due this week"
- "Find customers who might be struggling with payments"
- "What's our total outstanding loan amount?"
"""
    
    def _explain_portfolios_table(self, table_info: Dict) -> str:
        """Explain portfolios table in business terms"""
        if not table_info:
            return "❌ Portfolios table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 📈 Portfolios Table Explanation

**What it contains:** Customer investment portfolios and their performance

**Business Purpose:** Tracks how customers' investments are performing, what their risk tolerance is, and manages their investment goals.

**Number of portfolios:** {row_count} total investment portfolios

**Key Information Stored:**
💰 **Portfolio Value** - Current total worth of all investments
📊 **Performance** - Year-to-date returns, gains/losses
🎯 **Investment Strategy** - Conservative, moderate, aggressive approach
👤 **Customer Link** - Which customer owns this portfolio
📈 **Holdings** - What stocks, bonds, funds are in the portfolio
📅 **Timeline** - When portfolio was created, last rebalanced

**Real-world use:**
- Monitor investment performance for customers
- Identify portfolios that need rebalancing
- Find customers ready for financial planning discussions
- Track which investment strategies work best

**Example questions you can ask:**
- "Which portfolios have the best returns this year?"
- "Show me customers with conservative investment strategies"
- "Find portfolios that lost money recently"
- "Which customers should we contact about their investments?"
"""
    
    def _explain_risk_assessments_table(self, table_info: Dict) -> str:
        """Explain risk assessments table in business terms"""
        if not table_info:
            return "❌ Risk assessments table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## ⚠️ Risk Assessments Table Explanation

**What it contains:** Evaluations of how risky each customer is for the bank

**Business Purpose:** Helps the bank decide whether to approve loans, set interest rates, and manage potential losses from customers who might not pay back money.

**Number of assessments:** {row_count} total risk evaluations

**Key Information Stored:**
📊 **Risk Score** - Number from 0-100 indicating how risky the customer is
🎯 **Risk Category** - Low, medium, high risk classification
🔍 **Risk Factors** - What makes this customer risky (job stability, credit history, debt levels)
📅 **Assessment Date** - When this evaluation was done
👤 **Customer Link** - Which customer this assessment is for
📋 **Assessment Type** - Credit risk, investment risk, operational risk

**Real-world use:**
- Decide loan approval and interest rates
- Monitor customers who might become problematic
- Comply with banking regulations about risk management
- Plan for potential losses

**Example questions you can ask:**
- "Which customers are high risk for loan defaults?"
- "Show me customers whose risk scores have improved"
- "Find customers who need updated risk assessments"
- "What makes our riskiest customers risky?"
"""
    
    def _explain_compliance_table(self, table_info: Dict) -> str:
        """Explain compliance table in business terms"""
        if not table_info:
            return "❌ Compliance reports table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 📋 Compliance Reports Table Explanation

**What it contains:** Reports we must submit to government regulators

**Business Purpose:** Tracks all the paperwork and reports the bank must file with government agencies to stay legally compliant and avoid fines.

**Number of reports:** {row_count} compliance reports

**Key Information Stored:**
📊 **Report Type** - AML (anti-money laundering), capital adequacy, stress tests
📅 **Due Dates** - When reports must be submitted to avoid penalties
✅ **Submission Status** - Draft, submitted, approved, rejected
🏢 **Regulatory Body** - Which government agency needs this report
📋 **Report Content** - Summary of what's being reported
⚠️ **Compliance Status** - Whether we're meeting requirements

**Real-world use:**
- Avoid regulatory fines and penalties
- Track deadlines for important submissions
- Monitor bank's overall compliance health
- Prepare for regulatory examinations

**Example questions you can ask:**
- "What compliance reports are due this month?"
- "Are we up to date with all regulatory requirements?"
- "Which reports were rejected and need resubmission?"
- "Show me our anti-money laundering compliance status"
"""
    
    def _explain_employees_table(self, table_info: Dict) -> str:
        """Explain employees table in business terms"""
        if not table_info:
            return "❌ Employees table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 👨‍💼 Employees Table Explanation

**What it contains:** All bank staff and their work information

**Business Purpose:** Manages our workforce, tracks who works where, their roles, and helps assign customers to the right staff members.

**Number of employees:** {row_count} total staff members

**Key Information Stored:**
👤 **Personal Info** - Names, contact details, employee ID numbers
🏢 **Work Details** - Department, job title, which branch they work at
📅 **Employment History** - Hire date, salary, employment status
🎯 **Responsibilities** - Whether they handle loans, investments, customer service
👥 **Customer Assignments** - Which customers they serve as advisors

**Real-world use:**
- Assign customers to appropriate staff members
- Track employee performance and responsibilities
- Manage staffing across different branches
- Ensure customers have proper advisor relationships

**Example questions you can ask:**
- "Which employees work in the downtown branch?"
- "Show me investment advisors and their customers"
- "Find loan officers who handle mortgage applications"
- "Which staff members have been here longest?"
"""
    
    def _explain_branches_table(self, table_info: Dict) -> str:
        """Explain branches table in business terms"""
        if not table_info:
            return "❌ Branches table not found in database"
        
        row_count = table_info.get('row_count', 0)
        
        return f"""## 🏢 Branches Table Explanation

**What it contains:** All bank branch locations and their details

**Business Purpose:** Manages our physical locations, tracks which customers and employees belong to each branch, and monitors branch performance.

**Number of branches:** {row_count} total locations

**Key Information Stored:**
📍 **Location Details** - Addresses, phone numbers, operating hours
👨‍💼 **Management** - Branch manager, staff count
📊 **Performance** - Customer count, account totals, branch metrics
🕒 **Operations** - Opening hours, services offered
🏢 **Branch Type** - Main office, satellite office, ATM location

**Real-world use:**
- Help customers find nearest branch locations
- Analyze which branches are most profitable
- Plan new branch locations or closures
- Assign customers and staff to appropriate branches

**Example questions you can ask:**
- "Which branch has the most customers?"
- "Show me branch locations in downtown area"
- "Find branches that are underperforming"
- "Which branch managers handle the most accounts?"
"""
    
    def _explain_database_overview(self, tables: Dict, relationships: List) -> str:
        """Explain entire database structure in business terms"""
        table_count = len([t for t in tables.keys() if not t.startswith('pg_')])
        relationship_count = len(relationships)
        
        return f"""## 🏦 Financial Services Database Overview

**What this database contains:** Complete information system for a bank or financial institution

**Business Purpose:** Manages all aspects of banking operations - from customer relationships to loan management to investment tracking to regulatory compliance.

**Database Size:** {table_count} main data tables with {relationship_count} connections between them

## 📊 Main Business Areas Covered:

### 👥 **Customer Management**
- Customer profiles and contact information
- Account relationships and history
- Customer segmentation and classification

### 💰 **Banking Operations** 
- Checking, savings, and business accounts
- Account balances and transaction history
- Account status and lifecycle management

### 🏠 **Lending Business**
- Mortgages, auto loans, personal loans, business loans
- Payment tracking and loan performance
- Risk assessment for loan approvals

### 📈 **Investment Services**
- Customer investment portfolios
- Stock, bond, and fund holdings
- Investment performance tracking

### ⚠️ **Risk Management**
- Credit risk, investment risk, operational risk assessments
- Risk scoring and categorization
- Risk factor analysis

### 📋 **Regulatory Compliance**
- Government reporting requirements
- Audit trails and activity logging
- Compliance status tracking

## 🔗 **How Everything Connects:**
- Customers can have multiple accounts, loans, and portfolios
- Each account, loan, or portfolio belongs to one customer
- Employees are assigned to serve specific customers
- All activities are tracked for compliance and audit purposes
- Risk assessments help make lending and investment decisions

**Think of it as:** A complete digital record of everything a bank needs to know to serve customers, manage risk, and stay compliant with regulations.
"""

    def _log_query(self, session_id: str, user_query: str, sql_query: str, response: str):
        """Log database query to session if session manager available"""
        try:
            if self.session_manager and session_id:
                metadata = {
                    "query_type": "database",
                    "sql_query": sql_query,
                    "user_query": user_query
                }
                
                self.session_manager.add_message(
                    session_id, 
                    'user', 
                    f"DB Query: {user_query}", 
                    metadata
                )
                self.session_manager.add_message(
                    session_id, 
                    'assistant', 
                    response, 
                    metadata
                )
            
            # Also keep local history
            self.query_history.append({
                "user_query": user_query,
                "sql_query": sql_query,
                "response": response,
                "timestamp": os.path.getmtime(__file__)  # Simple timestamp
            })
            
        except Exception as e:
            print(f"Error logging query: {e}")
    
    def get_connection_info(self) -> str:
        """Get database connection information for display"""
        try:
            # Check if database is available
            if not self.db_analyzer or not self.db_manager:
                return """# 🔌 Database Connection Status
                
❌ **Status:** Not Configured

## Required Environment Variables
Please add these to your `.env` file:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

💡 **Note:** Database features are optional. You can use document RAG without database connection."""
            
            conn_status = self.db_analyzer.get_connection_status()
            
            info = f"""# 🔌 Database Connection Status

**Status:** {'✅ Connected' if conn_status['status'] == 'connected' else '❌ Disconnected'}
**Connection String:** `{conn_status['connection_string']}`
**Engine Active:** {'✅ Yes' if conn_status['engine_active'] else '❌ No'}

## 📋 Environment Variables Expected:
- `DB_HOST` (default: localhost)
- `DB_PORT` (default: 5432)  
- `DB_NAME` (default: rag_system)
- `DB_USER` (default: postgres)
- `DB_PASSWORD` (required)
"""
            
            if conn_status['status'] == 'connected':
                info += "\n✅ **Ready for queries!**"
            else:
                info += "\n❌ **Please check database configuration and connectivity**"
            
            return info
            
        except Exception as e:
            return f"❌ Error getting connection info: {str(e)}"
    
    def hybrid_query(self, query: str, session_id: str = None, include_documents: bool = True, include_database: bool = True) -> str:
        """Execute hybrid query combining document RAG and database search"""
        try:
            results = []
            
            # Database query if requested
            if include_database and self.db_analyzer.connection_status == "connected":
                db_response, sql_used = self.execute_natural_language_query(query, session_id)
                results.append(f"## 🗄️ Database Results\n{db_response}")
                if sql_used:
                    results.append(f"**SQL Used:** `{sql_used}`\n")
            
            # Document query if requested (would need RAG processor integration)
            if include_documents:
                results.append("## 📄 Document Search\n*Document search would be integrated here with RAG processor*")
            
            if not results:
                return "❌ No data sources enabled for query"
            
            return "\n\n".join(results)
            
        except Exception as e:
            return f"❌ Hybrid query error: {str(e)}"