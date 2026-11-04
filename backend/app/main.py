import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  (register models)
from app.api.v1 import (
    admin,
    admin_content,
    analysis,
    assistant,
    auth,
    billing,
    diary,
    explore,
    history,
    ingredients,
    kitchen,
    me,
    products,
    profiles,
    recipes,
    shopping,
    submissions,
)
from app.core.config import get_settings
from app.db import seed
from app.db.session import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("omniscan")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    if s.environment in ("development", "test") and s.database_url.startswith("sqlite"):
        # Local convenience only; staging/production run `alembic upgrade head` instead.
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        try:
            log.info("reference data seed: %s", seed.run(db))
        except Exception:  # pragma: no cover - surfaced in logs, app still starts
            log.exception("seed failed (did you run migrations?)")
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Food omniScan API",
        version=s.app_version,
        description="Food intelligence: barcode lookup, ingredient analysis, explainable scoring, allergen and diet "
        "compatibility. US FDA standards by default.",
        lifespan=lifespan,
        docs_url="/docs" if not s.is_production else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if s.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        if request.url.path.startswith("/api/") and request.method == "GET" and "authorization" in request.headers:
            response.headers.setdefault("Cache-Control", "private, no-store")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": {"code": "validation_error", "errors": errors}})

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # pragma: no cover
        log.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "server_error", "message": "Something went wrong on our side."}},
        )

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "version": s.app_version, "environment": s.environment}

    @app.get("/api/v1/meta", tags=["meta"])
    def meta():
        return {
            "app": s.app_name,
            "version": s.app_version,
            "default_region": s.default_region,
            "default_currency": s.default_currency,
            "default_locale": s.default_locale,
            "auth_provider": s.auth_provider,
            "ai_enabled": bool(s.gemini_api_key),
            "usda_enabled": bool(s.usda_api_key),
            "billing": {
                "stripe": bool(s.stripe_secret_key),
                "revenuecat": bool(s.revenuecat_webhook_auth),
                "paystack": bool(s.paystack_secret_key),
            },
            "attribution": ["Open Food Facts (ODbL)", "USDA FoodData Central (CC0)"],
        }

    for r in (
        auth,
        me,
        profiles,
        products,
        history,
        analysis,
        ingredients,
        submissions,
        shopping,
        diary,
        assistant,
        billing,
        recipes,
        kitchen,
        explore,
        admin,
        admin_content,
    ):
        app.include_router(r.router, prefix="/api/v1")
    return app


app = create_app()
