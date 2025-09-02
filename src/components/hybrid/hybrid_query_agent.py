import os
import json
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai
from datetime import datetime
import sys

# Import the database tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from components.database.database_tools import DatabaseTools


class HybridQueryAgent:
    """
    Intelligent agent that processes hybrid queries combining documents and database
    Uses multi-phase analysis to prevent errors and provide comprehensive answers
    """
    
    def __init__(self, rag_processor=None, db_analyzer=None, session_manager=None):
        self.rag_processor = rag_processor
        self.db_analyzer = db_analyzer  
        self.session_manager = session_manager
        
        # Initialize MCP-style database tools
        self.db_tools = DatabaseTools(db_analyzer)
        
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
            
            # Phase 1.5: Extract document concepts if needed
            if intent_analysis.get('needs_documents', False) and self.rag_processor:
                doc_concepts = self._extract_initial_document_concepts(user_query, intent_analysis)
                intent_analysis['document_concepts'] = doc_concepts
            
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
            
            model = genai.GenerativeModel('gemini-2.5-flash')
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
        """Phase 2: Scout database structure using database tools"""
        self._log_phase("🔍 Phase 2: Using database discovery tool")
        
        if not intent_analysis.get('needs_database', False):
            self._log_phase("⏭️ Skipping database scouting - not needed for this query")
            return {"relevant_tables": [], "skip_database": True}
        
        # Use Tool 1: Database Discovery
        discovery_result = self.db_tools.analyze_database_structure()
        
        if not discovery_result.get("success", False):
            return {"error": f"Database discovery failed: {discovery_result.get('error', 'Unknown error')}"}
        
        available_tables = discovery_result.get("table_names", [])
        tables_info = discovery_result.get("tables", {})
        
        self._log_phase(f"🔍 Discovered {len(available_tables)} tables: {', '.join(available_tables)}")
        
        # Analyze each table for relevance using Tool 2
        relevant_tables = []
        document_concepts = intent_analysis.get('document_concepts', [])
        
        for table_name in available_tables:
            self._log_phase(f"🔬 Analyzing {table_name} table...")
            
            # Use Tool 2: Table Content Analysis
            table_analysis = self.db_tools.analyze_table_content(table_name, document_concepts)
            
            if table_analysis.get("success", False):
                relevance_score = table_analysis.get("relevance_score", 0.0)
                
                if relevance_score > 0:  # Only include relevant tables
                    relevant_tables.append({
                        "table_name": table_name,
                        "relevance_score": relevance_score,
                        "business_context": table_analysis.get("business_context", ""),
                        "table_info": table_analysis.get("table_info", {}),
                        "query_potential": table_analysis.get("query_potential", {})
                    })
                    
                    self._log_phase(f"✅ {table_name}: relevance {relevance_score:.1f}")
                else:
                    self._log_phase(f"⏭️ {table_name}: not relevant (score {relevance_score:.1f})")
            else:
                self._log_phase(f"❌ {table_name}: analysis failed")
        
        # Sort by relevance score
        relevant_tables.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        self._log_phase(f"🎯 Selected {len(relevant_tables)} relevant tables for querying")
        
        return {"relevant_tables": relevant_tables[:3]}  # Top 3 most relevant
    
    def _execute_smart_queries(self, intent_analysis: Dict, db_scouting: Dict, user_query: str) -> Dict[str, Any]:
        """Phase 3: Execute targeted queries using database tools"""
        self._log_phase("💻 Phase 3: Executing smart queries with tools")
        
        results = {
            "document_results": None,
            "database_results": [],
            "document_concepts": []
        }
        
        # Document search first (if needed)
        if intent_analysis.get('needs_documents', False) and self.rag_processor:
            self._log_phase("📄 Using document search...")
            try:
                doc_keywords = intent_analysis.get('document_keywords', [user_query])
                search_query = " ".join(doc_keywords)
                
                rag_result = self.rag_processor.process_query(search_query, use_reranking=False, final_results=3)
                results["document_results"] = rag_result
                
                # Use Tool 5: Extract document concepts
                concept_extraction = self.db_tools.extract_document_concepts(
                    rag_result.get('response', ''), user_query
                )
                
                if concept_extraction.get("success", False):
                    results["document_concepts"] = concept_extraction.get("concepts", [])
                    self._log_phase(f"✅ Extracted {len(results['document_concepts'])} document concepts")
                else:
                    self._log_phase("❌ Document concept extraction failed")
                
            except Exception as e:
                self._log_phase(f"❌ Document search failed: {str(e)}")
        
        # Database queries using tools (if needed and relevant tables found)
        if (intent_analysis.get('needs_database', False) and 
            not db_scouting.get('skip_database', False) and
            db_scouting.get('relevant_tables')):
            
            self._log_phase("🗄️ Using smart query tools on relevant tables...")
            
            for table_info in db_scouting['relevant_tables']:
                table_name = table_info['table_name']
                query_intent = intent_analysis.get('comparison_type', 'data_analysis')
                
                self._log_phase(f"🎯 Using Tool 3 on {table_name}...")
                
                # Use Tool 3: Smart Query Executor
                query_result = self.db_tools.execute_targeted_query(
                    table_name=table_name,
                    query_intent=query_intent,
                    document_concepts=results["document_concepts"],
                    user_query=user_query
                )
                
                if query_result.get('success', False):
                    results["database_results"].append({
                        "table": table_name,
                        "query": query_result.get('query_used', ''),
                        "data": query_result.get('data', []),
                        "row_count": query_result.get('row_count', 0),
                        "business_interpretation": query_result.get('business_interpretation', ''),
                        "relevance_score": query_result.get('relevance_score', 0.0)
                    })
                    self._log_phase(f"✅ {table_name}: {query_result.get('row_count', 0)} results (relevance: {query_result.get('relevance_score', 0):.1f})")
                else:
                    self._log_phase(f"❌ {table_name} query failed: {query_result.get('error', 'unknown')}")
        
        return results
    
    
    def _synthesize_results(self, intent_analysis: Dict, query_results: Dict, user_query: str) -> Dict[str, Any]:
        """Phase 4: Synthesize results using Tool 4 - Result Correlator"""
        self._log_phase("🔀 Phase 4: Using Tool 4 - Result Correlator")
        
        try:
            document_content = ""
            if query_results.get('document_results'):
                document_content = query_results['document_results'].get('response', '')
            
            database_results = query_results.get('database_results', [])
            
            # Use Tool 4: Result Correlator
            self._log_phase("🔧 Applying correlation tool...")
            correlation_result = self.db_tools.correlate_results(
                document_content=document_content,
                database_results=database_results,
                user_query=user_query
            )
            
            if not correlation_result.get("success", False):
                # Fallback to basic synthesis
                self._log_phase("⚠️ Correlation tool failed, using basic synthesis")
                return self._create_basic_synthesis(query_results, user_query)
            
            # Format comprehensive response using correlation results
            final_response = self._format_tool_based_response(correlation_result, query_results)
            
            self._log_phase("✅ Tool-based synthesis completed")
            
            # Combine processing logs from all tools
            all_logs = self.processing_log + self.db_tools.get_tools_log()
            
            return {
                "success": True,
                "response": final_response,
                "processing_log": all_logs,
                "source_breakdown": {
                    "documents_used": query_results.get('document_results') is not None,
                    "database_tables_queried": len(query_results.get('database_results', [])),
                    "concepts_extracted": len(query_results.get('document_concepts', [])),
                    "tools_used": ["database_discovery", "table_analyzer", "query_executor", "result_correlator"],
                    "correlation_confidence": correlation_result.get("correlation_confidence", "N/A")
                },
                "correlation_analysis": correlation_result
            }
            
        except Exception as e:
            return self._create_error_response(f"Tool-based synthesis failed: {str(e)}")
    
    def _format_tool_based_response(self, correlation_result: Dict, query_results: Dict) -> str:
        """Format final response using tool-based correlation analysis"""
        response = "# 🤖 Smart Agent Analysis\n\n"
        
        # Overview from correlation tool
        correlation = correlation_result.get("correlation", "")
        if correlation:
            response += f"## 🔍 Document vs Database Analysis\n{correlation}\n\n"
        
        # Key insights from tools
        insights = correlation_result.get("insights", [])
        if insights:
            response += "## 💡 Key Business Insights\n"
            for insight in insights:
                response += f"• {insight}\n"
            response += "\n"
        
        # Strategy gaps identified by tools
        gaps = correlation_result.get("gaps", [])
        if gaps:
            response += "## ⚠️ Strategy-Reality Gaps\n"
            for gap in gaps:
                response += f"• {gap}\n"
            response += "\n"
        
        # Areas where strategy matches reality
        matches = correlation_result.get("matches", [])
        if matches:
            response += "## ✅ Strategic Alignment\n"
            for match in matches:
                response += f"• {match}\n"
            response += "\n"
        
        # Actionable recommendations from tools
        recommendations = correlation_result.get("recommendations", [])
        if recommendations:
            response += "## 🎯 Recommended Actions\n"
            for i, rec in enumerate(recommendations, 1):
                response += f"{i}. {rec}\n"
            response += "\n"
        
        # Supporting database evidence
        db_results = query_results.get('database_results', [])
        if db_results:
            response += "## 📊 Supporting Database Evidence\n"
            for result in db_results:
                table = result['table']
                count = result['row_count']
                interpretation = result.get('business_interpretation', '')
                response += f"**{table.title()}**: {count} records"
                if interpretation:
                    response += f" - {interpretation}"
                response += "\n"
        
        return response
    
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
    
    def _extract_initial_document_concepts(self, user_query: str, intent_analysis: Dict) -> List[Dict]:
        """Extract document concepts early for database relevance scoring"""
        try:
            if not self.rag_processor:
                return []
            
            # Quick document search to get concepts
            doc_keywords = intent_analysis.get('document_keywords', [user_query])
            search_query = " ".join(doc_keywords)
            
            rag_result = self.rag_processor.process_query(search_query, use_reranking=False, final_results=2)
            document_content = rag_result.get('response', '')
            
            # Use Tool 5 to extract concepts
            concept_result = self.db_tools.extract_document_concepts(document_content, user_query)
            
            if concept_result.get("success", False):
                return concept_result.get("concepts", [])
            else:
                return []
                
        except Exception as e:
            self._log_phase(f"Early concept extraction failed: {str(e)}")
            return []
    
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