"""Plan gating, tracking, recipes, meal plans, pantry, households, budget, discovery, alerts, admin content."""

import json
from datetime import UTC, date, datetime, timedelta

import respx

from app.models import PantryItem, Subscription, User
from app.services import alerts
from tests.conftest import mock_off_product, off_product, register

API = "/api/v1"


def ean13(body12: str) -> str:
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body12))
    return body12 + str((10 - s % 10) % 10)


def upgrade(db, headers_email: str, tier: str):
    u = db.query(User).filter(User.email == headers_email).one()
    db.add(Subscription(user_id=u.id, tier=tier, status="active", provider="manual",
                        current_period_end=datetime.now(UTC) + timedelta(days=30)))
    db.commit()


def new_user(client, db, tier: str | None = None, email: str | None = None):
    email = email or f"life{datetime.now().timestamp()}@example.com".replace(".", "", 1)
    h = register(client, email)
    if tier:
        upgrade(db, email, tier)
    return h, email


def gemini(respx_mock, payload: dict):
    return respx_mock.post(url__regex=r".*generateContent").respond(200, json={
        "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
        "usageMetadata": {"promptTokenCount": 500, "candidatesTokenCount": 300}})


# ------------------------------------------------------------------ plan gating


def test_free_user_sees_upgrade_prompt_and_paid_user_gets_access(client, db):
    h, email = new_user(client, db)
    r = client.get(f"{API}/pantry", headers=h)
    assert r.status_code == 402
    d = r.json()["detail"]
    assert d["code"] == "upgrade_required" and d["required_tier"] == "plus" and "Plus" in d["message"]
    upgrade(db, email, "plus")
    assert client.get(f"{API}/pantry", headers=h).status_code == 200
    # Household needs Family even on Plus
    assert client.post(f"{API}/household", headers=h, json={"name": "Home"}).json()["detail"]["required_tier"] == \
        "family"
    usage = client.get(f"{API}/billing/me", headers=h).json()
    assert usage["tier"] == "plus" and usage["features"]["pantry"]["included"] is True
    assert usage["features"]["health_insights"]["included"] is False
    plans = client.get(f"{API}/billing/plans").json()
    assert plans[0]["limits"]["pantry"] == 0 and "pantry" in plans[0]["feature_labels"]


def test_safety_features_stay_free(client, db):
    h, _ = new_user(client, db)
    assert client.get(f"{API}/safety/topics", headers=h).status_code == 200
    assert client.get(f"{API}/articles").status_code == 200
    assert client.get(f"{API}/local-foods").status_code == 200
    assert client.get(f"{API}/recipes").status_code == 200


# ------------------------------------------------------------------ diary: water, targets, servings, micros, reports


@respx.mock(assert_all_called=False)
def test_diary_tracking_micros_and_reports(respx_mock, client, db):
    code = ean13("501234500001")
    mock_off_product(respx_mock, code, off_product(code, product_name="Fortified Cereal", nutriments={
        "energy-kcal_100g": 380, "fat_100g": 2, "saturated-fat_100g": 0.5, "carbohydrates_100g": 80,
        "sugars_100g": 20, "fiber_100g": 6, "proteins_100g": 8, "salt_100g": 0.8,
        "iron_100g": 0.012, "vitamin-d_100g": 0.0000042, "calcium_100g": 0.4,
    }, serving_quantity="30", categories_tags=["en:breakfast-cereals"]))
    h, email = new_user(client, db)
    pid = client.get(f"{API}/products/barcode/{code}", headers=h).json()["product"]["id"]
    prod = client.get(f"{API}/products/{pid}").json()["product"]
    iron = next(m for m in prod["nutrition"]["micros_per_100"] if m["key"] == "iron")
    assert iron["amount"] == 12 and iron["unit"] == "mg" and iron["pct_dv"] == 67

    e = client.post(f"{API}/diary/entries", headers=h, json={"meal_type": "breakfast", "product_id": pid,
                                                             "servings": 2}).json()
    assert e["quantity_g"] == 60 and e["energy_kcal"] == 228 and "micros" not in e  # micros are Plus
    assert client.post(f"{API}/diary/water", headers=h, json={"ml": 500}).json()["total_ml"] == 500
    client.post(f"{API}/diary/water", headers=h, json={"ml": 250})
    goals = client.put(f"{API}/diary/goals", headers=h, json={"goals": {"protein": 90, "water_ml": 2500}}).json()
    assert goals["targets"]["protein"] == 90 and goals["targets"]["energy_kcal"] == 2000
    assert client.put(f"{API}/diary/goals", headers=h, json={"goals": {"bogus": 1}}).status_code == 422
    day = client.get(f"{API}/diary", headers=h).json()
    assert day["water"]["total_ml"] == 750 and day["micros_locked"] is True and day["targets"]["water_ml"] == 2500
    assert client.put(f"{API}/diary/weight", headers=h, json={"weight_kg": 70.5}).status_code == 200
    assert client.get(f"{API}/diary/weight", headers=h).json()["entries"][0]["weight_kg"] == 70.5

    assert client.get(f"{API}/diary/report", headers=h).status_code == 402
    upgrade(db, email, "plus")
    day = client.get(f"{API}/diary", headers=h).json()
    assert day["micros"]["iron"]["amount"] == 7.2  # 60 g x 12 mg/100 g
    rep = client.get(f"{API}/diary/report?period=week", headers=h).json()
    assert rep["days_logged"] == 1 and rep["averages"]["energy_kcal"] == 228 and len(rep["days"]) == 7
    assert client.get(f"{API}/diary/insights", headers=h).json()["detail"]["required_tier"] == "premium"


def test_insights_need_three_days_and_never_diagnose(client, db):
    h, email = new_user(client, db, "premium")
    today = date.today()
    for i in range(4):
        client.post(f"{API}/diary/entries", headers=h, json={
            "day": (today - timedelta(days=i)).isoformat(), "meal_type": "lunch", "description": "Rice",
            "energy_kcal": 700, "protein": 10, "fiber": 2, "sodium_mg": 3000})
    ins = client.get(f"{API}/diary/insights?days=7", headers=h).json()
    msgs = " ".join(i["message"] for i in ins["insights"])
    assert "Protein was below 70% of your target" in msgs and "Sodium was above your target" in msgs
    assert "diagnos" in msgs  # explicit "isn't a diagnosis"
    assert "Not medical advice" in ins["disclaimer"]


def test_bulk_meal_photo_entries_are_estimates(client, db):
    h, _ = new_user(client, db)
    r = client.post(f"{API}/diary/entries/bulk", headers=h, json={"entries": [
        {"meal_type": "dinner", "description": "Jollof rice", "energy_kcal": 450, "is_estimate": True},
        {"meal_type": "dinner", "description": "Fried plantain", "energy_kcal": 220, "is_estimate": True},
    ]})
    assert r.status_code == 201 and all(e["is_estimate"] and e["source"] == "ai_estimate" for e in r.json())
    assert client.get(f"{API}/diary", headers=h).json()["totals"]["includes_estimates"] is True


# ------------------------------------------------------------------ recipes & meal plans


def test_recipes_compatibility_substitutions_and_shopping_list(client, db):
    h, _ = new_user(client, db)
    pid = client.get(f"{API}/profiles", headers=h).json()[0]["id"]
    client.put(f"{API}/profiles/{pid}/allergens", headers=h,
               json=[{"code": "fish", "severity": "severe"}, {"code": "crustaceans", "severity": "severe"}])
    nigerian = client.get(f"{API}/recipes?region=NG").json()
    assert {"Jollof rice", "Egusi soup", "Moi moi"} <= {r["title"] for r in nigerian}
    egusi = next(r for r in nigerian if r["title"] == "Egusi soup")
    full = client.get(f"{API}/recipes/{egusi['id']}", headers=h).json()
    assert full["nutrition_per_serving"] is None  # no invented numbers
    verdict = full["compatibility"]["profiles"][0]["verdict"]
    assert verdict == "red"
    subs = full["compatibility"]["substitutions"]
    assert any(s["because"] == "crustaceans" and "ground crayfish" in s["replace"] for s in subs)
    r = client.post(f"{API}/recipes/{egusi['id']}/shopping-list", headers=h, json={"servings": 3}).json()
    assert r["added"] >= 8 and any(i["text"] == "ground egusi (melon seeds)" and i["quantity"] == "1 cups"
                                   for i in r["list"]["items"])
    again = client.post(f"{API}/recipes/{egusi['id']}/shopping-list", headers=h,
                        json={"list_id": r["list"]["id"]}).json()
    assert again["added"] == 0  # no duplicates


@respx.mock(assert_all_called=False)
def test_ai_recipe_and_meal_plan_are_gated_and_labelled(respx_mock, client, db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h, email = new_user(client, db)
    assert client.post(f"{API}/recipes/generate", headers=h, json={"request": "bean stew"}).status_code == 402
    assert client.post(f"{API}/meal-plans", headers=h, json={"name": "Week"}).status_code == 402
    upgrade(db, email, "premium")
    gemini(respx_mock, {"title": "Quick bean stew", "description": "Beans in pepper sauce", "cuisine": "Nigerian",
                        "servings": 4, "time_minutes": 40, "ingredients": [{"name": "beans", "quantity": 2,
                                                                             "unit": "cups"}],
                        "steps": ["Cook"], "diet_tags": ["vegan"], "tags": ["nigerian"],
                        "preparation_notes": "Boiled", "nutrition_per_serving_estimate": {"energy_kcal": 300}})
    rec = client.post(f"{API}/recipes/generate", headers=h, json={"request": "bean stew", "region": "NG"}).json()
    assert rec["ai_generated"] and rec["nutrition_is_estimate"] and "estimate" in rec["notice"]
    assert rec["mine"] and rec["id"] not in {r["id"] for r in client.get(f"{API}/recipes").json() if not r["mine"]}

    gemini(respx_mock, {"name": "Naija week", "days": [{"day": 1, "meals": [
        {"meal_type": "breakfast", "title": "Moi moi", "description": "Steamed", "estimated_kcal": 300},
        {"meal_type": "dinner", "title": "Unknown dish", "estimated_kcal": 600},
        {"meal_type": "brunch", "title": "Ignored"}]}], "notes": "Approximate"})
    plan = client.post(f"{API}/meal-plans/generate", headers=h, json={"days": 1, "region": "NG"}).json()
    meals = plan["days"][0]["meals"]
    assert [m["title"] for m in meals] == ["Moi moi", "Unknown dish"]
    assert meals[0]["recipe_id"] and meals[1]["recipe_id"] is None
    sl = client.post(f"{API}/meal-plans/{plan['id']}/shopping-list", headers=h, json={}).json()
    assert sl["meals_without_recipe"] == ["Unknown dish"] and sl["added"] >= 5
    usage = client.get(f"{API}/billing/me", headers=h).json()["features"]
    assert usage["ai_recipes"]["used"] == 1 and usage["ai_meal_plans"]["used"] == 1


# ------------------------------------------------------------------ pantry, household, budget


def test_pantry_expiry_household_sharing_and_budget(client, db):
    owner_h, owner_email = new_user(client, db, "family")
    member_h, member_email = new_user(client, db)  # free plan: can still use shared items
    item = client.post(f"{API}/pantry", headers=owner_h, json={
        "name": "Milk", "location": "fridge", "expires_on": (date.today() + timedelta(days=1)).isoformat()}).json()
    assert item["status"] == "soon" and item["days_left"] == 1
    assert [i["name"] for i in client.get(f"{API}/pantry/expiring", headers=owner_h).json()] == ["Milk"]
    assert alerts.expiry_reminders(db) >= 1
    assert alerts.expiry_reminders(db) == 0  # only once per item
    notes = client.get(f"{API}/notifications", headers=owner_h).json()
    assert any(n["kind"] == "expiry" and "Milk" in n["title"] for n in notes)

    hh = client.post(f"{API}/household", headers=owner_h, json={"name": "Our home"}).json()
    client.post(f"{API}/household/invite", headers=owner_h, json={"email": member_email})
    invites = client.get(f"{API}/household", headers=member_h).json()["invites"]
    assert invites and invites[0]["household"] == "Our home"
    assert client.post(f"{API}/household/invites/{invites[0]['id']}/accept", headers=member_h).status_code == 200
    shared = client.post(f"{API}/shopping-lists", headers=owner_h, json={"name": "Shared", "shared_with_family": True})
    assert shared.json()["household_id"] == hh["id"]
    assert "Shared" in [sl["name"] for sl in client.get(f"{API}/shopping-lists", headers=member_h).json()]
    item2 = client.post(f"{API}/pantry", headers=owner_h, json={"name": "Rice", "shared": True}).json()
    # Member is on the free plan: pantry access is a Plus feature for their own use
    assert client.get(f"{API}/pantry", headers=member_h).status_code == 402
    assert client.delete(f"{API}/shopping-lists/{shared.json()['id']}", headers=member_h).status_code == 403

    assert client.put(f"{API}/budget", headers=owner_h, json={"monthly_amount": 150000, "currency": "NGN"}).json()[
        "shared"]
    client.post(f"{API}/purchases", headers=owner_h, json={"name": "Rice 5kg", "price": 12000, "currency": "NGN",
                                                           "store": "Shoprite"})
    client.post(f"{API}/purchases", headers=owner_h, json={"name": "Oil", "price": 4500, "currency": "NGN",
                                                           "store": "Market"})
    s = client.get(f"{API}/budget", headers=owner_h).json()
    assert s["spent"] == 16500 and s["remaining"] == 133500 and list(s["by_store"]) == ["Shoprite", "Market"]
    assert item2["shared"] is True
    db.expire_all()
    assert db.get(PantryItem, item["id"]).reminded_at is not None


# ------------------------------------------------------------------ discovery


@respx.mock(assert_all_called=False)
def test_rankings_share_prices_and_details(respx_mock, client, db, admin_headers):
    codes = []
    for i, (sugar, fiber) in enumerate([(1, 9), (5, 6), (12, 4), (20, 2), (30, 1), (40, 0.5), (8, 5)]):
        code = ean13(f"60000000{i:04d}")
        codes.append(code)
        r = client.post(f"{API}/admin/products", headers=admin_headers, json={
            "barcode": code, "name": f"Cracker {i}", "brand": "Testco", "category": "Test Crackers",
            "ingredients_text": "wheat flour, sunflower oil, salt",
            "nutrition": {"energy_kcal": 420, "fat": 12, "saturated_fat": 2, "carbohydrates": 65, "sugars": sugar,
                          "fiber": fiber, "protein": 9, "salt": 1.0},
            "countries": ["nigeria"], "nafdac_number": "A1-1234"})
        assert r.status_code == 201, r.text
    cat = next(c for c in client.get(f"{API}/categories").json() if c["name"] == "Test Crackers")
    h, email = new_user(client, db)
    free = client.get(f"{API}/rankings", headers=h, params={"category": cat["code"], "country": "NG"}).json()
    assert free["total"] == 7 and len(free["results"]) == 5 and free["locked"]
    scores = [r["score"] for r in free["results"]]
    assert scores == sorted(scores, reverse=True) and free["best_in_category"]["name"] == "Cracker 0"
    upgrade(db, email, "plus")
    assert len(client.get(f"{API}/rankings", headers=h, params={"category": cat["code"]}).json()["results"]) == 7

    pid = free["results"][0]["id"]
    tok = client.post(f"{API}/products/{pid}/share", headers=h).json()["token"]
    shared = client.get(f"{API}/shared/{tok}").json()
    assert shared["shared"] and shared["analysis"]["compatibility"] == []
    details = client.get(f"{API}/products/{pid}/details").json()
    assert details["nafdac"]["format_ok"] and "greenbook" in details["nafdac"]["check_url"]
    assert details["history"][0]["action"] == "product.create"

    free_h, _ = new_user(client, db)
    client.post(f"{API}/products/{pid}/prices", headers=free_h,
                json={"price": 950, "currency": "NGN", "store": "Shoprite", "city": "Lagos", "country": "NG"})
    client.post(f"{API}/products/{pid}/prices", headers=free_h,
                json={"price": 800, "currency": "NGN", "store": "Market", "city": "Lagos", "country": "NG"})
    locked = client.get(f"{API}/products/{pid}/prices", headers=free_h).json()
    assert locked["locked"] and locked["reports"] == 2 and len(locked["where_to_buy"]) == 2
    paid = client.get(f"{API}/products/{pid}/prices", headers=h).json()
    assert paid["cheapest"]["store"] == "Market" and paid["cheapest"]["price"] == 800


@respx.mock(assert_all_called=False)
def test_scan_creates_allergen_and_watchlist_alerts(respx_mock, client, db):
    code = ean13("700000000001")
    mock_off_product(respx_mock, code, off_product(code, product_name="Nut Bar",
                                                   ingredients_text="Dates, almonds, palm oil, salt."))
    h, email = new_user(client, db, "plus")
    pid = client.get(f"{API}/profiles", headers=h).json()[0]["id"]
    client.put(f"{API}/profiles/{pid}/allergens", headers=h, json=[{"code": "nuts", "severity": "severe"}])
    client.put(f"{API}/profiles/{pid}/avoid", headers=h, json=["palm oil"])
    client.get(f"{API}/products/barcode/{code}", headers=h)
    client.get(f"{API}/products/barcode/{code}", headers=h)  # second scan doesn't duplicate alerts
    kinds = [n["kind"] for n in client.get(f"{API}/notifications", headers=h).json()]
    assert kinds.count("allergen_alert") == 1 and kinds.count("ingredient_alert") == 1


def test_local_foods_safety_and_articles(client):
    foods = client.get(f"{API}/local-foods?q=egwusi").json()
    assert foods["foods"][0]["slug"] == "egusi-soup" and foods["foods"][0]["recipe_id"]
    assert foods["names_reviewed"] is False
    topics = client.get(f"{API}/safety/topics").json()
    assert "does not mean a particular brand" in topics["risk_explainer"]["product_rule"]
    assert {t["slug"] for t in topics["topics"]} >= {"heavy-metals", "microplastics", "glyphosate", "aflatoxins"}
    art = client.get(f"{API}/articles/hazard-vs-risk").json()
    assert art["body"] and art["sources"]


def test_admin_content_analytics_and_jobs(client, admin_headers):
    r = client.put(f"{API}/admin/articles/new-tip", headers=admin_headers, json={
        "slug": "new-tip", "title": "Tip", "summary": "S", "body": "B", "topic": "nutrition", "status": "published"})
    assert r.status_code == 200 and r.json()["published_at"]
    assert "new-tip" in [a["slug"] for a in client.get(f"{API}/articles").json()]
    a = client.get(f"{API}/admin/analytics", headers=admin_headers).json()
    assert "top_products" in a and "feature_usage" in a
    assert "expiry" in client.post(f"{API}/admin/jobs/daily", headers=admin_headers).json()
    h = register(client)
    assert client.get(f"{API}/admin/analytics", headers=h).status_code == 403


@respx.mock(assert_all_called=False)
def test_assistant_languages_are_paid(respx_mock, client, db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h, email = new_user(client, db)
    assert client.post(f"{API}/assistant/ask", headers=h, json={"question": "Wetin dey inside?",
                                                                "language": "pcm"}).status_code == 402
    upgrade(db, email, "plus")
    gem = respx_mock.post(url__regex=r".*generateContent").respond(200, json={
        "candidates": [{"content": {"parts": [{"text": "E get sugar."}]}}], "usageMetadata": {}})
    r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "Wetin dey inside?", "language": "pcm"})
    assert r.status_code == 200
    assert "Answer in Nigerian Pidgin" in json.loads(gem.calls.last.request.content)["systemInstruction"]["parts"][0][
        "text"]


@respx.mock(assert_all_called=False)
def test_foreign_label_is_analysed_from_its_translation(respx_mock, client, db, monkeypatch):
    import io

    from PIL import Image

    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h, _ = new_user(client, db)
    gemini(respx_mock, {"ingredients_text": "Sucre, huile de palme, noisettes 13%, lait écrémé en poudre",
                        "contains_statement": None, "may_contain_statement": None, "legibility": "good",
                        "language": "fr", "english_translation": {
                            "ingredients_text": "Sugar, palm oil, hazelnuts 13%, skimmed milk powder",
                            "contains_statement": None, "may_contain_statement": None}})
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "JPEG")
    r = client.post(f"{API}/analysis/image", headers=h, data={"task": "ingredients"},
                    files={"image": ("photo.jpg", buf.getvalue(), "image/jpeg")}).json()
    assert r["ingredients_text"].startswith("Sucre") and r["ingredients_text_english"].startswith("Sugar")
    status = {a["code"]: a["status"] for a in r["analysis"]["allergens"]}
    assert status["milk"] == "contains" and status["nuts"] == "contains"


@respx.mock(assert_all_called=False)
def test_gemini_overload_is_retried(respx_mock, client, db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    h, _ = new_user(client, db)
    route = respx_mock.post(url__regex=r".*generateContent")
    route.side_effect = [
        respx.MockResponse(503, json={"error": {"status": "UNAVAILABLE"}}),
        respx.MockResponse(200, json={"candidates": [{"content": {"parts": [{"text": "Hi"}]}}], "usageMetadata": {}}),
    ]
    r = client.post(f"{API}/assistant/ask", headers=h, json={"question": "Hello there"})
    assert r.status_code == 200 and route.call_count == 2


def test_planned_meals_link_to_recipes_by_dish_name(db):
    from app.api.v1.recipes import match_recipe
    from app.models import Recipe

    public = db.query(Recipe).filter(Recipe.is_public.is_(True)).all()
    by_id = {r.id: r.title for r in public}
    assert by_id[match_recipe(public, "Akara and Pap")] == "Akara (bean fritters)"
    assert by_id[match_recipe(public, "Nigerian Jollof Rice with Fried Plantain")] == "Jollof rice"
    assert by_id[match_recipe(public, "Fish pepper soup with yam")] == "Fish pepper soup"
    assert match_recipe(public, "Catfish stew") is None


def test_alternatives_prefer_products_sold_locally(client, db, admin_headers):
    def make(i, sugar, country):
        r = client.post(f"{API}/admin/products", headers=admin_headers, json={
            "barcode": ean13(f"61000000{i:04d}"), "name": f"Biscuit {i}", "category": "Local Biscuits",
            "ingredients_text": "wheat flour, sugar, palm oil", "countries": [country],
            "nutrition": {"energy_kcal": 450, "fat": 18, "saturated_fat": 8, "carbohydrates": 65, "sugars": sugar,
                          "fiber": 2, "protein": 6, "salt": 0.8}})
        return r.json()["id"]

    base = make(1, 40, "nigeria")
    us_better = make(2, 2, "united-states")
    ng_better = make(3, 2, "nigeria")
    h, _ = new_user(client, db)
    alts = client.get(f"{API}/products/{base}/alternatives", headers=h, params={"country": "NG"}).json()
    ids = [a["product"]["id"] for a in alts["alternatives"]]
    assert ids.index(ng_better) < ids.index(us_better)
    assert alts["alternatives"][0]["sold_in_country"] is True and alts["country"] == "NG"
