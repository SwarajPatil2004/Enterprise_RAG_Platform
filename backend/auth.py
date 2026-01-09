# Globals/Configuration
# - bearer = HTTPBearer() (FastAPI authentication scheme)
# - SECRET = environment variable "APP_SECRET" or default "dev_secret"
# - EXPIRE_MIN = environment variable "TOKEN_EXPIRE_MINUTES" or default 240
# - ALGO = "HS256"

# Function: login(username, password) -> token_string
# - conn ← get_conn()
# - cur ← conn.cursor()
# - Query: SELECT * FROM users WHERE username = username
# - row ← fetch first result row
# - Close connection
# - If row is null OR row["password"] != password:
#   - Raise HTTP 401 "Bad username or password"
# - Create payload dictionary:
#   - user_id = row["user_id"]
#   - tenant_id = row["tenant_id"]
#   - role = row["role"]
#   - exp = current UTC time + EXPIRE_MIN minutes
# - token ← JWT.encode(payload, SECRET, algorithm=ALGO)
# - Return token

# Function: require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> User
# - token ← creds.credentials (extract token from Authorization header)
# - Try:
#   - data ← JWT.decode(token, SECRET, algorithms=[ALGO])
#   - Create and return User object:
#     - user_id = int(data["user_id"])
#     - username = "(from_token)"
#     - tenant_id = str(data["tenant_id"])
#     - role = str(data["role"])
# - Catch any JWT decode exception:
#   - Raise HTTP 401 "Invalid token"