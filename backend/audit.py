from datetime import datetime
import json
from .db import get_conn

def init_audit():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit(
      audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
      tenant_id TEXT NOT NULL,
      user_id INTEGER NOT NULL,
      question TEXT NOT NULL,
      retrieved TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def log_audit(tenant_id: str, user_id: int, question: str, retrieved_json: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit(tenant_id,user_id,question,retrieved,created_at) VALUES(?,?,?,?,?)",
        (tenant_id, user_id, question, retrieved_json, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def list_audit_for_tenant(tenant_id: str, limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT audit_id, tenant_id, user_id, question, retrieved, created_at "
        "FROM audit WHERE tenant_id=? ORDER BY audit_id DESC LIMIT ?",
        (tenant_id, limit),
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append({
            "audit_id": r["audit_id"],
            "tenant_id": r["tenant_id"],
            "user_id": r["user_id"],
            "question": r["question"],
            "retrieved": json.loads(r["retrieved"] or "[]"),
            "created_at": r["created_at"],
        })
    return out
