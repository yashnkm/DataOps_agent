"""
MCP-Style Database Analysis Function Tools
Modular toolkit for intelligent database discovery and analysis
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
import google.generativeai as genai
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine


class DatabaseTools:
    """
    Collection of MCP-style function tools for database analysis
    Each tool has a focused responsibility and can be chained together
    """
    
    def __init__(self, db_analyzer=None):
        self.db_analyzer = db_analyzer
        self.tools_log = []
        
        # Configure Gemini for AI analysis
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
    
    def _log_tool_action(self, tool_name: str, message: str):
        """Log tool actions for transparency"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] 🔧 {tool_name}: {message}"
        self.tools_log.append(log_entry)
        print(log_entry)
    
    def analyze_database_structure(self) -> Dict[str, Any]:
        """
        Tool 1: Database Discovery
        Discovers all available tables, columns, relationships, and metadata
        """
        self._log_tool_action("database_discovery", "Scanning database structure...")
        
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                return {
                    "success": False,
                    "error": "Database connection not available",
                    "tables": {},
                    "relationships": [],
                    "metadata": {}
                }
            
            # Get comprehensive database analysis
            analysis = self.db_analyzer.analyze_database_structure()
            
            if "error" in analysis:
                return {
                    "success": False,
                    "error": analysis["error"],
                    "tables": {},
                    "relationships": [],
                    "metadata": {}
                }
            
            # Extract and organize information
            tables = analysis.get("tables", {})
            relationships = analysis.get("relationships", [])
            
            # Filter out system tables
            user_tables = {name: info for name, info in tables.items() 
                          if not name.startswith('pg_') and not name.startswith('information_schema')}
            
            # Create metadata summary
            metadata = {
                "total_tables": len(user_tables),
                "total_relationships": len(relationships),
                "tables_with_data": len([t for t in user_tables.values() if t.get('row_count', 0) > 0]),
                "database_type": "postgresql",
                "discovery_timestamp": datetime.now().isoformat()
            }
            
            self._log_tool_action("database_discovery", f"Found {len(user_tables)} tables, {len(relationships)} relationships")
            
            return {
                "success": True,
                "tables": user_tables,
                "relationships": relationships,
                "metadata": metadata,
                "table_names": list(user_tables.keys())
            }
            
        except Exception as e:
            self._log_tool_action("database_discovery", f"Failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "tables": {},
                "relationships": [],
                "metadata": {}
            }
    
    def analyze_table_content(self, table_name: str, document_concepts: List[Dict] = None) -> Dict[str, Any]:
        """
        Tool 2: Table Content Analysis  
        Deep analysis of specific table structure, sample data, and business context
        """
        self._log_tool_action("table_analyzer", f"Analyzing {table_name} table...")
        
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                return {
                    "success": False,
                    "error": "Database connection not available",
                    "table_info": {},
                    "business_context": "",
                    "sample_data": []
                }
            
            # Get table structure
            db_analysis = self.db_analyzer.analyze_database_structure()
            if "error" in db_analysis:
                return {
                    "success": False,
                    "error": db_analysis["error"],
                    "table_info": {},
                    "business_context": "",
                    "sample_data": []
                }
            
            tables = db_analysis.get("tables", {})
            if table_name not in tables:
                return {
                    "success": False,
                    "error": f"Table '{table_name}' not found in database",
                    "table_info": {},
                    "business_context": "",
                    "sample_data": []
                }
            
            table_info = tables[table_name]
            columns = table_info.get("columns", [])
            row_count = table_info.get("row_count", 0)
            
            # Get sample data if table has records
            sample_data = []
            if row_count > 0:
                sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                sample_result = self.db_analyzer.execute_safe_query(sample_query)
                if sample_result.get("success", False):
                    sample_data = sample_result.get("data", [])
            
            # Generate business context using AI
            business_context = self._generate_business_context(table_name, columns, sample_data, document_concepts)
            
            # Calculate relevance to document concepts
            relevance_score = self._calculate_relevance_to_concepts(columns, document_concepts) if document_concepts else 0.0
            
            self._log_tool_action("table_analyzer", f"{table_name}: {len(columns)} columns, {row_count} rows, relevance: {relevance_score:.2f}")
            
            return {
                "success": True,
                "table_name": table_name,
                "table_info": table_info,
                "business_context": business_context,
                "sample_data": sample_data,
                "relevance_score": relevance_score,
                "column_analysis": self._analyze_column_types(columns),
                "query_potential": self._assess_query_potential(columns, document_concepts)
            }
            
        except Exception as e:
            self._log_tool_action("table_analyzer", f"Failed analyzing {table_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "table_info": {},
                "business_context": "",
                "sample_data": []
            }
    
    def execute_targeted_query(self, table_name: str, query_intent: str, document_concepts: List[Dict] = None, 
                             user_query: str = "") -> Dict[str, Any]:
        """
        Tool 3: Smart Query Executor
        Executes intelligent query on specific table using document concepts and intent
        """
        self._log_tool_action("query_executor", f"Querying {table_name} with intent: {query_intent}")
        
        try:
            if not self.db_analyzer or self.db_analyzer.connection_status != "connected":
                return {
                    "success": False,
                    "error": "Database connection not available",
                    "data": [],
                    "query_used": "",
                    "business_interpretation": ""
                }
            
            # First analyze table structure
            table_analysis = self.analyze_table_content(table_name, document_concepts)
            if not table_analysis.get("success", False):
                return {
                    "success": False,
                    "error": table_analysis.get("error", "Table analysis failed"),
                    "data": [],
                    "query_used": "",
                    "business_interpretation": ""
                }
            
            table_info = table_analysis["table_info"]
            columns = table_info.get("columns", [])
            column_analysis = table_analysis.get("column_analysis", {})
            
            # Generate intelligent query based on table structure and concepts
            smart_query = self._generate_context_aware_query(
                table_name, columns, column_analysis, document_concepts, query_intent, user_query
            )
            
            if not smart_query:
                return {
                    "success": False,
                    "error": "Could not generate appropriate query for this table",
                    "data": [],
                    "query_used": "",
                    "business_interpretation": ""
                }
            
            # Execute the generated query
            query_result = self.db_analyzer.execute_safe_query(smart_query)
            
            if not query_result.get("success", False):
                return {
                    "success": False,
                    "error": query_result.get("error", "Query execution failed"),
                    "data": [],
                    "query_used": smart_query,
                    "business_interpretation": ""
                }
            
            # Generate business interpretation of results
            business_interpretation = self._interpret_query_results(
                query_result.get("data", []), table_name, query_intent, document_concepts
            )
            
            self._log_tool_action("query_executor", f"Retrieved {query_result.get('row_count', 0)} records from {table_name}")
            
            return {
                "success": True,
                "table_name": table_name,
                "data": query_result.get("data", []),
                "row_count": query_result.get("row_count", 0),
                "query_used": smart_query,
                "business_interpretation": business_interpretation,
                "relevance_score": table_analysis.get("relevance_score", 0.0)
            }
            
        except Exception as e:
            self._log_tool_action("query_executor", f"Failed querying {table_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "query_used": "",
                "business_interpretation": ""
            }
    
    def correlate_results(self, document_content: str, database_results: List[Dict], 
                         user_query: str) -> Dict[str, Any]:
        """
        Tool 4: Result Correlator
        Correlates document insights with database findings for comprehensive business analysis
        """
        self._log_tool_action("result_correlator", "Correlating document and database findings...")
        
        try:
            if not database_results:
                return {
                    "success": False,
                    "error": "No database results to correlate",
                    "correlation": "",
                    "insights": [],
                    "recommendations": []
                }
            
            # Use AI to correlate results intelligently
            correlation_analysis = self._ai_correlate_results(document_content, database_results, user_query)
            
            self._log_tool_action("result_correlator", "Correlation analysis completed")
            
            return {
                "success": True,
                "correlation": correlation_analysis.get("correlation", ""),
                "insights": correlation_analysis.get("insights", []),
                "recommendations": correlation_analysis.get("recommendations", []),
                "gaps_identified": correlation_analysis.get("gaps", []),
                "matches_found": correlation_analysis.get("matches", [])
            }
            
        except Exception as e:
            self._log_tool_action("result_correlator", f"Correlation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "correlation": "",
                "insights": [],
                "recommendations": []
            }
    
    def extract_document_concepts(self, document_content: str, user_query: str) -> Dict[str, Any]:
        """
        Tool 5: Document Concept Extractor
        Extracts key business concepts, values, and targets from document content
        """
        self._log_tool_action("concept_extractor", "Extracting concepts from documents...")
        
        try:
            # Use AI to extract relevant concepts
            concepts = self._ai_extract_concepts(document_content, user_query)
            
            self._log_tool_action("concept_extractor", f"Extracted {len(concepts)} concepts")
            
            return {
                "success": True,
                "concepts": concepts,
                "document_summary": document_content[:500] + "..." if len(document_content) > 500 else document_content,
                "extraction_confidence": self._calculate_extraction_confidence(concepts)
            }
            
        except Exception as e:
            self._log_tool_action("concept_extractor", f"Extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "concepts": [],
                "document_summary": "",
                "extraction_confidence": 0.0
            }
    
    # Helper methods for AI-powered analysis
    
    def _generate_business_context(self, table_name: str, columns: List[Dict], 
                                 sample_data: List[Dict], document_concepts: List[Dict] = None) -> str:
        """Generate business context explanation for table using AI"""
        try:
            if not os.getenv('GOOGLE_API_KEY_SOL_4'):
                return f"Table {table_name} with {len(columns)} columns"
            
            column_info = []
            for col in columns:
                col_desc = f"{col['name']} ({col['type']})"
                if not col.get('nullable', True):
                    col_desc += " [Required]"
                column_info.append(col_desc)
            
            sample_text = ""
            if sample_data:
                sample_text = f"\nSample data: {json.dumps(sample_data[0], default=str)}"
            
            prompt = f"""Analyze this database table and explain its business purpose in simple terms:

Table Name: {table_name}
Columns: {', '.join(column_info)}
{sample_text}

Provide a concise business explanation:
1. What type of business data this table stores
2. What business purpose it serves
3. Key information it contains
4. How it might be used in business operations

Keep response under 100 words, business-friendly language."""

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            return response.text.strip()
            
        except Exception as e:
            return f"Business context analysis failed: {str(e)}"
    
    def _analyze_column_types(self, columns: List[Dict]) -> Dict[str, List[str]]:
        """Categorize columns by business data types"""
        categories = {
            "identifiers": [],
            "financial": [],
            "temporal": [],
            "textual": [],
            "status": [],
            "numerical": [],
            "other": []
        }
        
        for col in columns:
            name = col["name"].lower()
            data_type = col["type"].lower()
            
            if any(suffix in name for suffix in ['_id', 'id']):
                categories["identifiers"].append(col["name"])
            elif any(keyword in name for keyword in ['amount', 'balance', 'value', 'price', 'cost', 'income', 'salary']):
                categories["financial"].append(col["name"])
            elif any(keyword in name for keyword in ['date', 'time', 'created', 'updated', 'timestamp']):
                categories["temporal"].append(col["name"])
            elif any(keyword in name for keyword in ['status', 'state', 'active', 'enabled', 'type', 'category']):
                categories["status"].append(col["name"])
            elif 'text' in data_type or 'char' in data_type or 'varchar' in data_type:
                categories["textual"].append(col["name"])
            elif any(num_type in data_type for num_type in ['int', 'decimal', 'numeric', 'float']):
                categories["numerical"].append(col["name"])
            else:
                categories["other"].append(col["name"])
        
        return categories
    
    def _calculate_relevance_to_concepts(self, columns: List[Dict], document_concepts: List[Dict]) -> float:
        """Calculate how relevant table is to document concepts"""
        if not document_concepts:
            return 0.0
        
        relevance_score = 0.0
        column_names = [col["name"].lower() for col in columns]
        
        for concept in document_concepts:
            concept_type = concept.get("type", "").lower()
            concept_context = concept.get("context", "").lower()
            
            # Score based on concept types
            if concept_type == "income_threshold" and any('income' in col for col in column_names):
                relevance_score += 10.0
            elif concept_type == "credit_score_threshold" and any('score' in col for col in column_names):
                relevance_score += 10.0
            elif concept_type == "percentage" and any('return' in col or 'rate' in col for col in column_names):
                relevance_score += 5.0
            elif any(keyword in " ".join(column_names) for keyword in concept_context.split()):
                relevance_score += 3.0
        
        return min(relevance_score, 100.0)  # Cap at 100
    
    def _assess_query_potential(self, columns: List[Dict], document_concepts: List[Dict] = None) -> Dict[str, Any]:
        """Assess what types of queries would be useful for this table"""
        column_analysis = self._analyze_column_types(columns)
        
        potential = {
            "can_filter_by_value": len(column_analysis["financial"]) > 0 or len(column_analysis["numerical"]) > 0,
            "can_filter_by_date": len(column_analysis["temporal"]) > 0,
            "can_filter_by_status": len(column_analysis["status"]) > 0,
            "can_search_text": len(column_analysis["textual"]) > 0,
            "has_relationships": len(column_analysis["identifiers"]) > 1,
            "primary_value_columns": column_analysis["financial"] + column_analysis["numerical"],
            "filterable_columns": column_analysis["status"] + column_analysis["temporal"],
            "searchable_columns": column_analysis["textual"]
        }
        
        return potential
    
    def _generate_context_aware_query(self, table_name: str, columns: List[Dict], 
                                    column_analysis: Dict, document_concepts: List[Dict],
                                    query_intent: str, user_query: str) -> Optional[str]:
        """Generate intelligent query based on table structure and document concepts"""
        
        # Build SELECT clause with relevant columns
        column_names = [col["name"] for col in columns]
        
        # Choose most relevant columns for display
        display_columns = []
        
        # Always include identifiers
        display_columns.extend(column_analysis.get("identifiers", [])[:2])
        
        # Include textual columns that might contain names or descriptions
        text_cols = column_analysis.get("textual", [])
        name_cols = [col for col in text_cols if any(keyword in col.lower() for keyword in ['name', 'title', 'description'])]
        display_columns.extend(name_cols[:2])
        
        # Include financial/numerical columns based on document concepts
        if document_concepts:
            for concept in document_concepts:
                if concept.get("type") == "income_threshold":
                    income_cols = [col for col in column_analysis.get("financial", []) if 'income' in col.lower()]
                    display_columns.extend(income_cols[:1])
                elif concept.get("type") == "credit_score_threshold":
                    score_cols = [col for col in column_names if 'score' in col.lower()]
                    display_columns.extend(score_cols[:1])
        
        # Add other important financial/numerical columns
        financial_cols = column_analysis.get("financial", [])
        display_columns.extend([col for col in financial_cols if col not in display_columns][:3])
        
        # Add status columns
        status_cols = column_analysis.get("status", [])
        display_columns.extend([col for col in status_cols if col not in display_columns][:2])
        
        # Remove duplicates and limit
        display_columns = list(dict.fromkeys(display_columns))[:8]  # Max 8 columns
        
        if not display_columns:
            display_columns = column_names[:5]  # Fallback to first 5 columns
        
        # Build WHERE conditions based on document concepts
        where_conditions = []
        
        for concept in document_concepts or []:
            if concept.get("type") == "income_threshold":
                income_cols = [col for col in column_names if 'income' in col.lower()]
                if income_cols:
                    threshold = concept.get("value", "").replace(',', '')
                    try:
                        threshold_num = float(threshold)
                        where_conditions.append(f"{income_cols[0]} >= {threshold_num}")
                    except ValueError:
                        pass
            
            elif concept.get("type") == "credit_score_threshold":
                score_cols = [col for col in column_names if 'score' in col.lower()]
                if score_cols:
                    threshold = concept.get("value", "")
                    try:
                        threshold_num = float(threshold)
                        where_conditions.append(f"{score_cols[0]} >= {threshold_num}")
                    except ValueError:
                        pass
        
        # Add common business filters
        if 'is_active' in column_names:
            where_conditions.append("is_active = true")
        elif any('active' in col.lower() for col in column_names):
            active_cols = [col for col in column_names if 'active' in col.lower()]
            where_conditions.append(f"{active_cols[0]} = true")
        
        if any('status' in col.lower() for col in column_names):
            status_cols = [col for col in column_names if 'status' in col.lower()]
            # Assume 'active' is a good default status
            where_conditions.append(f"{status_cols[0]} = 'active'")
        
        # Build final query
        query_parts = [f"SELECT {', '.join(display_columns)}"]
        query_parts.append(f"FROM {table_name}")
        
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))
        
        query_parts.append("LIMIT 10")
        
        final_query = " ".join(query_parts)
        
        self._log_tool_action("query_executor", f"Generated query: {final_query[:60]}...")
        
        return final_query
    
    def _interpret_query_results(self, data: List[Dict], table_name: str, 
                               query_intent: str, document_concepts: List[Dict]) -> str:
        """Generate business interpretation of query results"""
        if not data:
            return f"No records found in {table_name} matching the criteria"
        
        row_count = len(data)
        
        # Extract key insights from the data
        insights = []
        
        # Analyze numerical patterns
        for key, value in data[0].items():
            if isinstance(value, (int, float)):
                values = [row.get(key, 0) for row in data if isinstance(row.get(key), (int, float))]
                if values:
                    avg_val = sum(values) / len(values)
                    max_val = max(values)
                    min_val = min(values)
                    
                    if 'income' in key.lower() or 'salary' in key.lower():
                        insights.append(f"Income range: ${min_val:,.0f} - ${max_val:,.0f} (avg: ${avg_val:,.0f})")
                    elif 'balance' in key.lower() or 'amount' in key.lower():
                        insights.append(f"Balance range: ${min_val:,.0f} - ${max_val:,.0f} (avg: ${avg_val:,.0f})")
                    elif 'score' in key.lower():
                        insights.append(f"Score range: {min_val} - {max_val} (avg: {avg_val:.1f})")
        
        # Create business summary
        summary = f"Found {row_count} records in {table_name}. "
        if insights:
            summary += " ".join(insights)
        
        return summary
    
    def _ai_correlate_results(self, document_content: str, database_results: List[Dict], 
                            user_query: str) -> Dict[str, Any]:
        """Use AI to correlate document and database information"""
        try:
            if not os.getenv('GOOGLE_API_KEY_SOL_4'):
                return {
                    "correlation": "AI correlation not available - API key not configured",
                    "insights": [],
                    "recommendations": [],
                    "gaps": [],
                    "matches": []
                }
            
            # Format database results for AI analysis
            db_summary = self._format_db_results_for_ai(database_results)
            
            prompt = f"""You are a business analyst. Correlate document strategy with database reality.

User Question: "{user_query}"

Document Content (Strategy/Goals):
{document_content[:1000]}

Database Reality:
{db_summary}

Provide JSON response with:
{{
  "correlation": "Overall analysis comparing document goals with database reality",
  "insights": ["Key insight 1", "Key insight 2"],
  "recommendations": ["Business recommendation 1", "Business recommendation 2"],
  "gaps": ["Gap between strategy and reality 1"],
  "matches": ["Where strategy aligns with current data 1"]
}}

Return ONLY valid JSON."""

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            try:
                correlation_data = json.loads(response.text.strip())
                return correlation_data
            except json.JSONDecodeError:
                return {
                    "correlation": response.text.strip(),
                    "insights": [],
                    "recommendations": [],
                    "gaps": [],
                    "matches": []
                }
                
        except Exception as e:
            return {
                "correlation": f"Correlation analysis failed: {str(e)}",
                "insights": [],
                "recommendations": [],
                "gaps": [],
                "matches": []
            }
    
    def _ai_extract_concepts(self, document_content: str, user_query: str) -> List[Dict[str, Any]]:
        """Use AI to extract key concepts from document content"""
        try:
            if not os.getenv('GOOGLE_API_KEY_SOL_4'):
                return []
            
            prompt = f"""Extract key business concepts from this document that might relate to database queries:

Document Content:
{document_content}

User Query Context: "{user_query}"

Extract and return JSON array of concepts:
[
  {{
    "type": "threshold|target|requirement|metric",
    "value": "extracted value", 
    "context": "business context",
    "field_keywords": ["potential database column keywords"]
  }}
]

Focus on:
- Numerical thresholds (income levels, scores, percentages)
- Business targets and goals
- Criteria and requirements
- Key performance indicators

Return ONLY valid JSON array."""

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            try:
                concepts = json.loads(response.text.strip())
                return concepts if isinstance(concepts, list) else []
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            return []
    
    def _format_db_results_for_ai(self, database_results: List[Dict]) -> str:
        """Format database results for AI analysis"""
        if not database_results:
            return "No database results found."
        
        formatted = ""
        for result in database_results:
            table = result.get('table_name', 'Unknown')
            data = result.get('data', [])
            count = result.get('row_count', 0)
            
            formatted += f"\n{table} Table Analysis:\n"
            formatted += f"- Records found: {count}\n"
            
            if data and len(data) > 0:
                # Show summary statistics
                first_record = data[0]
                formatted += "- Key data points:\n"
                
                for key, value in first_record.items():
                    if isinstance(value, (int, float)):
                        # Show range for numerical data
                        values = [row.get(key, 0) for row in data if isinstance(row.get(key), (int, float))]
                        if values:
                            formatted += f"  {key}: {min(values)} - {max(values)}\n"
                    elif isinstance(value, str) and len(str(value)) < 50:
                        # Show sample text values
                        unique_values = list(set([str(row.get(key, '')) for row in data[:3]]))
                        formatted += f"  {key}: {', '.join(unique_values[:3])}\n"
                
            formatted += "\n"
        
        return formatted
    
    def _calculate_extraction_confidence(self, concepts: List[Dict]) -> float:
        """Calculate confidence in concept extraction"""
        if not concepts:
            return 0.0
        
        confidence = 0.0
        for concept in concepts:
            if concept.get("value") and concept.get("type"):
                confidence += 25.0  # Base score for complete concept
                
                if concept.get("field_keywords"):
                    confidence += 10.0  # Bonus for field mapping
        
        return min(confidence, 100.0)
    
    def get_tools_log(self) -> List[str]:
        """Get processing log from all tools"""
        return self.tools_log.copy()
    
    def clear_tools_log(self):
        """Clear the tools processing log"""
        self.tools_log = []