"""JWT authentication, password hashing, user management."""
import sqlite3
import bcrypt
import jwt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from fastapi import Request, HTTPException
from app.config import DB_PATH

JWT_SECRET = secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


@dataclass
class User:
    id: int
    email: str
    created_at: str


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(email: str, password: str) -> User | None:
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email.lower().strip(), hash_password(password)),
            )
            conn.commit()
            return User(id=cursor.lastrowid, email=email, created_at=datetime.now().isoformat())
    except sqlite3.IntegrityError:
        return None


def authenticate(email: str, password: str) -> str | None:
    """Return JWT token if credentials valid, else None."""
    with _get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None

    token = jwt.encode(
        {"user_id": row["id"], "email": row["email"], "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    return token


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None


def get_current_user(request: Request) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return User(id=payload["user_id"], email=payload["email"], created_at="")


def auth_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = get_current_user(request)
        request.state.user = user
        return await func(request, *args, **kwargs)
    return wrapper
