"""API integration tests against a real SQLite database with mocked external providers."""

import hashlib
import hmac
import io
import json
import time

import httpx
import respx
from PIL import Image

from tests.conftest import COLA, OFF, mock_off_product, off_product, register

API = "/api/v1"


# ------------------------------------------------------------------ auth, profiles, privacy
def test_register_login_me(client):
    h = register(client, "alice@example.com")
    me = client.get(f"{API}/me", headers=h).json()
    assert me["email"] == "alice@example.com" and me["tier"] == "free" and me["region"] == "US"
    assert me["currency"] == "USD"
    r = client.post(f"{API}/auth/login", json={"email": "alice@example.com", "password": "wrong-Pass1"})
    assert r.status_code == 401
    assert client.get(f"{API}/me").status_code == 401
    assert client.get(f"{API}/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_weak_password_and_terms_rejected(client):
    r = client.post(f"{API}/auth/register", json={"email": "w@example.com", "password": "alllowercase",
                                                  "accept_terms": True})
    assert r.status_code == 422
    r = client.post(f"{API}/auth/register", json={"email": "w2@example.com", "password": "Good1Pass",
                                                  "accept_terms": False})
    assert r.status_code == 422


def test_dietary_profile_and_family(client):
    h = register(client)
    profiles = client.get(f"{API}/profiles", headers=h).json()
    me = profiles[0]
    assert me["is_primary"]
    r = client.put(f"{API}/profiles/{me['id']}/allergens", headers=h,
                   json=[{"code": "peanuts", "severity": "anaphylaxis"}, {"code": "milk", "severity": "intolerance",
                                                                            "avoid_traces": False}])
    assert r.status_code == 200 and len(r.json()["allergens"]) == 2
    assert client.put(f"{API}/profiles/{me['id']}/diets", headers=h, json=["vegan", "low_sodium"]).status_code == 200
    assert client.put(f"{API}/profiles/{me['id']}/diets", headers=h, json=["paleo-ish"]).status_code == 422
    assert client.put(f"{API}/profiles/{me['id']}/avoid", headers=h, json=["Palm Oil", "E171"]).json()["avoid"] == \
        ["e171", "palm oil"]
    # free plan: one profile only
    r = client.post(f"{API}/profiles", headers=h, json={"name": "Kid"})
    assert r.status_code == 402 and r.json()["detail"]["code"] == "plan_limit"


def test_health_data_requires_consent(client):
    h = register(client, consent=False)
    pid = client.get(f"{API}/profiles", headers=h).json()[0]["id"]
    r = client.put(f"{API}/profiles/{pid}/allergens", headers=h, json=[{"code": "milk"}])
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required"
    client.patch(f"{API}/me", headers=h, json={"consent_health_data": True})
    assert client.put(f"{API}/profiles/{pid}/allergens", headers=h, json=[{"code": "milk"}]).status_code == 200
    # withdrawing consent deletes the health data
    client.patch(f"{API}/me", headers=h, json={"consent_health_data": False})
    assert client.get(f"{API}/profiles/{pid}", headers=h).json()["allergens"] == []


def test_cannot_access_other_users_profile(client):
    a, b = register(client), register(client)
    pid = client.get(f"{API}/profiles", headers=a).json()[0]["id"]
    assert client.get(f"{API}/profiles/{pid}", headers=b).status_code == 404


# ------------------------------------------------------------------ scanning
@respx.mock(assert_all_called=False)
def test_scan_found_analysed_and_cached(respx_mock, client):
    h = register(client)
    pid = client.get(f"{API}/profiles", headers=h).json()[0]["id"]
    client.put(f"{API}/profiles/{pid}/diets", headers=h, json=["low_sugar"])
    route = mock_off_product(respx_mock, COLA, off_product(COLA))
    r = client.get(f"{API}/products/barcode/{COLA}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["product"]["name"] == "Test Cola"
    assert body["product"]["provenance"]["source"] == "off"
    assert "Open Database License" in body["product"]["provenance"]["attribution"]
    sc = body["analysis"]["score"]
    assert sc["grade"] == "poor" and sc["methodology_version"]
    assert body["analysis"]["compatibility"][0]["verdict"] == "red"
    assert route.call_count == 1
    # Second scan via the UPC-A form hits the cache (same GTIN-14)
    r2 = client.get(f"{API}/products/barcode/049000000443", headers=h)
    assert r2.status_code == 200 and r2.json()["sources"] == ["cache"] and route.call_count == 1
    hist = client.get(f"{API}/history", headers=h).json()
    assert hist[0]["scan_count"] == 2 and hist[0]["product"]["name"] == "Test Cola"


@respx.mock(assert_all_called=False)
def test_scan_not_found_and_invalid(respx_mock, client):
    mock_off_product(respx_mock, "0012345678905", None)
    r = client.get(f"{API}/products/barcode/012345678905")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "product_not_found"
    r = client.get(f"{API}/products/barcode/012345678906")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_barcode"


@respx.mock(assert_all_called=False)
def test_provider_down_is_graceful(respx_mock, client):
    respx_mock.get(f"{OFF}/api/v2/product/0076543210985.json").mock(side_effect=httpx.ConnectError("down"))
    r = client.get(f"{API}/products/barcode/076543210985")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "provider_unavailable"


@respx.mock(assert_all_called=False)
def test_offline_sync_idempotent(respx_mock, client):
    h = register(client)
    mock_off_product(respx_mock, "3017620422003", off_product("3017620422003", product_name="Spread",
                                                              categories_tags=["en:spreads"]))
    batch = [{"client_id": "offline-0001", "barcode": "3017620422003", "scanned_at": "2026-11-01T10:00:00Z"},
             {"client_id": "offline-0002", "barcode": "123", "scanned_at": "2026-11-01T10:01:00Z"}]
    r = client.post(f"{API}/scans/sync", headers=h, json=batch).json()["results"]
    assert r[0]["status"] == "found" and r[1]["status"] == "invalid"
    client.post(f"{API}/scans/sync", headers=h, json=batch)
    hist = client.get(f"{API}/history", headers=h).json()
    assert len(hist) == 1 and hist[0]["scan_count"] == 1


def test_text_analysis_from_ocr(client):
    r = client.post(f"{API}/analysis/text", json={
        "ingredients_text": "INGREDIENTS: ENRICHED FLOUR (WHEAT FLOUR, NIACIN), SUGAR, PALM OIL, RED 40. "
                            "CONTAINS: WHEAT. MAY CONTAIN MILK.",
        "nutrition_text": "Serving size 30g\nCalories 140\nTotal Fat 6g 8%\nSaturated Fat 3g 15%\nSodium 95mg 4%\n"
                          "Total Carbohydrate 20g 7%\nTotal Sugars 9g\nIncludes 9g Added Sugars 18%\nProtein 1g"})
    assert r.status_code == 200, r.text
    d = r.json()
    allergens = {a["code"]: a["status"] for a in d["allergens"]}
    assert allergens["wheat"] == "contains" and allergens["milk"] == "may_contain"
    assert d["nutrition_per_100"]["added_sugars"] == 30.0
    assert d["score"]["overall"] is not None
    assert any(i["ingredient"] and i["ingredient"]["slug"] == "allura-red" for i in d["ingredients"])


# ------------------------------------------------------------------ alternatives & compare
@respx.mock(assert_all_called=False)
def test_alternatives_and_compare(respx_mock, client):
    h = register(client)
    base = "5000000000012"
    better = "5000000000029"
    mock_off_product(respx_mock, base, off_product(base, product_name="Sugary Soda",
                                                   categories_tags=["en:beverages", "en:sodas-test"]))
    diet = off_product(better, product_name="Sparkling Water Lemon", brands="Clear",
                       categories_tags=["en:beverages", "en:sodas-test"], nova_group=1,
                       ingredients_text="Carbonated water, lemon juice",
                       nutriments={"energy-kcal_100g": 1, "fat_100g": 0, "saturated-fat_100g": 0,
                                   "carbohydrates_100g": 0.1, "sugars_100g": 0.1, "proteins_100g": 0, "salt_100g": 0})
    respx_mock.get(f"{OFF}/api/v2/search").respond(200, json={"products": [diet["product"]]})
    pid = client.get(f"{API}/products/barcode/{base}", headers=h).json()["product"]["id"]
    alt = client.get(f"{API}/products/{pid}/alternatives", headers=h).json()
    assert alt["alternatives"], alt
    a0 = alt["alternatives"][0]
    assert a0["product"]["name"] == "Sparkling Water Lemon" and a0["score_delta"] > 0
    assert any("Less sugar" in b for b in a0["reasons"]["better"])
    cmp = client.post(f"{API}/compare", headers=h, json={"product_ids": [pid, a0["product"]["id"]],
                                                          "objective": "lowest_sugar"}).json()
    assert cmp["best"]["name"] == "Sparkling Water Lemon"
    shared = client.get(f"{API}/compare/{cmp['share_token']}").json()
    assert "compatibility" not in shared["products"][0]


# ------------------------------------------------------------------ user data
@respx.mock(assert_all_called=False)
def test_favourites_lists_diary_export_delete(respx_mock, client):
    h = register(client)
    code = "4006381333931"
    mock_off_product(respx_mock, code, off_product(code, product_name="Granola", categories_tags=["en:cereals"],
                                                   is_beverage=False, serving_quantity="50",
                                                   nutriments={"energy-kcal_100g": 450, "fat_100g": 18,
                                                               "saturated-fat_100g": 3, "carbohydrates_100g": 60,
                                                               "sugars_100g": 20, "fiber_100g": 7,
                                                               "proteins_100g": 10, "salt_100g": 0.3}))
    pid = client.get(f"{API}/products/barcode/{code}", headers=h).json()["product"]["id"]
    assert client.post(f"{API}/favourites", headers=h, json={"product_id": pid}).status_code == 201
    assert client.post(f"{API}/favourites", headers=h, json={"product_id": pid, "list_type": "trusted"}).status_code == 201
    assert len(client.get(f"{API}/favourites", headers=h).json()) == 1
    sl = client.post(f"{API}/shopping-lists", headers=h, json={"name": "Weekly"}).json()
    sl = client.post(f"{API}/shopping-lists/{sl['id']}/items", headers=h, json={"product_id": pid}).json()
    item = sl["items"][0]
    sl = client.patch(f"{API}/shopping-lists/{sl['id']}/items/{item['id']}", headers=h, json={"checked": True}).json()
    assert sl["items"][0]["checked"]
    e = client.post(f"{API}/diary/entries", headers=h, json={"meal_type": "breakfast", "product_id": pid}).json()
    assert e["quantity_g"] == 50 and e["energy_kcal"] == 225 and not e["is_estimate"]
    client.post(f"{API}/diary/entries", headers=h, json={"meal_type": "lunch", "description": "Jollof rice",
                                                          "energy_kcal": 500, "is_estimate": True})
    day = client.get(f"{API}/diary", headers=h).json()
    assert day["totals"]["energy_kcal"] == 725 and day["totals"]["includes_estimates"]
    assert client.get(f"{API}/diary/summary?days=7", headers=h).json()["days_logged"] == 1
    export = client.get(f"{API}/me/export", headers=h).json()
    assert export["scan_history"] and export["favourites"] and export["food_diary"]
    assert "password_hash" not in json.dumps(export)
    assert client.request("DELETE", f"{API}/me", headers=h, json={"confirm": "nope"}).status_code == 422
    assert client.request("DELETE", f"{API}/me", headers=h, json={"confirm": "DELETE"}).status_code == 204
    assert client.get(f"{API}/me", headers=h).status_code == 401


# ------------------------------------------------------------------ submissions & admin
def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 50, 50)).save(buf, "JPEG")
    return buf.getvalue()


@respx.mock(assert_all_called=False)
def test_unknown_product_submission_and_moderation(respx_mock, client, admin_headers):
    h = register(client)
    code = "0036000291452"
    mock_off_product(respx_mock, code, None)
    assert client.get(f"{API}/products/barcode/{code}").status_code == 404
    up = client.post(f"{API}/uploads", headers=h, files={"image": ("front.jpg", _jpeg(), "image/jpeg")})
    assert up.status_code == 201
    bad = client.post(f"{API}/uploads", headers=h, files={"image": ("x.jpg", b"not an image", "image/jpeg")})
    assert bad.status_code == 415
    sub = client.post(f"{API}/submissions", headers=h, json={
        "barcode": code, "name": "Local Plantain Chips", "brand": "Corner Shop",
        "ingredients_text": "Plantain, palm oil, salt", "image_ids": [up.json()["image_id"]], "ocr_confidence": 0.82,
        "nutrition": {"energy_kcal": 520, "fat": 28, "saturated_fat": 12, "carbohydrates": 62, "sugars": 2,
                      "protein": 2, "salt": 0.9}})
    assert sub.status_code == 201, sub.text
    assert client.post(f"{API}/submissions", headers=h, json={"barcode": code, "name": "Dup"}).status_code == 409
    # RBAC: normal users can't moderate
    assert client.get(f"{API}/admin/submissions", headers=h).status_code == 403
    queue = client.get(f"{API}/admin/submissions", headers=admin_headers).json()
    assert any(s["id"] == sub.json()["id"] for s in queue)
    r = client.post(f"{API}/admin/submissions/{sub.json()['id']}/review", headers=admin_headers,
                    json={"action": "approve", "notes": "Checked against photo"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    found = client.get(f"{API}/products/barcode/{code}").json()
    assert found["product"]["name"] == "Local Plantain Chips" and found["product"]["provenance"]["source"] == "community"
    assert found["product"]["provenance"]["verified_at"]
    mine = client.get(f"{API}/submissions/mine", headers=h).json()
    assert mine[0]["status"] == "approved"
    notes = client.get(f"{API}/notifications", headers=h).json()
    assert notes and notes[0]["kind"] == "submission"
    logs = client.get(f"{API}/admin/audit-logs?action=submission", headers=admin_headers).json()
    assert logs and logs[0]["action"] == "submission.approve"


def test_admin_methodology_versioning(client, admin_headers):
    ms = client.get(f"{API}/admin/methodologies", headers=admin_headers).json()
    active = next(m for m in ms if m["is_active"])
    cfg = active["config"]
    cfg["weights"] = {**cfg["weights"], "nutrition": 45, "ingredients": 20}
    r = client.post(f"{API}/admin/methodologies", headers=admin_headers,
                    json={"version": "2026.12-us.2", "name": "Tuned", "config": cfg, "notes": "More nutrition weight",
                          "activate": True})
    assert r.status_code == 201, r.text
    assert client.post(f"{API}/admin/methodologies", headers=admin_headers,
                       json={"version": "2026.12-us.2", "name": "x", "config": cfg, "notes": "dup"}).status_code == 409
    bad = {**cfg, "weights": {**cfg["weights"], "nutrition": 90}}
    assert client.post(f"{API}/admin/methodologies", headers=admin_headers,
                       json={"version": "2026.12-us.3", "name": "x", "config": bad, "notes": "bad"}).status_code == 422
    sc = client.post(f"{API}/analysis/text", json={"ingredients_text": "Oats", "nutrition": {
        "energy_kcal": 375, "fat": 8, "saturated_fat": 1.5, "carbohydrates": 60, "sugars": 1, "protein": 11,
        "salt": 0}}).json()["score"]
    assert sc["methodology_version"] == "2026.12-us.2"
    # restore the default for other tests
    client.post(f"{API}/admin/methodologies/{active['version']}/activate", headers=admin_headers)


@respx.mock(assert_all_called=False)
def test_recall_notifies_users_and_zeroes_score(respx_mock, client, admin_headers):
    h = register(client)
    code = "0041220576074"
    mock_off_product(respx_mock, code, off_product(code, product_name="Recalled Snack",
                                                   categories_tags=["en:snacks"]))
    client.get(f"{API}/products/barcode/{code}", headers=h)
    r = client.post(f"{API}/admin/recalls", headers=admin_headers, json={
        "title": "Undeclared peanuts", "reason": "May contain undeclared peanut", "hazard": "undeclared_allergen",
        "jurisdiction": "US", "authority": "FDA", "barcode": code})
    assert r.status_code == 201 and r.json()["notified_users"] == 1
    body = client.get(f"{API}/products/barcode/{code}", headers=h).json()
    assert body["analysis"]["score"]["overall"] == 0 and body["analysis"]["recalls"]
    assert client.get(f"{API}/notifications", headers=h).json()[0]["kind"] == "recall"


def test_admin_ingredient_edit_requires_admin(client, admin_headers):
    h = register(client)
    body = {"concern_level": "caution", "reason": "test", "verify": True}
    assert client.patch(f"{API}/admin/ingredients/sucralose", headers=h, json=body).status_code == 403
    r = client.patch(f"{API}/admin/ingredients/sucralose", headers=admin_headers, json=body)
    assert r.status_code == 200 and r.json()["verification_status"] == "verified"
    ing = client.get(f"{API}/ingredients/sucralose").json()
    assert ing["verification_status"] == "verified" and ing["sources"][0]["key"] == "who_nss_2023"


def test_ingredient_encyclopedia_search(client):
    r = client.get(f"{API}/ingredients?q=red 40").json()
    assert r["items"][0]["slug"] == "allura-red" and r["items"][0]["name"].startswith("Red 40")
    assert client.get(f"{API}/ingredients?q=e171").json()["items"][0]["slug"] == "titanium-dioxide"
    assert client.get(f"{API}/ingredients/does-not-exist").status_code == 404


# ------------------------------------------------------------------ billing & AI quotas
def _stripe_sig(payload: bytes, secret="whsec_test", ts=None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_stripe_webhook_grants_entitlement_idempotently(client):
    h = register(client)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    event = {"id": "evt_1", "type": "customer.subscription.created", "data": {"object": {
        "id": "sub_1", "status": "active", "metadata": {"user_id": uid, "tier": "premium"},
        "current_period_end": int(time.time()) + 86400 * 30,
        "items": {"data": [{"price": {"recurring": {"interval": "month"}}}]}}}}
    payload = json.dumps(event).encode()
    bad = client.post(f"{API}/billing/webhooks/stripe", content=payload, headers={"Stripe-Signature": "t=1,v1=bad"})
    assert bad.status_code == 400
    r = client.post(f"{API}/billing/webhooks/stripe", content=payload, headers={"Stripe-Signature": _stripe_sig(payload)})
    assert r.json()["result"] == "processed"
    r = client.post(f"{API}/billing/webhooks/stripe", content=payload, headers={"Stripe-Signature": _stripe_sig(payload)})
    assert r.json()["result"] == "duplicate"
    assert client.get(f"{API}/me", headers=h).json()["tier"] == "premium"
    # premium allows extra profiles
    assert client.post(f"{API}/profiles", headers=h, json={"name": "Partner"}).status_code == 201


def test_revenuecat_and_paystack_webhooks(client):
    h = register(client)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    body = {"event": {"id": "rc_1", "type": "INITIAL_PURCHASE", "app_user_id": uid, "product_id": "omniscan_family_monthly",
                      "expiration_at_ms": int(time.time() * 1000) + 86400000, "original_transaction_id": "t1"}}
    assert client.post(f"{API}/billing/webhooks/revenuecat", json=body, headers={"Authorization": "wrong"}).status_code == 401
    assert client.post(f"{API}/billing/webhooks/revenuecat", json=body,
                       headers={"Authorization": "Bearer rc-test-auth"}).json()["result"] == "processed"
    assert client.get(f"{API}/me", headers=h).json()["tier"] == "family"
    ps_body = json.dumps({"event": "charge.success", "data": {"id": 99, "reference": "ref1",
                                                               "metadata": {"user_id": uid, "tier": "plus"}}}).encode()
    sig = hmac.new(b"sk_test_paystack", ps_body, hashlib.sha512).hexdigest()
    assert client.post(f"{API}/billing/webhooks/paystack", content=ps_body,
                       headers={"x-paystack-signature": "bad"}).status_code == 401
    assert client.post(f"{API}/billing/webhooks/paystack", content=ps_body,
                       headers={"x-paystack-signature": sig}).json()["result"] == "processed"


def test_ai_not_configured_is_explicit(client):
    h = register(client)
    r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "Is this healthy?"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_not_configured"


@respx.mock(assert_all_called=False)
def test_ai_assistant_grounded_and_quota(respx_mock, client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h = register(client)
    gem = respx_mock.post(url__regex=r"https://generativelanguage\.googleapis\.com/.*generateContent").respond(200, json={
        "candidates": [{"content": {"parts": [{"text": "It contains Red 40 [eu_reg_1333_2008]."}]}}],
        "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 40}})
    for _ in range(5):
        r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "What is Red 40?",
                                                                 "ingredient_slugs": ["allura-red"]})
        assert r.status_code == 200, r.text
    sent = json.loads(gem.calls.last.request.content)
    assert "STRICT GROUNDING RULES" in sent["systemInstruction"]["parts"][0]["text"]
    assert "Allura" in sent["contents"][-1]["parts"][0]["text"]
    assert r.json()["disclaimer"] and r.json()["ai_generated"]
    r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "One more?"})
    assert r.status_code == 402 and r.json()["detail"]["code"] == "quota_exceeded"
    assert client.get(f"{API}/me/usage", headers=h).json()["features"]["ai_assistant"]["used"] == 5


@respx.mock(assert_all_called=False)
def test_failed_ai_call_not_charged(respx_mock, client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h = register(client)
    respx_mock.post(url__regex=r".*generateContent").respond(500, json={"error": "boom"})
    r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "hi there"})
    assert r.status_code == 502
    assert client.get(f"{API}/me/usage", headers=h).json()["features"]["ai_assistant"]["used"] == 0


@respx.mock(assert_all_called=False)
def test_ai_label_photo_keeps_allergen_statements(respx_mock, client, monkeypatch):
    """Vision output often drops "Contains:" / "May contain"; we must re-label, not lose or promote them."""
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h = register(client)
    extracted = {"ingredients_text": "WHOLE GRAIN OATS, SUGAR, SALT, RED 40.", "contains_statement": "WHEAT.",
                 "may_contain_statement": "PEANUTS.", "legibility": "good", "language": "en"}
    respx_mock.post(url__regex=r".*generateContent").respond(200, json={
        "candidates": [{"content": {"parts": [{"text": json.dumps(extracted)}]}}],
        "usageMetadata": {"promptTokenCount": 900, "candidatesTokenCount": 60}})
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "JPEG")
    r = client.post(f"{API}/analysis/image", headers=h, data={"task": "ingredients"},
                    files={"image": ("photo.jpg", buf.getvalue(), "image/jpeg")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ingredients_text"].endswith("Contains: WHEAT.\nMay contain: PEANUTS.")
    status = {a["code"]: a["status"] for a in body["analysis"]["allergens"]}
    assert status["wheat"] == "contains" and status["peanuts"] == "may_contain"


def test_plans_and_meta(client):
    plans = client.get(f"{API}/billing/plans").json()
    assert [p["monthly_usd"] for p in plans] == [0, 3.99, 7.99, 11.99]
    meta = client.get(f"{API}/meta").json()
    assert meta["default_region"] == "US" and meta["default_currency"] == "USD"
    assert client.get("/health").headers["x-content-type-options"] == "nosniff"
