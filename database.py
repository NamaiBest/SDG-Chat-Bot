"""
Database Module for SDG Chat Bot
Supports both PostgreSQL (Railway) and JSON file storage (local development)
Automatically switches based on DATABASE_URL environment variable
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

# Try to import psycopg2 (only available in production/Railway)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("[INFO] psycopg2 not installed - using JSON file storage for local development")

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_DATABASE = DATABASE_URL is not None and PSYCOPG2_AVAILABLE
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
        return None
    
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
        
        # Users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_username 
            ON users(username)
        """)
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        print("[SUCCESS] Database initialized successfully")
        return db_pool
        
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
    """Save conversation to JSON file by username"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        
        if not os.path.exists(mode_memory_dir):
            os.makedirs(mode_memory_dir)
            
        # Use username as filename instead of session_id
        file_path = os.path.join(mode_memory_dir, f"{username}.json")
        
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
            "session_id": session_id,  # Keep session_id for reference
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
        
        print(f"[SUCCESS] Conversation saved to JSON for user {username}: {file_path}")
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

def load_conversation_db(username: str, mode: str = "sustainability") -> Optional[Dict]:
    """Load conversation from PostgreSQL database by username"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get messages for this user and mode (all sessions)
        cursor.execute("""
            SELECT user_message, bot_response, has_media, media_type, timestamp, session_id
            FROM conversations
            WHERE username = %s AND mode = %s
            ORDER BY timestamp ASC
        """, (username, mode))
        
        messages = cursor.fetchall()
        
        if not messages:
            cursor.close()
            release_db_connection(conn)
            return None
        
        # Get detailed memories for this user (all sessions)
        cursor.execute("""
            SELECT media_type, timestamp, detailed_analysis, extracted_memory
            FROM detailed_memories
            WHERE session_id IN (
                SELECT DISTINCT session_id FROM conversations WHERE username = %s
            )
            ORDER BY timestamp ASC
        """, (username,))
        
        memories = cursor.fetchall()
        
        cursor.close()
        release_db_connection(conn)
        
        # Format data
        conversation_data = {
            "username": username,
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

def load_conversation_json(username: str, mode: str = "sustainability") -> Optional[Dict]:
    """Load conversation from JSON file by username"""
    try:
        memory_subdir = "personal_assistant" if mode == "personal-assistant" else "sustainability"
        mode_memory_dir = os.path.join(MEMORY_DIR, memory_subdir)
        # Use username as filename instead of session_id
        file_path = os.path.join(mode_memory_dir, f"{username}.json")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from JSON: {file_path}")
                return data
        
        # Try old location (session-based - for backwards compatibility)
        old_file_path = os.path.join(MEMORY_DIR, f"{username}.json")
        if os.path.exists(old_file_path):
            with open(old_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[SUCCESS] Loaded conversation from old location: {old_file_path}")
                return data
        
        print(f"[INFO] No conversation file found for user: {username}")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to load conversation from JSON: {e}")
        return None

def load_conversation(username: str, mode: str = "sustainability") -> Optional[Dict]:
    """
    Load conversation by username - automatically uses database or JSON based on configuration
    """
    if USE_DATABASE:
        return load_conversation_db(username, mode)
    else:
        return load_conversation_json(username, mode)

def get_conversation_context(username: str, mode: str = "sustainability", limit: int = 20) -> str:
    """Get recent conversation history for better responses by username"""
    conversation = load_conversation(username, mode)
    all_messages = []
    
    if conversation and conversation.get("messages"):
        all_messages.extend(conversation["messages"])
        print(f"[SUCCESS] Loaded {len(conversation['messages'])} messages from {mode} mode")
    
    # Load cross-mode context for personal assistant
    if mode == "personal-assistant":
        sustainability_conversation = load_conversation(username, "sustainability")
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


# ============================================
# User Authentication Functions
# ============================================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def register_user_db(username: str, password: str) -> Dict[str, Any]:
    """Register a new user in PostgreSQL database"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, created_at)
            VALUES (%s, %s, %s)
            RETURNING id, username, created_at
        """, (username, password_hash, datetime.now()))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        return {
            "success": True,
            "user_id": result[0],
            "username": result[1],
            "created_at": result[2].isoformat()
        }
    except psycopg2.IntegrityError:
        conn.rollback()
        db_pool.putconn(conn)
        return {"success": False, "error": "Username already exists"}
    except Exception as e:
        print(f"[ERROR] Error registering user: {e}")
        return {"success": False, "error": str(e)}


def register_user_json(username: str, password: str) -> Dict[str, Any]:
    """Register a new user in JSON file"""
    users_file = os.path.join(MEMORY_DIR, "users.json")
    
    # Load existing users
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        users = {}
    
    # Check if username exists
    if username in users:
        return {"success": False, "error": "Username already exists"}
    
    # Add new user
    password_hash = hash_password(password)
    users[username] = {
        "password_hash": password_hash,
        "created_at": datetime.now().isoformat()
    }
    
    # Save to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    return {
        "success": True,
        "username": username,
        "created_at": users[username]["created_at"]
    }


def register_user(username: str, password: str) -> Dict[str, Any]:
    """Register a new user (auto-detects DB or JSON)"""
    if USE_DATABASE:
        return register_user_db(username, password)
    else:
        return register_user_json(username, password)


def verify_login_db(username: str, password: str) -> Dict[str, Any]:
    """Verify user login in PostgreSQL database"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute("""
            SELECT id, username, created_at
            FROM users
            WHERE username = %s AND password_hash = %s
        """, (username, password_hash))
        
        result = cursor.fetchone()
        
        if result:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = %s WHERE username = %s
            """, (datetime.now(), username))
            conn.commit()
            
            cursor.close()
            db_pool.putconn(conn)
            
            return {
                "success": True,
                "user_id": result[0],
                "username": result[1],
                "created_at": result[2].isoformat()
            }
        else:
            cursor.close()
            db_pool.putconn(conn)
            return {"success": False, "error": "Invalid credentials"}
            
    except Exception as e:
        print(f"[ERROR] Error verifying login: {e}")
        return {"success": False, "error": str(e)}


def verify_login_json(username: str, password: str) -> Dict[str, Any]:
    """Verify user login in JSON file"""
    users_file = os.path.join(MEMORY_DIR, "users.json")
    
    if not os.path.exists(users_file):
        return {"success": False, "error": "No users registered"}
    
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    if username not in users:
        return {"success": False, "error": "Username not found"}
    
    password_hash = hash_password(password)
    
    if users[username]["password_hash"] == password_hash:
        # Update last login
        users[username]["last_login"] = datetime.now().isoformat()
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        return {
            "success": True,
            "username": username,
            "created_at": users[username]["created_at"]
        }
    else:
        return {"success": False, "error": "Invalid password"}


def verify_login(username: str, password: str) -> Dict[str, Any]:
    """Verify user login (auto-detects DB or JSON)"""
    if USE_DATABASE:
        return verify_login_db(username, password)
    else:
        return verify_login_json(username, password)


def check_username_exists_db(username: str) -> bool:
    """Check if username exists in PostgreSQL database"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        count = cursor.fetchone()[0]
        
        cursor.close()
        db_pool.putconn(conn)
        
        return count > 0
    except Exception as e:
        print(f"[ERROR] Error checking username: {e}")
        return False


def check_username_exists_json(username: str) -> bool:
    """Check if username exists in JSON file"""
    users_file = os.path.join(MEMORY_DIR, "users.json")
    
    if not os.path.exists(users_file):
        return False
    
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    return username in users


def check_username_exists(username: str) -> bool:
    """Check if username exists (auto-detects DB or JSON)"""
    if USE_DATABASE:
        return check_username_exists_db(username)
    else:
        return check_username_exists_json(username)


# Initialize database on module import
init_database()
