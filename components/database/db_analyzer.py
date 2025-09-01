import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
import google.generativeai as genai
from typing import Dict, Any, List, Optional, Tuple
import json


class DatabaseAnalyzer:
    def __init__(self):
        self.connection_string = self._build_connection_string()
        self.engine: Optional[Engine] = None
        self.connection_status = "not_attempted"
        self.schema_cache = None
        
        # Configure Gemini for SQL generation
        if os.getenv('GOOGLE_API_KEY_SOL_4'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY_SOL_4'))
        
        # Try to connect
        self.connect_to_database()
    
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
                connect_args={"connect_timeout": 5}
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.connection_status = "connected"
            print("✅ Database connection successful")
            return True
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            self.connection_status = "failed"
            self.engine = None
            return False
    
    def analyze_database_structure(self) -> Dict[str, Any]:
        """Comprehensive database structure analysis"""
        if self.connection_status != "connected":
            return {"error": "Database not connected"}
        
        try:
            analysis = {
                "connection_status": "connected",
                "tables": {},
                "relationships": [],
                "indexes": {},
                "constraints": {},
                "suggestions": []
            }
            
            # Get table information
            tables_info = self._get_tables_info()
            analysis["tables"] = tables_info
            
            # Get relationships (foreign keys)
            relationships = self._get_foreign_key_relationships()
            analysis["relationships"] = relationships
            
            # Get indexes
            indexes = self._get_indexes_info()
            analysis["indexes"] = indexes
            
            # Get constraints
            constraints = self._get_constraints_info()
            analysis["constraints"] = constraints
            
            # Generate suggestions
            suggestions = self._generate_database_suggestions(tables_info, relationships)
            analysis["suggestions"] = suggestions
            
            self.schema_cache = analysis
            return analysis
            
        except Exception as e:
            return {"error": f"Database analysis failed: {str(e)}"}
    
    def _get_tables_info(self) -> Dict[str, Any]:
        """Get detailed table information"""
        tables_query = """
        SELECT 
            t.table_name,
            t.table_type,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale
        FROM information_schema.tables t
        LEFT JOIN information_schema.columns c 
            ON t.table_name = c.table_name
        WHERE t.table_schema = 'public'
        ORDER BY t.table_name, c.ordinal_position;
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(tables_query))
            rows = result.fetchall()
        
        tables = {}
        for row in rows:
            table_name = row[0]
            if table_name not in tables:
                tables[table_name] = {
                    "type": row[1],
                    "columns": [],
                    "row_count": 0
                }
            
            if row[2]:  # column_name
                column_info = {
                    "name": row[2],
                    "type": row[3],
                    "nullable": row[4] == "YES",
                    "default": row[5],
                    "max_length": row[6],
                    "precision": row[7],
                    "scale": row[8]
                }
                tables[table_name]["columns"].append(column_info)
        
        # Get row counts
        for table_name in tables.keys():
            try:
                with self.engine.connect() as conn:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    tables[table_name]["row_count"] = count_result.scalar()
            except:
                tables[table_name]["row_count"] = "Unknown"
        
        return tables
    
    def _get_foreign_key_relationships(self) -> List[Dict[str, Any]]:
        """Get foreign key relationships"""
        fk_query = """
        SELECT
            tc.table_name as source_table,
            kcu.column_name as source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public';
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(fk_query))
                rows = result.fetchall()
            
            relationships = []
            for row in rows:
                relationships.append({
                    "source_table": row[0],
                    "source_column": row[1],
                    "target_table": row[2],
                    "target_column": row[3],
                    "constraint_name": row[4]
                })
            
            return relationships
        except Exception as e:
            print(f"Error getting foreign keys: {e}")
            return []
    
    def _get_indexes_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get index information"""
        index_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(index_query))
                rows = result.fetchall()
            
            indexes = {}
            for row in rows:
                table_name = row[1]
                if table_name not in indexes:
                    indexes[table_name] = []
                
                indexes[table_name].append({
                    "name": row[2],
                    "definition": row[3]
                })
            
            return indexes
        except Exception as e:
            print(f"Error getting indexes: {e}")
            return {}
    
    def _get_constraints_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get constraint information"""
        constraint_query = """
        SELECT
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
        ORDER BY tc.table_name, tc.constraint_type;
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(constraint_query))
                rows = result.fetchall()
            
            constraints = {}
            for row in rows:
                table_name = row[0]
                if table_name not in constraints:
                    constraints[table_name] = []
                
                constraints[table_name].append({
                    "name": row[1],
                    "type": row[2],
                    "column": row[3]
                })
            
            return constraints
        except Exception as e:
            print(f"Error getting constraints: {e}")
            return {}
    
    def _generate_database_suggestions(self, tables: Dict[str, Any], relationships: List[Dict[str, Any]]) -> List[str]:
        """Generate CRUD operation suggestions"""
        suggestions = []
        
        for table_name, table_info in tables.items():
            # Skip system tables
            if table_name.startswith('pg_') or table_name in ['information_schema']:
                continue
            
            row_count = table_info.get("row_count", 0)
            columns = table_info.get("columns", [])
            
            # Basic suggestions
            suggestions.append(f"**{table_name}** ({row_count} rows)")
            
            # SELECT suggestions
            if row_count > 0:
                suggestions.append(f"  📊 SELECT: \"Show me all data from {table_name}\"")
                suggestions.append(f"  📊 SELECT: \"Get the first 10 records from {table_name}\"")
                
                # Column-specific suggestions
                text_columns = [col["name"] for col in columns if "char" in col["type"].lower() or "text" in col["type"].lower()]
                if text_columns:
                    suggestions.append(f"  🔍 SEARCH: \"Find records in {table_name} where {text_columns[0]} contains 'keyword'\"")
            
            # INSERT suggestions
            non_auto_columns = [col["name"] for col in columns if col["default"] is None or "nextval" not in str(col["default"])]
            if non_auto_columns:
                column_list = ", ".join(non_auto_columns[:3])
                suggestions.append(f"  ➕ INSERT: \"Add a new record to {table_name} with {column_list}\"")
            
            # UPDATE suggestions if has primary key
            pk_columns = [col["name"] for col in columns if col["name"].endswith("_id") or col["name"] == "id"]
            if pk_columns and row_count > 0:
                suggestions.append(f"  ✏️ UPDATE: \"Update {table_name} where {pk_columns[0]} = 1\"")
        
        # JOIN suggestions based on relationships
        if relationships:
            suggestions.append("\n**🔗 JOIN Operations:**")
            for rel in relationships[:3]:  # Show first 3 relationships
                suggestions.append(f"  🔗 JOIN: \"Show data from {rel['source_table']} with related {rel['target_table']} information\"")
        
        return suggestions
    
    def generate_crud_examples(self) -> Dict[str, List[str]]:
        """Generate example CRUD queries for the database"""
        if not self.schema_cache:
            self.analyze_database_structure()
        
        if not self.schema_cache or "tables" not in self.schema_cache:
            return {"error": "No schema information available"}
        
        examples = {
            "SELECT": [],
            "INSERT": [],
            "UPDATE": [],
            "DELETE": [],
            "JOIN": []
        }
        
        tables = self.schema_cache["tables"]
        relationships = self.schema_cache.get("relationships", [])
        
        for table_name, table_info in tables.items():
            if table_name.startswith('pg_'):
                continue
            
            columns = table_info["columns"]
            if not columns:
                continue
            
            # SELECT examples
            examples["SELECT"].extend([
                f"SELECT * FROM {table_name} LIMIT 10;",
                f"SELECT COUNT(*) FROM {table_name};",
            ])
            
            # Add column-specific selects
            text_cols = [col["name"] for col in columns if "char" in col["type"].lower() or "text" in col["type"].lower()]
            if text_cols:
                examples["SELECT"].append(f"SELECT {text_cols[0]} FROM {table_name} WHERE {text_cols[0]} ILIKE '%keyword%';")
            
            # INSERT examples
            insertable_cols = [col["name"] for col in columns if not (col["name"].endswith("_id") and col["default"])]
            if insertable_cols:
                col_names = ", ".join(insertable_cols[:3])
                placeholders = ", ".join(["'value'" for _ in insertable_cols[:3]])
                examples["INSERT"].append(f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders});")
            
            # UPDATE examples
            pk_cols = [col["name"] for col in columns if col["name"] in ["id", f"{table_name}_id"]]
            update_cols = [col["name"] for col in columns if col["name"] not in pk_cols]
            if pk_cols and update_cols:
                examples["UPDATE"].append(f"UPDATE {table_name} SET {update_cols[0]} = 'new_value' WHERE {pk_cols[0]} = 1;")
            
            # DELETE examples (with safety constraints)
            if pk_cols:
                examples["DELETE"].append(f"DELETE FROM {table_name} WHERE {pk_cols[0]} = 1;")
        
        # JOIN examples
        for rel in relationships[:5]:
            source_table = rel["source_table"]
            target_table = rel["target_table"]
            source_col = rel["source_column"]
            target_col = rel["target_column"]
            
            examples["JOIN"].append(
                f"SELECT s.*, t.* FROM {source_table} s "
                f"JOIN {target_table} t ON s.{source_col} = t.{target_col} LIMIT 10;"
            )
        
        return examples
    
    def execute_safe_query(self, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute SQL query with safety checks"""
        if self.connection_status != "connected":
            return {
                "success": False,
                "error": "Database not connected",
                "data": []
            }
        
        # Enhanced safety checks
        dangerous_patterns = [
            'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 
            'DELETE.*FROM.*WHERE.*1.*=.*1',  # Dangerous delete
            'UPDATE.*SET.*WHERE.*1.*=.*1',   # Dangerous update
        ]
        
        query_upper = sql_query.upper().strip()
        
        # Allow specific safe operations
        safe_operations = ['SELECT', 'WITH']
        is_safe_operation = any(query_upper.startswith(op) for op in safe_operations)
        
        if not is_safe_operation:
            # Check for dangerous patterns
            for pattern in dangerous_patterns:
                if pattern in query_upper:
                    return {
                        "success": False,
                        "error": f"Dangerous operation '{pattern}' not allowed in safe mode",
                        "data": []
                    }
        
        try:
            with self.engine.connect() as conn:
                # Add LIMIT if not present and it's a SELECT
                if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
                    sql_query += f" LIMIT {max_rows}"
                
                result = conn.execute(text(sql_query))
                
                # Handle different query types
                if result.returns_rows:
                    columns = list(result.keys())
                    rows = result.fetchall()
                    
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(columns):
                            value = row[i]
                            # Convert non-serializable types
                            if hasattr(value, 'isoformat'):  # datetime objects
                                value = value.isoformat()
                            elif isinstance(value, (bytes, bytearray)):
                                value = str(value)
                            row_dict[col] = value
                        data.append(row_dict)
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "columns": columns,
                        "query_executed": sql_query
                    }
                else:
                    # For non-SELECT queries (if allowed)
                    return {
                        "success": True,
                        "message": "Query executed successfully",
                        "affected_rows": result.rowcount,
                        "query_executed": sql_query
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "query_attempted": sql_query
            }
    
    def _get_foreign_key_relationships(self) -> List[Dict[str, Any]]:
        """Get foreign key relationships"""
        fk_query = """
        SELECT
            tc.table_name as source_table,
            kcu.column_name as source_column,
            ccu.table_name AS target_table,
            ccu.column_name AS target_column,
            tc.constraint_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        LEFT JOIN information_schema.referential_constraints AS rc
            ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public';
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(fk_query))
                rows = result.fetchall()
            
            relationships = []
            for row in rows:
                relationships.append({
                    "source_table": row[0],
                    "source_column": row[1],
                    "target_table": row[2],
                    "target_column": row[3],
                    "constraint_name": row[4],
                    "update_rule": row[5],
                    "delete_rule": row[6]
                })
            
            return relationships
        except Exception as e:
            print(f"Error getting foreign keys: {e}")
            return []
    
    def _get_indexes_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get index information"""
        index_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(index_query))
                rows = result.fetchall()
            
            indexes = {}
            for row in rows:
                table_name = row[1]
                if table_name not in indexes:
                    indexes[table_name] = []
                
                indexes[table_name].append({
                    "name": row[2],
                    "definition": row[3]
                })
            
            return indexes
        except Exception as e:
            print(f"Error getting indexes: {e}")
            return {}
    
    def _get_constraints_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get constraint information"""
        constraint_query = """
        SELECT
            tc.table_name,
            tc.constraint_name,
            tc.constraint_type,
            kcu.column_name
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = 'public'
        ORDER BY tc.table_name, tc.constraint_type;
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(constraint_query))
                rows = result.fetchall()
            
            constraints = {}
            for row in rows:
                table_name = row[0]
                if table_name not in constraints:
                    constraints[table_name] = []
                
                constraints[table_name].append({
                    "name": row[1],
                    "type": row[2],
                    "column": row[3]
                })
            
            return constraints
        except Exception as e:
            print(f"Error getting constraints: {e}")
            return {}
    
    def _generate_database_suggestions(self, tables: Dict[str, Any], relationships: List[Dict[str, Any]]) -> List[str]:
        """Generate intelligent query suggestions"""
        suggestions = []
        
        # Table overview suggestions
        suggestions.append("🔍 **Database Overview Queries:**")
        suggestions.append("\"Show me all tables and their row counts\"")
        suggestions.append("\"What is the database structure?\"")
        suggestions.append("\"Show me the relationships between tables\"")
        
        # Table-specific suggestions
        for table_name, table_info in tables.items():
            if table_name.startswith('pg_'):
                continue
            
            row_count = table_info.get("row_count", 0)
            columns = table_info.get("columns", [])
            
            suggestions.append(f"\n📊 **{table_name} Table ({row_count} rows):**")
            
            if row_count > 0:
                # Basic queries
                suggestions.append(f"\"Show me data from {table_name}\"")
                suggestions.append(f"\"How many records are in {table_name}?\"")
                
                # Column-specific queries
                text_columns = [col["name"] for col in columns if "char" in col["type"].lower() or "text" in col["type"].lower()]
                date_columns = [col["name"] for col in columns if "date" in col["type"].lower() or "time" in col["type"].lower()]
                numeric_columns = [col["name"] for col in columns if any(t in col["type"].lower() for t in ["int", "decimal", "numeric", "float"])]
                
                if text_columns:
                    suggestions.append(f"\"Search {table_name} for records containing 'keyword' in {text_columns[0]}\"")
                
                if date_columns:
                    suggestions.append(f"\"Show {table_name} records from the last month\"")
                
                if numeric_columns:
                    suggestions.append(f"\"What is the average {numeric_columns[0]} in {table_name}?\"")
        
        # Relationship-based suggestions
        if relationships:
            suggestions.append("\n🔗 **Related Data Queries:**")
            for rel in relationships[:3]:
                suggestions.append(f"\"Show {rel['source_table']} data with related {rel['target_table']} information\"")
        
        return suggestions
    
    def natural_language_to_sql(self, query: str) -> Dict[str, Any]:
        """Convert natural language to SQL using current schema"""
        if not os.getenv('GOOGLE_API_KEY_SOL_4'):
            return {"error": "Google API key not configured"}
        
        if not self.schema_cache:
            analysis = self.analyze_database_structure()
            if "error" in analysis:
                return analysis
        
        try:
            # Format schema for prompt
            schema_text = "Database Schema:\n"
            for table_name, table_info in self.schema_cache["tables"].items():
                if table_name.startswith('pg_'):
                    continue
                
                schema_text += f"\nTable: {table_name} ({table_info.get('row_count', 0)} rows)\n"
                for col in table_info["columns"]:
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    schema_text += f"  - {col['name']} ({col['type']}) {nullable}\n"
            
            # Add relationships
            if self.schema_cache.get("relationships"):
                schema_text += "\nRelationships:\n"
                for rel in self.schema_cache["relationships"]:
                    schema_text += f"  - {rel['source_table']}.{rel['source_column']} -> {rel['target_table']}.{rel['target_column']}\n"
            
            prompt = f"""You are a PostgreSQL expert. Convert the natural language query to SQL.

{schema_text}

Rules:
1. Return ONLY the SQL query, no explanations
2. Use proper PostgreSQL syntax  
3. Always include LIMIT for SELECT queries (max 100 rows)
4. Use ILIKE for case-insensitive text searches
5. For date filters, use appropriate date functions
6. Only generate SELECT queries for safety
7. Use table aliases for JOINs
8. Include appropriate WHERE clauses

Natural language query: {query}

SQL Query:"""

            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            # Clean up response
            sql_query = response.text.strip()
            if sql_query.startswith('```sql'):
                sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            return {
                "success": True,
                "sql_query": sql_query,
                "schema_used": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating SQL: {str(e)}"
            }
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current database connection status"""
        return {
            "status": self.connection_status,
            "connection_string": self.connection_string.replace(os.getenv('DB_PASSWORD', ''), '***') if os.getenv('DB_PASSWORD') else self.connection_string,
            "engine_active": self.engine is not None
        }