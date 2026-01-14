# Function: init_audit()
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Execute SQL to create audit table if it doesn't exist:
#   - audit_id INTEGER PRIMARY KEY AUTOINCREMENT
#   - tenant_id TEXT NOT NULL
#   - user_id INTEGER NOT NULL
#   - question TEXT NOT NULL
#   - retrieved TEXT NOT NULL
#   - created_at TEXT NOT 

# - Commit transaction
# - Close connection

# Function: log_audit(tenant_id, user_id, question, retrieved_json)
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Insert new audit record:
#   - tenant_id = tenant_id
#   - user_id = user_id
#   - question = question
#   - retrieved = retrieved_json
#   - created_at = current UTC timestamp in ISO format
# - Commit transaction
# - Close connection