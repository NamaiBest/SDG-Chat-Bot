"""
ESP32-CAM Integration Module
Handles device registration, video streaming, and audio processing from ESP32-CAM devices
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict
import uuid

# Database imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_DATABASE = DATABASE_URL is not None and PSYCOPG2_AVAILABLE
MEMORY_DIR = "memory"
DEVICES_FILE = os.path.join(MEMORY_DIR, "devices.json")


def init_devices_table(db_pool):
    """Initialize ESP32 devices table in PostgreSQL"""
    if not USE_DATABASE or not db_pool:
        return
    
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Create devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS esp32_devices (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255) NOT NULL,
                device_name VARCHAR(255),
                mac_address VARCHAR(50),
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_id 
            ON esp32_devices(device_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_username 
            ON esp32_devices(username)
        """)
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        print("[SUCCESS] ESP32 devices table initialized")
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize devices table: {e}")


def register_device_db(device_id: str, username: str, device_name: str, mac_address: str, db_pool) -> Dict:
    """Register ESP32 device in PostgreSQL"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Check if device already exists
        cursor.execute("""
            SELECT device_id, username FROM esp32_devices 
            WHERE device_id = %s
        """, (device_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing device
            cursor.execute("""
                UPDATE esp32_devices 
                SET username = %s, device_name = %s, mac_address = %s, 
                    last_seen = %s, is_active = TRUE
                WHERE device_id = %s
            """, (username, device_name, mac_address, datetime.now(), device_id))
        else:
            # Insert new device
            cursor.execute("""
                INSERT INTO esp32_devices 
                (device_id, username, device_name, mac_address, registered_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (device_id, username, device_name, mac_address, datetime.now(), datetime.now()))
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        return {
            "success": True,
            "device_id": device_id,
            "username": username,
            "message": "Device registered successfully"
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to register device: {e}")
        return {"success": False, "error": str(e)}


def register_device_json(device_id: str, username: str, device_name: str, mac_address: str) -> Dict:
    """Register ESP32 device in JSON file"""
    try:
        if not os.path.exists(MEMORY_DIR):
            os.makedirs(MEMORY_DIR)
        
        # Load existing devices
        devices = {}
        if os.path.exists(DEVICES_FILE):
            with open(DEVICES_FILE, 'r') as f:
                devices = json.load(f)
        
        # Add or update device
        devices[device_id] = {
            "username": username,
            "device_name": device_name,
            "mac_address": mac_address,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "is_active": True
        }
        
        # Save devices
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2)
        
        return {
            "success": True,
            "device_id": device_id,
            "username": username,
            "message": "Device registered successfully"
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to register device: {e}")
        return {"success": False, "error": str(e)}


def get_device_username_db(device_id: str, db_pool) -> Optional[str]:
    """Get username associated with device from PostgreSQL"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT username FROM esp32_devices 
            WHERE device_id = %s AND is_active = TRUE
        """, (device_id,))
        
        result = cursor.fetchone()
        cursor.close()
        db_pool.putconn(conn)
        
        return result[0] if result else None
        
    except Exception as e:
        print(f"[ERROR] Failed to get device username: {e}")
        return None


def get_device_username_json(device_id: str) -> Optional[str]:
    """Get username associated with device from JSON"""
    try:
        if not os.path.exists(DEVICES_FILE):
            return None
        
        with open(DEVICES_FILE, 'r') as f:
            devices = json.load(f)
        
        device = devices.get(device_id)
        if device and device.get("is_active"):
            return device.get("username")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to get device username: {e}")
        return None


def update_device_last_seen_db(device_id: str, db_pool) -> bool:
    """Update device last seen timestamp in PostgreSQL"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE esp32_devices 
            SET last_seen = %s 
            WHERE device_id = %s
        """, (datetime.now(), device_id))
        
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to update device last seen: {e}")
        return False


def update_device_last_seen_json(device_id: str) -> bool:
    """Update device last seen timestamp in JSON"""
    try:
        if not os.path.exists(DEVICES_FILE):
            return False
        
        with open(DEVICES_FILE, 'r') as f:
            devices = json.load(f)
        
        if device_id in devices:
            devices[device_id]["last_seen"] = datetime.now().isoformat()
            
            with open(DEVICES_FILE, 'w') as f:
                json.dump(devices, f, indent=2)
            
            return True
        
        return False
        
    except Exception as e:
        print(f"[ERROR] Failed to update device last seen: {e}")
        return False
