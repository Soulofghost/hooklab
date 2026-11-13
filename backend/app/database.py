import os
import sqlite3
from backend.app.config import DB_PATH

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS webhook_endpoints (
        id TEXT PRIMARY KEY,
        token TEXT UNIQUE,
        name TEXT,
        secret TEXT,
        forward_url TEXT,
        status TEXT DEFAULT 'ACTIVE',
        total_events INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS webhook_events (
        id TEXT PRIMARY KEY,
        endpoint_id TEXT,
        method TEXT,
        path TEXT,
        headers_json TEXT,
        query_params TEXT,
        body TEXT,
        signature_verified INTEGER DEFAULT 0,
        client_ip TEXT,
        received_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_attempts (
        id TEXT PRIMARY KEY,
        event_id TEXT,
        target_url TEXT,
        http_status INTEGER,
        response_time_ms REAL,
        response_body TEXT,
        success INTEGER,
        attempted_at TEXT
    );
    """)

    conn.commit()
    conn.close()

init_db()
