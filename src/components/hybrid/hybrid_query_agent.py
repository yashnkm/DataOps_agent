import os
import json
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai
from datetime import datetime


class HybridQueryAgent:
    """
    Intelligent agent that processes hybrid queries combining documents and database
    Uses multi-phase analysis to prevent errors and provide comprehensive answers
    """
    
    def __init__(self, rag_processor=None, db_analyzer=None, session_manager=None):
        self.rag_processor = rag_processor
        self.db_analyzer = db_analyzer  
        self.session_manager = session_manager
        
        # Configure Gemini for intelligent analysis
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
        
        self.processing_log = []
    
    def process_hybrid_query(self, user_query: str, session_id: str = None) -> Dict[str, Any]:
        """Main agent processing pipeline"""
        
        # Initialize processing log
        self.processing_log = []
        self._log_phase("🚀 Starting hybrid query processing")
        
        try:
            # Phase 1: Intent Analysis
            intent_analysis = self._analyze_user_intent(user_query)
            if intent_analysis.get('error'):
                return self._create_error_response(intent_analysis['error'])
            
            # Phase 2: Database Scouting
            db_scouting = self._scout_database_relevance(intent_analysis, user_query)
            if db_scouting.get('error'):
                return self._create_error_response(db_scouting['error'])
            
            # Phase 3: Smart Query Generation & Execution
            query_results = self._execute_smart_queries(intent_analysis, db_scouting, user_query)
            
            # Phase 4: Result Synthesis
            final_response = self._synthesize_results(intent_analysis, query_results, user_query)
            
            # Log to session if available
            if self.session_manager and session_id:
                self._log_to_session(session_id, user_query, final_response)
            
            return final_response
            
        except Exception as e:
            error_response = self._create_error_response(f"Agent processing failed: {str(e)}")
            self._log_phase(f"❌ Agent error: {str(e)}")
            return error_response
    
    def _analyze_user_intent(self, user_query: str) -> Dict[str, Any]:
        """Phase 1: Analyze what the user really wants"""
        self._log_phase("🧠 Phase 1: Analyzing user intent")
        
        try:
            prompt = f"""Analyze this user query and extract key information:

User Query: "{user_query}"

Extract and return JSON with:
1. "needs_documents": true/false - Does this query need document information?
2. "needs_database": true/false - Does this query need database data?
3. "key_concepts": [list] - Main business concepts mentioned
4. "document_keywords": [list] - Terms to search for in documents
5. "database_targets": [list] - What type of database info might be needed (customers, accounts, loans, etc.)
6. "comparison_type": string - "strategy_vs_reality", "document_lookup", "data_analysis", "hybrid_comparison"
7. "priority": "document_first" or "database_first" or "equal"

Return ONLY valid JSON, no other text."""

            if not os.getenv('GOOGLE_API_KEY_SOL_4'):
                return {"error": "Google API key not configured"}
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            # Parse JSON response
            try:
                intent_data = json.loads(response.text.strip())
                self._log_phase(f"✅ Intent identified: {intent_data.get('comparison_type', 'unknown')}")
                return intent_data
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "needs_documents": True,
                    "needs_database": True,
                    "key_concepts": [user_query],
                    "document_keywords": [user_query],
                    "database_targets": ["customers", "accounts"],
                    "comparison_type": "hybrid_comparison", 
                    "priority": "document_first"
                }
                
        except Exception as e:
            return {"error": f"Intent analysis failed: {str(e)}"}
    
    def _scout_database_relevance(self, intent_analysis: Dict, user_query: str) -> Dict[str, Any]:
        """Phase 2: Scout database structure for relevant tables/columns"""
        self._log_phase("🔍 Phase 2: Scouting database structure")
        
        if not intent_analysis.get('needs_database', False):
            self._log_phase("⏭️ Skipping database scouting - not needed for this query")
            return {"relevant_tables": [], "skip_database": True}
        
        if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
            return {"error": "Database not available for scouting"}
        
        try:
            # Get actual database structure
            db_overview = self.db_analyzer.analyze_database_structure()
            if "error" in db_overview:
                return {"error": f"Database structure analysis failed: {db_overview['error']}"}
            
            actual_tables = db_overview["tables"]
            target_concepts = intent_analysis.get('database_targets', [])
            key_concepts = intent_analysis.get('key_concepts', [])
            
            # Score table relevance
            relevant_tables = []
            
            for table_name, table_info in actual_tables.items():
                if table_name.startswith('pg_'):
                    continue
                
                relevance_score = self._calculate_table_relevance(
                    table_name, table_info, target_concepts, key_concepts, user_query
                )
                
                if relevance_score > 0:
                    relevant_tables.append({
                        "table_name": table_name,
                        "relevance_score": relevance_score,
                        "columns": table_info["columns"],
                        "row_count": table_info["row_count"],
                        "reasoning": self._explain_table_relevance(table_name, target_concepts, key_concepts)
                    })
            
            # Sort by relevance
            relevant_tables.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            self._log_phase(f"✅ Found {len(relevant_tables)} relevant tables")
            return {"relevant_tables": relevant_tables[:3]}  # Top 3 most relevant
            
        except Exception as e:
            return {"error": f"Database scouting failed: {str(e)}"}
    
    def _calculate_table_relevance(self, table_name: str, table_info: Dict, 
                                 target_concepts: List[str], key_concepts: List[str], 
                                 user_query: str) -> float:
        """Calculate how relevant a table is to the user query"""
        score = 0.0
        query_lower = user_query.lower()
        
        # Direct table name mentions
        if table_name.lower() in query_lower:
            score += 10.0
        
        # Target concept matching
        for concept in target_concepts:
            if concept.lower() in table_name.lower():
                score += 5.0
        
        # Column relevance
        columns = table_info.get("columns", [])
        for col in columns:
            col_name = col["name"].lower()
            
            # Key concept matching in columns
            for concept in key_concepts:
                if concept.lower() in col_name:
                    score += 3.0
            
            # Specific important columns
            if any(keyword in col_name for keyword in ['income', 'balance', 'amount', 'score', 'value']):
                if any(keyword in query_lower for keyword in ['income', 'money', 'balance', 'score', 'value', 'wealth']):
                    score += 2.0
            
            # Date columns for time-based queries
            if 'date' in col_name and any(keyword in query_lower for keyword in ['recent', 'last', 'this', 'month', 'year']):
                score += 1.0
        
        # Row count consideration (prefer tables with data)
        if table_info.get("row_count", 0) > 0:
            score += 1.0
        
        return score
    
    def _explain_table_relevance(self, table_name: str, target_concepts: List[str], key_concepts: List[str]) -> str:
        """Explain why a table is relevant"""
        reasons = []
        
        if table_name in ['customers', 'accounts', 'portfolios']:
            reasons.append(f"{table_name} contains financial customer data")
        
        for concept in target_concepts:
            if concept.lower() in table_name.lower():
                reasons.append(f"matches {concept} concept")
        
        return "; ".join(reasons) if reasons else "general business relevance"
    
    def _execute_smart_queries(self, intent_analysis: Dict, db_scouting: Dict, user_query: str) -> Dict[str, Any]:
        """Phase 3: Execute targeted queries on relevant tables"""
        self._log_phase("💻 Phase 3: Executing smart queries")
        
        results = {
            "document_results": None,
            "database_results": [],
            "document_concepts": []
        }
        
        # Document search first (if needed)
        if intent_analysis.get('needs_documents', False) and self.rag_processor:
            self._log_phase("📄 Searching documents...")
            try:
                doc_keywords = intent_analysis.get('document_keywords', [user_query])
                search_query = " ".join(doc_keywords)
                
                rag_result = self.rag_processor.process_query(search_query, use_reranking=False, final_results=3)
                results["document_results"] = rag_result
                
                # Extract key values/concepts from document results
                results["document_concepts"] = self._extract_document_concepts(rag_result.get('response', ''))
                self._log_phase(f"✅ Found document concepts: {results['document_concepts']}")
                
            except Exception as e:
                self._log_phase(f"❌ Document search failed: {str(e)}")
        
        # Database queries (if needed and relevant tables found)
        if (intent_analysis.get('needs_database', False) and 
            not db_scouting.get('skip_database', False) and
            db_scouting.get('relevant_tables')):
            
            self._log_phase("🗄️ Querying relevant database tables...")
            
            for table_info in db_scouting['relevant_tables']:
                table_name = table_info['table_name']
                
                # Generate context-aware query for this specific table
                table_query = self._generate_table_specific_query(
                    table_name, table_info, intent_analysis, results["document_concepts"], user_query
                )
                
                if table_query:
                    self._log_phase(f"🎯 Querying {table_name}: {table_query[:50]}...")
                    
                    query_result = self.db_analyzer.execute_safe_query(table_query)
                    if query_result.get('success', False):
                        results["database_results"].append({
                            "table": table_name,
                            "query": table_query,
                            "data": query_result.get('data', []),
                            "row_count": query_result.get('row_count', 0),
                            "relevance_reasoning": table_info['reasoning']
                        })
                        self._log_phase(f"✅ {table_name}: {query_result.get('row_count', 0)} results")
                    else:
                        self._log_phase(f"❌ {table_name} query failed: {query_result.get('error', 'unknown')}")
        
        return results
    
    def _extract_document_concepts(self, document_response: str) -> List[Dict[str, str]]:
        """Extract key numerical values and concepts from document text"""
        concepts = []
        
        # Simple pattern matching for now (could be enhanced with NLP)
        text = document_response.lower()
        
        # Extract income thresholds
        import re
        income_patterns = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:income|salary|annual)', text)
        for amount in income_patterns:
            concepts.append({
                "type": "income_threshold", 
                "value": amount.replace(',', ''),
                "context": "income requirement"
            })
        
        # Extract percentages
        percentage_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
        for pct in percentage_patterns:
            concepts.append({
                "type": "percentage",
                "value": pct,
                "context": "performance or allocation target"
            })
        
        # Extract credit score mentions
        credit_patterns = re.findall(r'credit\s+score[s]?\s+(?:above|over|higher\s+than)\s+(\d+)', text)
        for score in credit_patterns:
            concepts.append({
                "type": "credit_score_threshold",
                "value": score,
                "context": "credit requirement"
            })
        
        return concepts
    
    def _generate_table_specific_query(self, table_name: str, table_info: Dict, 
                                     intent_analysis: Dict, document_concepts: List[Dict], 
                                     user_query: str) -> Optional[str]:
        """Generate intelligent, targeted query for specific table"""
        
        columns = table_info['columns']
        column_names = [col['name'] for col in columns]
        
        # Build query based on document concepts and table structure
        query_parts = []
        where_conditions = []
        
        # Base SELECT
        if table_name == 'customers':
            # For customers, show relevant personal and financial info
            relevant_cols = []
            for col in ['customer_id', 'first_name', 'last_name', 'annual_income', 'credit_score', 'customer_segment']:
                if col in column_names:
                    relevant_cols.append(col)
            
            if relevant_cols:
                query_parts.append(f"SELECT {', '.join(relevant_cols)}")
                query_parts.append(f"FROM {table_name}")
                
                # Apply document-based filters
                for concept in document_concepts:
                    if concept['type'] == 'income_threshold' and 'annual_income' in column_names:
                        threshold = concept['value']
                        where_conditions.append(f"annual_income >= {threshold}")
                    elif concept['type'] == 'credit_score_threshold' and 'credit_score' in column_names:
                        threshold = concept['value']
                        where_conditions.append(f"credit_score >= {threshold}")
                
                # Default active customers filter
                if 'is_active' in column_names:
                    where_conditions.append("is_active = true")
        
        elif table_name == 'accounts':
            # For accounts, show balance and account info
            relevant_cols = []
            for col in ['account_id', 'customer_id', 'account_type', 'balance', 'account_status']:
                if col in column_names:
                    relevant_cols.append(col)
            
            if relevant_cols:
                query_parts.append(f"SELECT {', '.join(relevant_cols)}")
                query_parts.append(f"FROM {table_name}")
                
                # Apply filters based on query content
                if 'high' in user_query.lower() and 'balance' in column_names:
                    where_conditions.append("balance > 100000")  # High balance threshold
                
                if 'account_status' in column_names:
                    where_conditions.append("account_status = 'active'")
        
        elif table_name == 'portfolios':
            # For portfolios, show performance and value info
            relevant_cols = []
            for col in ['portfolio_id', 'customer_id', 'portfolio_name', 'total_value', 'ytd_return_percentage', 'risk_tolerance']:
                if col in column_names:
                    relevant_cols.append(col)
            
            if relevant_cols:
                query_parts.append(f"SELECT {', '.join(relevant_cols)}")
                query_parts.append(f"FROM {table_name}")
                
                # Apply performance filters based on document concepts
                for concept in document_concepts:
                    if concept['type'] == 'percentage' and 'ytd_return_percentage' in column_names:
                        # Use percentage from document as comparison
                        pct = float(concept['value'])
                        if 'performance' in user_query.lower() or 'return' in user_query.lower():
                            where_conditions.append(f"ytd_return_percentage >= {pct}")
        
        elif table_name == 'loans':
            # For loans, show loan details and status
            relevant_cols = []
            for col in ['loan_id', 'customer_id', 'loan_type', 'loan_amount', 'outstanding_balance', 'loan_status']:
                if col in column_names:
                    relevant_cols.append(col)
            
            if relevant_cols:
                query_parts.append(f"SELECT {', '.join(relevant_cols)}")
                query_parts.append(f"FROM {table_name}")
                
                if 'loan_status' in column_names:
                    where_conditions.append("loan_status = 'active'")
        
        else:
            # Generic approach for other tables
            query_parts.append(f"SELECT *")
            query_parts.append(f"FROM {table_name}")
        
        # Add WHERE conditions
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))
        
        # Add LIMIT
        query_parts.append("LIMIT 10")
        
        final_query = " ".join(query_parts)
        self._log_phase(f"🎯 Generated query for {table_name}")
        
        return final_query
    
    def _synthesize_results(self, intent_analysis: Dict, query_results: Dict, user_query: str) -> Dict[str, Any]:
        """Phase 4: Synthesize document and database results into comprehensive answer"""
        self._log_phase("🔀 Phase 4: Synthesizing results")
        
        try:
            synthesis_prompt = f"""You are a business analyst. Combine document analysis with database results to answer this query comprehensively.

User Question: "{user_query}"

Document Results: {query_results.get('document_results', {}).get('response', 'No document results')}

Database Results:
{self._format_db_results_for_synthesis(query_results.get('database_results', []))}

Document Concepts Extracted: {query_results.get('document_concepts', [])}

Task: Provide a comprehensive business answer that:
1. Compares document strategy/goals with actual database reality
2. Identifies gaps, matches, or insights
3. Provides actionable business recommendations
4. Uses specific numbers from database when available
5. References document context appropriately

Format as business-friendly response with clear sections and insights."""

            if not os.getenv('GOOGLE_API_KEY_SOL_4'):
                return self._create_basic_synthesis(query_results, user_query)
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(synthesis_prompt)
            
            final_answer = response.text.strip()
            
            self._log_phase("✅ Synthesis completed")
            
            return {
                "success": True,
                "response": final_answer,
                "processing_log": self.processing_log,
                "source_breakdown": {
                    "documents_used": query_results.get('document_results') is not None,
                    "database_tables_queried": len(query_results.get('database_results', [])),
                    "concepts_extracted": len(query_results.get('document_concepts', []))
                }
            }
            
        except Exception as e:
            return self._create_error_response(f"Result synthesis failed: {str(e)}")
    
    def _format_db_results_for_synthesis(self, db_results: List[Dict]) -> str:
        """Format database results for AI synthesis"""
        if not db_results:
            return "No relevant database results found."
        
        formatted = ""
        for result in db_results:
            table = result['table']
            data = result['data']
            count = result['row_count']
            
            formatted += f"\n{table.title()} Table ({count} records):\n"
            
            if data:
                # Show first few records with key info
                for i, record in enumerate(data[:3], 1):
                    formatted += f"  Record {i}: "
                    key_fields = []
                    for key, value in record.items():
                        if any(keyword in key.lower() for keyword in ['name', 'income', 'score', 'balance', 'amount', 'value']):
                            key_fields.append(f"{key}={value}")
                    formatted += ", ".join(key_fields) + "\n"
                
                if count > 3:
                    formatted += f"  ... and {count - 3} more records\n"
            
            formatted += "\n"
        
        return formatted
    
    def _create_basic_synthesis(self, query_results: Dict, user_query: str) -> Dict[str, Any]:
        """Create basic synthesis when AI is not available"""
        response = "## Hybrid Query Results\n\n"
        
        # Document section
        if query_results.get('document_results'):
            response += "### 📄 Document Analysis\n"
            response += query_results['document_results'].get('response', 'No document content found')
            response += "\n\n"
        
        # Database section
        if query_results.get('database_results'):
            response += "### 🗄️ Database Results\n"
            for result in query_results['database_results']:
                table = result['table']
                count = result['row_count']
                response += f"**{table.title()} Table**: {count} relevant records found\n"
                
                if result['data']:
                    response += f"Sample data from {table}:\n"
                    for i, record in enumerate(result['data'][:2], 1):
                        response += f"  {i}. "
                        key_values = []
                        for k, v in record.items():
                            if any(kw in k.lower() for kw in ['name', 'income', 'score', 'balance']):
                                key_values.append(f"{k}: {v}")
                        response += ", ".join(key_values) + "\n"
                response += "\n"
        
        return {
            "success": True,
            "response": response,
            "processing_log": self.processing_log,
            "source_breakdown": {
                "documents_used": query_results.get('document_results') is not None,
                "database_tables_queried": len(query_results.get('database_results', [])),
                "concepts_extracted": len(query_results.get('document_concepts', []))
            }
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "response": f"❌ Hybrid query failed: {error_message}",
            "processing_log": self.processing_log
        }
    
    def _log_phase(self, message: str):
        """Log processing phase for debugging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        print(log_entry)  # Optional: remove for production
    
    def _log_to_session(self, session_id: str, user_query: str, response: Dict[str, Any]):
        """Log hybrid query to session"""
        try:
            if self.session_manager:
                self.session_manager.add_message(
                    session_id,
                    'user',
                    f"Hybrid Query: {user_query}",
                    {
                        "query_type": "hybrid_agent",
                        "processing_phases": len(self.processing_log)
                    }
                )
                self.session_manager.add_message(
                    session_id,
                    'assistant', 
                    response.get('response', ''),
                    {
                        "query_type": "hybrid_agent_response",
                        "success": response.get('success', False),
                        "sources_used": response.get('source_breakdown', {})
                    }
                )
        except Exception as e:
            self._log_phase(f"Session logging failed: {str(e)}")
    
    def get_processing_log(self) -> List[str]:
        """Get detailed processing log for debugging"""
        return self.processing_log.copy()