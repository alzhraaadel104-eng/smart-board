"""Local SQLite user accounts and signed browser sessions."""
import base64
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path

ITERATIONS = 310_000
COOKIE_NAME = "smart_sketch_session"
SESSION_SECONDS = 60 * 60 * 24 * 7


@contextmanager
def _connection():
    connection = sqlite3.connect(database_path(), timeout=10)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def database_path() -> Path:
    configured = os.getenv("DATABASE_PATH", "").strip()
    path = Path(configured).expanduser() if configured else Path(__file__).resolve().parents[2] / "data" / "users.db"
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _session_secret() -> bytes:
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters.")
        return configured.encode("utf-8")
    secret_file = database_path().parent / "session.secret"
    try:
        with secret_file.open("x", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(48))
        try:
            secret_file.chmod(0o600)
        except OSError:
            pass
    except FileExistsError:
        pass
    return secret_file.read_text(encoding="utf-8").strip().encode("utf-8")


def init_db() -> None:
    with _connection() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _decode(salt), int(rounds))
        return hmac.compare_digest(actual, _decode(expected))
    except (ValueError, TypeError):
        return False


def create_user(username: str, email: str, password: str):
    try:
        with _connection() as connection:
            connection.execute(
                "INSERT INTO users (username,email,password_hash) VALUES (?,?,?)",
                (username.strip(), email.strip().lower(), hash_password(password)),
            )
            row = connection.execute(
                "SELECT id,username,email,created_at FROM users WHERE username=? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
    except sqlite3.IntegrityError:
        return None
    return {"id": row[0], "username": row[1], "email": row[2], "created_at": row[3]}


def find_user(login: str):
    with _connection() as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT id,username,email,password_hash,created_at FROM users WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE",
            (login.strip(), login.strip()),
        ).fetchone()
    return dict(row) if row else None


def public_user(user):
    return {"id": user["id"], "username": user["username"], "email": user["email"], "created_at": user["created_at"]}


def make_session(user_id: int) -> str:
    payload = _encode(json.dumps({"uid": user_id, "exp": int(time.time()) + SESSION_SECONDS}, separators=(",", ":")).encode("utf-8"))
    signature = _encode(hmac.new(_session_secret(), payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def session_user(token: str | None):
    if not token or "." not in token:
        return None
    try:
        payload, signature = token.rsplit(".", 1)
        expected = hmac.new(_session_secret(), payload.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode(signature)):
            return None
        data = json.loads(_decode(payload))
        if int(data["exp"]) < int(time.time()):
            return None
        with _connection() as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT id,username,email,created_at FROM users WHERE id=?", (int(data["uid"]),)).fetchone()
        return dict(row) if row else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
