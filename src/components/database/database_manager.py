import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import google.generativeai as genai
from typing import Dict, Any, List, Optional


class DatabaseManager:
    def __init__(self):
        self.connection_string = self._build_connection_string()
        self.engine: Optional[Engine] = None
        self.connection_status = "not_attempted"
        
        # Configure Gemini for SQL generation
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
        
        # Try to connect but don't block if it fails - skip for now
        self.connection_status = "not_attempted"
        print("💡 Database connection will be attempted on first use")
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'rag_system')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def connect_to_database(self) -> bool:
        """Establish database connection"""
        try:
            self.engine = create_engine(
                self.connection_string,
                connect_args={"connect_timeout": 5}  # 5 second timeout
            )
            # Test connection with timeout
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.connection_status = "connected"
            return True
            
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.connection_status = "failed"
            self.engine = None
            return False
    
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information for SQL generation"""
        try:
            schema_query = """
            SELECT 
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(schema_query))
                rows = result.fetchall()
            
            # Organize schema by table
            schema = {}
            for row in rows:
                table_name = row[0]
                if table_name not in schema:
                    schema[table_name] = []
                
                schema[table_name].append({
                    'column': row[1],
                    'type': row[2],
                    'nullable': row[3] == 'YES'
                })
            
            return schema
            
        except Exception as e:
            print(f"Error getting database schema: {e}")
            return {}
    
    def generate_sql_query(self, natural_language_query: str, schema: Dict[str, Any]) -> str:
        """Convert natural language to SQL using Gemini"""
        
        if not os.getenv('GOOGLE_API_KEY_SOL_4'):
            return "Error: GOOGLE_API_KEY_SOL_4 not configured for SQL generation"
        
        try:
            # Format schema for prompt
            schema_text = "Database Schema:\n"
            for table, columns in schema.items():
                schema_text += f"\nTable: {table}\n"
                for col in columns:
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    schema_text += f"  - {col['column']} ({col['type']}) {nullable}\n"
            
            prompt = f"""You are a PostgreSQL expert. Convert the natural language query to SQL.

{schema_text}

Rules:
1. Return ONLY the SQL query, no explanations
2. Use proper PostgreSQL syntax
3. Include appropriate WHERE clauses for safety
4. Use LIMIT for large result sets
5. Handle case-insensitive searches with ILIKE when appropriate

Natural language query: {natural_language_query}

SQL Query:"""

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            # Clean up the response (remove any markdown formatting)
            sql_query = response.text.strip()
            if sql_query.startswith('```sql'):
                sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            return sql_query
            
        except Exception as e:
            return f"Error generating SQL: {str(e)}"
    
    def execute_query(self, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute SQL query safely with row limits"""
        
        # Basic SQL injection protection
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = sql_query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    'success': False,
                    'error': f"Dangerous SQL operation '{keyword}' not allowed",
                    'data': []
                }
        
        try:
            with self.engine.connect() as conn:
                # Add LIMIT if not present and it's not a COUNT/aggregate query
                if 'LIMIT' not in query_upper and not any(agg in query_upper for agg in ['COUNT(', 'SUM(', 'AVG(', 'MAX(', 'MIN(']):
                    sql_query += f" LIMIT {max_rows}"
                
                result = conn.execute(text(sql_query))
                
                # Convert to list of dictionaries
                columns = result.keys()
                rows = result.fetchall()
                
                data = []
                for row in rows:
                    data.append(dict(zip(columns, row)))
                
                return {
                    'success': True,
                    'data': data,
                    'row_count': len(data),
                    'query_executed': sql_query
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'query_attempted': sql_query
            }
    
    def natural_language_query(self, query: str) -> Dict[str, Any]:
        """Complete pipeline: natural language to SQL to results"""
        
        # 1. Get database schema
        schema = self.get_database_schema()
        if not schema:
            return {
                'success': False,
                'error': "Could not retrieve database schema",
                'response': "Database connection or schema issues"
            }
        
        # 2. Generate SQL
        sql_query = self.generate_sql_query(query, schema)
        
        if sql_query.startswith("Error:"):
            return {
                'success': False,
                'error': sql_query,
                'response': sql_query
            }
        
        # 3. Execute query
        query_results = self.execute_query(sql_query)
        
        if not query_results['success']:
            return {
                'success': False,
                'error': query_results['error'],
                'response': f"Query failed: {query_results['error']}"
            }
        
        # 4. Format response
        if query_results['data']:
            response = f"Found {query_results['row_count']} results:\n\n"
            
            # Format first few rows for display
            for i, row in enumerate(query_results['data'][:5]):
                response += f"Row {i+1}:\n"
                for key, value in row.items():
                    response += f"  {key}: {value}\n"
                response += "\n"
            
            if query_results['row_count'] > 5:
                response += f"... and {query_results['row_count'] - 5} more rows\n"
            
            response += f"\nSQL Query Used: {sql_query}"
        else:
            response = "No results found for your query."
        
        return {
            'success': True,
            'response': response,
            'data': query_results['data'],
            'sql_query': sql_query,
            'row_count': query_results['row_count']
        }