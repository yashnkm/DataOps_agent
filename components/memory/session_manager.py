import os
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path


class SessionManager:
    def __init__(self, db_path: str = "./sessions.db"):
        self.db_path = db_path
        self.current_session_id = None
        self.max_context_length = 10  # Maximum messages to keep in context
        self.session_timeout_hours = 24  # Sessions expire after 24 hours
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for session storage"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message_type TEXT,  -- 'user' or 'assistant'
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            # Documents table for session-based document tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    filename TEXT,
                    file_path TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chunk_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            conn.commit()
    
    def create_session(self, metadata: Dict[str, Any] = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sessions (session_id, metadata) VALUES (?, ?)',
                (session_id, json.dumps(metadata or {}))
            )
            conn.commit()
        
        self.current_session_id = session_id
        return session_id
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Get existing session or create new one"""
        if session_id:
            # Check if session exists and is not expired
            if self._is_session_valid(session_id):
                self.current_session_id = session_id
                self._update_session_activity(session_id)
                return session_id
        
        # Create new session
        return self.create_session()
    
    def _is_session_valid(self, session_id: str) -> bool:
        """Check if session exists and is not expired"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT last_activity FROM sessions WHERE session_id = ?',
                (session_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return False
            
            # Check if session is expired
            last_activity = datetime.fromisoformat(result[0])
            expiry_time = last_activity + timedelta(hours=self.session_timeout_hours)
            
            return datetime.now() < expiry_time
    
    def _update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
                (session_id,)
            )
            conn.commit()
    
    def add_message(self, session_id: str, message_type: str, content: str, 
                   metadata: Dict[str, Any] = None):
        """Add a message to the conversation history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO conversations (session_id, message_type, content, metadata) VALUES (?, ?, ?, ?)',
                (session_id, message_type, content, json.dumps(metadata or {}))
            )
            conn.commit()
        
        # Update session activity
        self._update_session_activity(session_id)
    
    def get_conversation_history(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT message_type, content, timestamp, metadata 
                FROM conversations 
                WHERE session_id = ? 
                ORDER BY timestamp DESC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (session_id,))
            results = cursor.fetchall()
            
            # Convert to list of dicts (reverse to get chronological order)
            history = []
            for row in reversed(results):
                history.append({
                    'role': row[0],
                    'content': row[1],
                    'timestamp': row[2],
                    'metadata': json.loads(row[3])
                })
            
            return history
    
    def get_context_for_query(self, session_id: str) -> str:
        """Get recent conversation context for current query"""
        history = self.get_conversation_history(session_id, limit=self.max_context_length)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history[-self.max_context_length:]:  # Last N messages
            role = "User" if msg['role'] == 'user' else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def add_document_to_session(self, session_id: str, filename: str, file_path: str, 
                               chunk_count: int = 0, metadata: Dict[str, Any] = None):
        """Track document uploads for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO session_documents 
                   (session_id, filename, file_path, chunk_count, metadata) 
                   VALUES (?, ?, ?, ?, ?)''',
                (session_id, filename, file_path, chunk_count, json.dumps(metadata or {}))
            )
            conn.commit()
    
    def get_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """Get documents uploaded in this session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT filename, file_path, upload_time, chunk_count, metadata 
                   FROM session_documents 
                   WHERE session_id = ? 
                   ORDER BY upload_time''',
                (session_id,)
            )
            results = cursor.fetchall()
            
            documents = []
            for row in results:
                documents.append({
                    'filename': row[0],
                    'file_path': row[1],
                    'upload_time': row[2],
                    'chunk_count': row[3],
                    'metadata': json.loads(row[4])
                })
            
            return documents
    
    def clear_session(self, session_id: str) -> bool:
        """Clear all data for a session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete conversations
                cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
                
                # Delete session documents
                cursor.execute('DELETE FROM session_documents WHERE session_id = ?', (session_id,))
                
                # Delete session
                cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error clearing session: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get expired session IDs
            cursor.execute(
                'SELECT session_id FROM sessions WHERE last_activity < ?',
                (cutoff_time.isoformat(),)
            )
            expired_sessions = [row[0] for row in cursor.fetchall()]
            
            # Clear each expired session
            for session_id in expired_sessions:
                self.clear_session(session_id)
        
        return len(expired_sessions)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute(
                'SELECT created_at, last_activity FROM sessions WHERE session_id = ?',
                (session_id,)
            )
            session_info = cursor.fetchone()
            
            # Get message count
            cursor.execute(
                'SELECT COUNT(*) FROM conversations WHERE session_id = ?',
                (session_id,)
            )
            message_count = cursor.fetchone()[0]
            
            # Get document count
            cursor.execute(
                'SELECT COUNT(*), SUM(chunk_count) FROM session_documents WHERE session_id = ?',
                (session_id,)
            )
            doc_stats = cursor.fetchone()
            
            return {
                'session_id': session_id,
                'created_at': session_info[0] if session_info else None,
                'last_activity': session_info[1] if session_info else None,
                'message_count': message_count,
                'document_count': doc_stats[0] or 0,
                'total_chunks': doc_stats[1] or 0
            }