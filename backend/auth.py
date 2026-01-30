import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .db import get_conn
from .models import User

bearer = HTTPBearer()

SECRET = os.getenv("APP_SECRET", "dev_secret")
EXPIRE_MIN = int(os.getenv("TOKEN_EXPIRE_MINUTES", "240"))
ALGO = "HS256"

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def login(username: str, password: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or not pwd_context.verify(password, row["password"]):
        raise HTTPException(status_code=401, detail="Bad username or password")

    payload = {
        "user_id": row["user_id"],
        "tenant_id": row["tenant_id"],
        "role": row["role"],
        "groups": json.loads(row["groups"] or "[]"),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN),
    }

    return jwt.encode(payload, SECRET, algorithm=ALGO)

def require_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> User:
    token = creds.credentials
    try:
        data = jwt.decode(token, SECRET, algorithms=[ALGO])
        return User(
            user_id=int(data["user_id"]),
            username="(from_token)",
            tenant_id=str(data["tenant_id"]),
            role=str(data["role"]),
            groups=list(data.get("groups", [])),
        )

    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")