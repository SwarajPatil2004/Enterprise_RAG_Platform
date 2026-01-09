# Globals
# - Set DB_PATH to the file path: current script directory + "app.db".

# Function: get_conn()
# - Open a connection to SQLite database at DB_PATH
# - Configure connection so query results return "row objects" (dictionary-like access by column name)
# - Return the connection

# Function: init_db()
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Execute SQL:
#   - Create table users if it does not exist with columns:
#     - user_id auto-increment primary key
#     - username unique + not null
#     - password not null
#     - tenant_id not null
#     - role not null
#   - Create table documents if it does not exist with columns:
#     - doc_id auto-increment primary key
#     - tenant_id not null
#     - title not null
#     - created_by not null
#     - roles_allowed not null
#     - source_type not null
#     - source_value not null
#     - created_at not null
# - Commit transaction
# - Close connection

# Function: seed_demo_users()
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Define list demo_users containing:
#   - ("t1_admin", "pass", "t1", "admin")
#   - ("t1_member", "pass", "t1", "member")
#   - ("t2_admin", "pass", "t2", "admin")
#   - ("t2_member", "pass", "t2", "member")
# - For each user record u in demo_users:
#   - Try:
#     - Insert into users(username, password, tenant_id, role) values from u
#   - If insert fails due to duplicate username (integrity/unique constraint error):
#     - Ignore and continue
# - Commit transaction
# - Close connection

# Function: create_document(tenant_id, title, created_by, roles_allowed_json, source_type, source_value) -> doc_id
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Insert a new row into documents with:
#   - tenant_id, title, created_by, roles_allowed_json, source_type, source_value
#   - created_at ← current UTC timestamp in ISO format
# - doc_id ← last inserted row id
# - Commit transaction
# - Close connection
# - Return doc_id