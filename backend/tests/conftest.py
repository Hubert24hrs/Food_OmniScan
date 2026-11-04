import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="omniscan-test-")
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db".replace("\\", "/"),
    "JWT_SECRET": "test-secret-key-0123456789abcdef",
    "BOOTSTRAP_ADMIN_EMAILS": "admin@example.com",
    "UPLOAD_DIR": os.path.join(_tmp, "uploads"),
    "AUTH_PROVIDER": "local",
    "GEMINI_API_KEY": "",
    "USDA_API_KEY": "",
    "STRIPE_SECRET_KEY": "",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
    "REVENUECAT_WEBHOOK_AUTH": "rc-test-auth",
    "PAYSTACK_SECRET_KEY": "sk_test_paystack",
    "RATE_LIMIT_AUTH_PER_MINUTE": "1000",
    "RATE_LIMIT_PER_MINUTE": "1000",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.ratelimit import limiter  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ai import provider as _ai_provider  # noqa: E402

_ai_provider.RETRY_BACKOFF_S = 0  # no real sleeps when tests exercise retries

OFF = "https://world.openfoodfacts.org"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.reset()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


_counter = {"n": 0}


def register(client, email: str | None = None, consent: bool = True, country: str = "US") -> dict:
    _counter["n"] += 1
    email = email or f"user{_counter['n']}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Sup3rSecret", "display_name": "Test",
                                                   "country": country, "accept_terms": True,
                                                   "consent_health_data": consent})
    if r.status_code == 409:
        r = client.post("/api/v1/auth/login", json={"email": email, "password": "Sup3rSecret"})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers(client):
    return register(client)


@pytest.fixture
def admin_headers(client):
    return register(client, "admin@example.com")


# --------------------------------------------------------------------------- OFF fixtures
# Shapes mirror Open Food Facts API v2 responses. Values are test fixtures, not product data.

def off_product(code: str, **overrides) -> dict:
    p = {
        "code": code,
        "product_name": "Test Cola",
        "brands": "TestBrand",
        "categories_tags": ["en:beverages", "en:carbonated-drinks", "en:sodas", "en:colas"],
        "categories": "Beverages, Carbonated drinks, Sodas, Colas",
        "countries_tags": ["en:united-states"],
        "labels_tags": [],
        "ingredients_text": "Carbonated water, high fructose corn syrup, caramel color, phosphoric acid, natural "
        "flavors, caffeine.",
        "allergens_tags": [],
        "traces_tags": [],
        "additives_tags": ["en:e150d", "en:e338"],
        "ingredients_analysis_tags": ["en:palm-oil-free", "en:vegan", "en:vegetarian"],
        "nova_group": 4,
        "nutriscore_grade": "e",
        "serving_quantity": "355",
        "serving_size": "12 fl oz (355 ml)",
        "nutriments": {"energy-kcal_100g": 42, "fat_100g": 0, "saturated-fat_100g": 0, "carbohydrates_100g": 10.6,
                       "sugars_100g": 10.6, "proteins_100g": 0, "salt_100g": 0.03, "sodium_100g": 0.012},
        "image_front_url": "https://images.openfoodfacts.org/test/front.jpg",
    }
    p.update(overrides)
    return {"status": 1, "product": p}


COLA = "0049000000443"  # valid UPC-A check digit in EAN-13 form


def mock_off_product(respx_mock, code: str, payload: dict | None = None, status: int = 200):
    route = respx_mock.get(f"{OFF}/api/v2/product/{code}.json")
    if payload is None:
        route.respond(404, json={"status": 0, "status_verbose": "product not found"})
    else:
        route.respond(status, json=payload)
    return route
