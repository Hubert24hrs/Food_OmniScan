"""Environment-specific configuration.

All secrets come from environment variables (or a local `.env`); nothing secret
is committed. See `.env.example` for the full list.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Food omniScan"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False

    # PostgreSQL in production: postgresql+psycopg://user:pass@host:5432/omniscan
    database_url: str = "sqlite:///./omniscan.db"

    # CORS: comma-separated origins
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Auth -----------------------------------------------------------
    # "local": email/password with bcrypt + HS256 JWT issued by this API.
    # "firebase": verify Firebase ID tokens (Firebase Authentication).
    # "both": accept either (useful while migrating).
    auth_provider: Literal["local", "firebase", "both"] = "local"
    jwt_secret: str = Field(default="dev-insecure-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    firebase_project_id: str | None = None
    # Comma-separated emails that are promoted to admin on first login/registration.
    bootstrap_admin_emails: str = ""

    # --- Data providers --------------------------------------------------
    off_base_url: str = "https://world.openfoodfacts.org"
    off_search_url: str = "https://search.openfoodfacts.org"
    off_user_agent: str = "FoodOmniScan/0.1 (contact: dev@foodomniscan.app)"
    off_timeout_seconds: float = 10.0
    product_cache_hours: int = 24 * 7
    usda_api_key: str | None = None
    usda_base_url: str = "https://api.nal.usda.gov/fdc/v1"

    # --- AI ---------------------------------------------------------------
    ai_provider: Literal["gemini", "none"] = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # --- Market defaults ------------------------------------------------------
    # US standards are the default (FDA %DV, US Big 9 allergens, USD, en-US); EU/UK is secondary.
    default_region: str = "US"
    default_currency: str = "USD"
    default_locale: str = "en-US"
    public_app_url: str = "http://localhost:3000"

    # --- Payments ----------------------------------------------------------
    # Stripe: primary web billing (US/EU). Prices as JSON, e.g. {"plus_month":"price_123","plus_year":"price_456"}
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_prices: str = "{}"
    paystack_secret_key: str | None = None  # African markets
    revenuecat_webhook_auth: str | None = None  # iOS / Android in-app purchases

    # --- Uploads -------------------------------------------------------------
    upload_dir: str = "./uploads"
    max_upload_mb: int = 8

    # --- Abuse protection -------------------------------------------------
    rate_limit_per_minute: int = 120
    rate_limit_auth_per_minute: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.bootstrap_admin_emails.split(",") if e.strip()}

    @property
    def stripe_price_map(self) -> dict[str, str]:
        import json

        try:
            return json.loads(self.stripe_prices or "{}")
        except ValueError:
            return {}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.jwt_secret.startswith("dev-"):
        raise RuntimeError("JWT_SECRET must be set to a strong secret in production")
    return settings
