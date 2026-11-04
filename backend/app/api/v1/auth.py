from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import DB
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.services.accounts import ensure_user_defaults

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default="US", min_length=2, max_length=2)
    accept_terms: bool
    consent_health_data: bool = False  # needed before storing allergy/diet data


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user_id: str
    role: str


def _auth_enabled() -> None:
    if get_settings().auth_provider == "firebase":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email/password auth is disabled; sign in with Firebase.")


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: DB, request: Request):
    _auth_enabled()
    ratelimit.enforce(request, "auth", get_settings().rate_limit_auth_per_minute)
    if not body.accept_terms:
        raise HTTPException(422, "You must accept the terms of service.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    if body.password.lower() == body.password or not any(c.isdigit() for c in body.password):
        raise HTTPException(422, "Password needs at least one number and one uppercase letter.")
    now = datetime.now(UTC)
    country = (body.country or "US").upper()
    eu = {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
    currency = (
        "USD"
        if country == "US"
        else "GBP"
        if country == "GB"
        else "EUR"
        if country in eu
        else {"NG": "NGN", "GH": "GHS", "KE": "KES", "ZA": "ZAR", "CA": "CAD"}.get(country, "USD")
    )
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        country=country,
        currency=currency,
        locale="en-US" if country == "US" else "en",
        consent_terms_at=now,
        consent_health_data_at=now if body.consent_health_data else None,
    )
    if email in get_settings().admin_email_set:
        user.role = "admin"
    db.add(user)
    db.flush()
    ensure_user_defaults(db, user)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), user_id=user.id, role=user.role)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: DB, request: Request):
    _auth_enabled()
    ratelimit.enforce(request, "auth", get_settings().rate_limit_auth_per_minute)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(403, "Account disabled.")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), user_id=user.id, role=user.role)
