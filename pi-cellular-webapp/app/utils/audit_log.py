import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
from app.config import CONFIG_DIR, AUDIT_DB_PATH
from app.utils.time_sync import get_network_time

logging.basicConfig(level=logging.INFO)


def init_audit_db():
    """Initialize audit database."""
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL,
            details TEXT,
            old_value TEXT,
            new_value TEXT,
            tz_offset TEXT,
            source TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def log_operation(operation: str, details: str = "", old_value: str = "", new_value: str = ""):
    """
    Log operation to audit database with network time.
    
    Args:
        operation: Operation name (e.g., "IMEI_CHANGE", "RADIO_OFF")
        details: Human-readable description
        old_value: Previous value (for changes)
        new_value: New value (for changes)
    """
    try:
        init_audit_db()
        
        net_time = get_network_time()
        timestamp = net_time["network_time"].isoformat()
        tz_offset = net_time.get("tz_offset", "+0000")
        source = net_time.get("source", "unknown")
        
        conn = sqlite3.connect(AUDIT_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO audit_log 
               (timestamp, operation, details, old_value, new_value, tz_offset, source) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, operation, details, old_value, new_value, tz_offset, source)
        )
        
        conn.commit()
        conn.close()
        
        logging.info(f"Audit: {operation} - {details}")
    except Exception as e:
        logging.error(f"Failed to log operation: {e}")


def get_audit_log(limit: int = 100) -> List[Dict]:
    """
    Get recent audit log entries.
    
    Args:
        limit: Maximum number of entries to return
    
    Returns:
        List of audit log entries (newest first)
    """
    try:
        init_audit_db()
        
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT * FROM audit_log 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (limit,)
        )
        
        entries = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return entries
    except Exception as e:
        logging.error(f"Failed to get audit log: {e}")
        return []
