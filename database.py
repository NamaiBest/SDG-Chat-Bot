"""
Database Module for SDG Chat Bot
Supports both PostgreSQL (Railway) and JSON file storage (local development)
Automatically switches based on DATABASE_URL environment variable
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_DATABASE = DATABASE_URL is not None
MEMORY_DIR = "memory"

# Database connection pool
db_pool = None

def init_database():
    """Initialize database connection pool and create tables if using PostgreSQL"""
    global db_pool
    
    if not USE_DATABASE:
        print("[INFO] Using JSON file storage (DATABASE_URL not set)")
        # Ensure memory directory exists
        if not os.path.exists(MEMORY_DIR):
            os.makedirs(MEMORY_DIR)
        return
    
    print("[INFO] Using PostgreSQL database")
    
    try:
        # Create connection pool
        db_pool = SimpleConnectionPool(1, 10, DATABASE_URL)
        
        # Create tables
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                username VARCHAR(255) NOT NULL,
                mode VARCHAR(50) NOT NULL,
                user_message TEXT,
                bot_response TEXT,
                has_media BOOLEAN DEFAULT FALSE,
                media_type VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON conversations(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mode 
            ON conversations(mode)
        """)
        
        # Detailed memories table (for media analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detailed_memories (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                media_type VARCHAR(50),
                timestamp TIMESTAMP,
                detailed_analysis TEXT,
                extracted_memory JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        print("[SUCCESS] Database initialized successfully")
        
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        raise

def get_db_connection():
    """Get a database connection from the pool"""
    if not USE_DATABASE or db_pool is None:
        return None
    return db_pool.getconn()

def release_db_connection(conn):
    """Release connection back to the pool"""
    if USE_DATABASE and db_pool and conn:
        db_pool.putconn(conn)

def save_conversation_db(session_id: str, username: str, message: str, response: str, 
                        has_media: bool = False, media_type: Optional[str] = None, 
                        mode: str = "sustainability", detailed_memory: Optional[Dict] = None) -> bool:
    """Save conversation to PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert conversation message
        cursor.execute("""
            INSERT INTO conversations 
            (session_id, username, mode, user_message, bot_response, has_media, media_type, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session_id, username, mode, message, response, has_media, media_type, datetime.now()))
        
        # Insert detailed memory if provided
        if detailed_memory and has_media:
            cursor.execute("""
                INSERT INTO detailed_memories 
                (session_id, media_type, timestamp, detailed_analysis, extracted_memory)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                session_id,
                detailed_memory.get('media_type'),
                detailed_memory.get('timestamp'),
                detailed_memory.get('detailed_analysis'),
                json.dumps(detailed_memory.get('extracted_memory', {}))
            ))
        
        conn.commit()
        cursor.close()
        release_db_connection(conn)
        
        print(f"[SUCCESS] Conversation saved to database: {session_id}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to save conversation to database: {e}")
        if conn:
            conn.rollback()
            release_db_connection(conn)
        return False

def save_conversation_json(session_id: str, username: str, message: str, response: str,
                          has_media: bool = False, media_type: Optional[str] = None,
                          mode: str = "sustainability", detailed_memory: Optional[Dict] = None) -> bool:
    """Save conversation to JSON file"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        
        if not os.path.exists(mode_memory_dir):
            os.makedirs(mode_memory_dir)
            
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        
        conversation_data = {
            "username": username,
            "mode": mode,
            "messages": [],
            "detailed_memories": []
        }
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
        
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "has_media": has_media,
            "media_type": media_type
        }
        
        conversation_data["messages"].append(message_entry)
        
        if detailed_memory and has_media:
            if "detailed_memories" not in conversation_data:
                conversation_data["detailed_memories"] = []
            conversation_data["detailed_memories"].append(detailed_memory)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SUCCESS] Conversation saved to JSON: {file_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to save conversation to JSON: {e}")
        return False

def save_conversation(session_id: str, username: str, message: str, response: str,
                     has_media: bool = False, media_type: Optional[str] = None,
                     mode: str = "sustainability", detailed_memory: Optional[Dict] = None) -> bool:
    """
    Save conversation - automatically uses database or JSON based on configuration
    """
    if USE_DATABASE:
        return save_conversation_db(session_id, username, message, response, 
                                   has_media, media_type, mode, detailed_memory)
    else:
        return save_conversation_json(session_id, username, message, response,
                                     has_media, media_type, mode, detailed_memory)

def load_conversation_db(session_id: str, mode: str = "sustainability") -> Optional[Dict]:
    """Load conversation from PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get messages for this session and mode
        cursor.execute("""
            SELECT user_message, bot_response, has_media, media_type, timestamp
            FROM conversations
            WHERE session_id = %s AND mode = %s
            ORDER BY timestamp ASC
        """, (session_id, mode))
        
        messages = cursor.fetchall()
        
        if not messages:
            cursor.close()
            release_db_connection(conn)
            return None
        
        # Get detailed memories
        cursor.execute("""
            SELECT media_type, timestamp, detailed_analysis, extracted_memory
            FROM detailed_memories
            WHERE session_id = %s
            ORDER BY timestamp ASC
        """, (session_id,))
        
        memories = cursor.fetchall()
        
        cursor.close()
        release_db_connection(conn)
        
        # Format data
        conversation_data = {
            "username": messages[0].get("username", "User") if messages else "User",
            "mode": mode,
            "messages": [
                {
                    "timestamp": msg["timestamp"].isoformat() if msg["timestamp"] else None,
                    "user_message": msg["user_message"],
                    "bot_response": msg["bot_response"],
                    "has_media": msg["has_media"],
                    "media_type": msg["media_type"]
                }
                for msg in messages
            ],
            "detailed_memories": [
                {
                    "timestamp": mem["timestamp"].isoformat() if mem["timestamp"] else None,
                    "media_type": mem["media_type"],
                    "detailed_analysis": mem["detailed_analysis"],
                    "extracted_memory": mem["extracted_memory"]
                }
                for mem in memories
            ]
        }
        
        print(f"[SUCCESS] Loaded {len(messages)} messages from database")
        return conversation_data
        
    except Exception as e:
        print(f"[ERROR] Failed to load conversation from database: {e}")
        if conn:
            release_db_connection(conn)
        return None

def load_conversation_json(session_id: str, mode: str = "sustainability") -> Optional[Dict]:
    """Load conversation from JSON file"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        file_path = os.path.join(mode_memory_dir, f"{session_id}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from JSON: {file_path}")
                return data
        
        # Try old location
        old_file_path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if os.path.exists(old_file_path):
            with open(old_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from old location: {old_file_path}")
                return data
        
        print(f"[INFO] No conversation file found: {file_path}")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to load conversation from JSON: {e}")
        return None

def load_conversation(session_id: str, mode: str = "sustainability") -> Optional[Dict]:
    """
    Load conversation - automatically uses database or JSON based on configuration
    """
    if USE_DATABASE:
        return load_conversation_db(session_id, mode)
    else:
        return load_conversation_json(session_id, mode)

def get_conversation_context(session_id: str, mode: str = "sustainability", limit: int = 20) -> str:
    """Get recent conversation history for better responses"""
    conversation = load_conversation(session_id, mode)
    all_messages = []
    
    if conversation and conversation.get("messages"):
        all_messages.extend(conversation["messages"])
        print(f"[SUCCESS] Loaded {len(conversation['messages'])} messages from {mode} mode")
    
    # Load cross-mode context for personal assistant
    if mode == "personal-assistant":
        sustainability_conversation = load_conversation(session_id, "sustainability")
        if sustainability_conversation and sustainability_conversation.get("messages"):
            all_messages.extend(sustainability_conversation["messages"])
            print(f"[SUCCESS] Loaded {len(sustainability_conversation['messages'])} messages for cross-mode context")
    
    if not all_messages:
        print("[INFO] No conversation history found")
        return ""
    
    # Sort by timestamp
    try:
        all_messages.sort(key=lambda x: x.get('timestamp', ''))
    except Exception:
        pass
    
    # Get recent messages
    recent_messages = all_messages[-limit:]
    print(f"[SUCCESS] Using {len(recent_messages)} recent messages for context")
    
    # Build context string
    context = "=== COMPLETE CONVERSATION HISTORY ===\n"
    context += "Here's our complete conversation history across all modes so you can remember important details:\n\n"
    
    for msg in recent_messages:
        media_note = ""
        if msg.get("has_media"):
            m_type = msg.get("media_type", "media")
            media_note = f" (with {m_type})"
        context += f"User: {msg['user_message']}{media_note}\n"
        context += f"You responded: {msg['bot_response']}\n\n"
    
    context += "=== END CONVERSATION HISTORY ===\n"
    context += "CRITICAL: You MUST reference specific details from this conversation history. Never say you don't have stored observations if there are messages above.\n"
    
    return context

# Initialize database on module import
init_database()
