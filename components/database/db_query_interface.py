import os
import json
from typing import Dict, Any, List, Optional, Tuple
from .db_analyzer import DatabaseAnalyzer
from .database_manager import DatabaseManager
import google.generativeai as genai


class DatabaseQueryInterface:
    def __init__(self, session_manager=None):
        self.db_analyzer = DatabaseAnalyzer()
        self.db_manager = DatabaseManager()
        self.session_manager = session_manager
        self.query_history = []
        
    def get_database_overview(self) -> Dict[str, Any]:
        """Get comprehensive database overview"""
        try:
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
            # Convert to SQL
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
            
            # Format results
            if "data" in query_result and query_result["data"]:
                response = f"✅ **Query Results** ({query_result['row_count']} rows)\n\n"
                
                # Show column headers
                if query_result["data"]:
                    columns = list(query_result["data"][0].keys())
                    response += "| " + " | ".join(columns) + " |\n"
                    response += "|" + "|".join(["---"] * len(columns)) + "|\n"
                    
                    # Show data rows (limit for display)
                    for i, row in enumerate(query_result["data"][:10]):
                        values = [str(row.get(col, "")) for col in columns]
                        response += "| " + " | ".join(values) + " |\n"
                    
                    if query_result['row_count'] > 10:
                        response += f"\n*Showing first 10 of {query_result['row_count']} total rows*\n"
                
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