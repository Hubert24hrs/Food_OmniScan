"""Password hashing, local JWTs and Firebase ID token verification."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; reject longer passwords instead of silently truncating.
    data = password.encode("utf-8")
    if len(data) > 72:
        raise ValueError("Password too long")
    return bcrypt.hashpw(data, bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: str, role: str) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,  # informational only; authorisation always re-reads the role from the DB
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
        "iss": "foodomniscan",
        "typ": "access",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], issuer="foodomniscan")


def verify_firebase_id_token(token: str) -> dict:
    """Verify a Firebase Authentication ID token against Google's public certs.

    Needs only FIREBASE_PROJECT_ID (no service-account secret). Raises ValueError on failure.
    """
    s = get_settings()
    if not s.firebase_project_id:
        raise ValueError("Firebase auth not configured")
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token

    claims = id_token.verify_firebase_token(token, g_requests.Request(), audience=s.firebase_project_id)
    if not claims or claims.get("iss") != f"https://securetoken.google.com/{s.firebase_project_id}":
        raise ValueError("Invalid Firebase token issuer")
    return claims
