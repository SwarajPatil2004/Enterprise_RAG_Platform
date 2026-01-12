import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "app.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_by TEXT NOT NULL,
        roles_allowed TEXT NOT NULL,
        source_type TEXT NOT NULL,
        source_value TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def seed_demo_users():
    conn = get_conn()
    cur = conn.cursor()

    # demo only: plaintext passwords (not safe for real apps)
    demo = [
        ("t1_admin", "pass", "t1", "admin"),
        ("t1_member", "pass", "t1", "member"),
        ("t2_admin", "pass", "t2", "admin"),
        ("t2_member", "pass", "t2", "member"),
    ]
    for u in demo:
        try:
            cur.execute(
                "INSERT INTO users(username, password, tenant_id, role) VALUES(?,?,?,?)",
                u
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

def create_document(tenant_id: str, title: str, created_by: int, roles_allowed_json: str,
                    source_type: str, source_value: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO documents(tenant_id,title,created_by,roles_allowed,source_type,source_value,created_at)
      VALUES(?,?,?,?,?,?,?)
    """, (tenant_id, title, created_by, roles_allowed_json, source_type, source_value, datetime.utcnow().isoformat()))
    doc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return doc_id