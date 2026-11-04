"""Request dependencies: DB session, authenticated user, server-side role checks."""

from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_firebase_id_token
from app.db.session import get_db
from app.models import User
from app.services.accounts import ensure_user_defaults

bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_db)]

ROLE_RANK = {"user": 0, "contributor": 1, "moderator": 2, "admin": 3}


def _user_from_token(db: Session, token: str) -> User | None:
    s = get_settings()
    if s.auth_provider in ("local", "both"):
        try:
            claims = decode_access_token(token)
            user = db.get(User, claims["sub"])
            if user:
                return user
        except jwt.PyJWTError:
            if s.auth_provider == "local":
                return None
    if s.auth_provider in ("firebase", "both"):
        try:
            claims = verify_firebase_id_token(token)
        except Exception:
            return None
        uid = claims["user_id"] if "user_id" in claims else claims["sub"]
        user = db.scalar(select(User).where(User.firebase_uid == uid))
        if user is None:
            email = (claims.get("email") or f"{uid}@firebase.local").lower()
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, firebase_uid=uid, display_name=claims.get("name"))
                if email in s.admin_email_set and claims.get("email_verified"):
                    user.role = "admin"
                db.add(user)
                db.flush()
                ensure_user_defaults(db, user)
            else:
                user.firebase_uid = uid
            user.last_login_at = datetime.now(UTC)
            db.commit()
        return user
    return None


def get_optional_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User | None:
    if creds is None:
        return None
    user = _user_from_token(db, creds.credentials)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", {"WWW-Authenticate": "Bearer"})
    user = _user_from_token(db, creds.credentials)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token", {"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_role(minimum: str):
    """Role check against the role stored in the database, never the token claim."""

    def checker(user: CurrentUser) -> User:
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {minimum} role")
        return user

    return checker


Moderator = Annotated[User, Depends(require_role("moderator"))]
Admin = Annotated[User, Depends(require_role("admin"))]


def request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
