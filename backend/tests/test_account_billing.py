"""Account deletion removes everything personal; plan errors tell the apps which plan to offer."""

from datetime import date, timedelta

from sqlalchemy import select

from app.models import FamilyProfile, PantryItem, Purchase, ShoppingList, User
from app.models.lifestyle import Household, HouseholdMember, WaterLog
from app.services import entitlements as ent
from tests.test_lifestyle import API, new_user


def test_deleting_an_account_removes_all_personal_data(client, db):
    owner_h, owner_email = new_user(client, db, "family")
    member_h, member_email = new_user(client, db)

    assert (
        client.post(
            f"{API}/pantry",
            headers=owner_h,
            json={"name": "Milk", "expires_on": (date.today() + timedelta(days=3)).isoformat()},
        ).status_code
        == 201
    )
    assert client.post(f"{API}/shopping-lists", headers=owner_h, json={"name": "Weekly"}).status_code == 201
    assert client.post(f"{API}/diary/water", headers=owner_h, json={"ml": 500}).status_code == 201
    assert (
        client.post(
            f"{API}/diary/entries",
            headers=owner_h,
            json={"meal_type": "lunch", "description": "Jollof", "energy_kcal": 450},
        ).status_code
        == 201
    )
    assert (
        client.put(f"{API}/budget", headers=owner_h, json={"monthly_amount": 50000, "currency": "NGN"}).status_code
        == 200
    )
    assert (
        client.post(
            f"{API}/purchases", headers=owner_h, json={"name": "Rice", "price": 9000, "currency": "NGN"}
        ).status_code
        == 201
    )
    recipe = {"title": "Akara", "ingredients": [{"name": "beans"}, {"name": "onion"}], "steps": ["Blend", "Fry"]}
    assert client.post(f"{API}/recipes", headers=owner_h, json=recipe).status_code == 201
    assert client.post(f"{API}/meal-plans", headers=owner_h, json={"name": "Week 1"}).status_code == 201
    assert client.post(f"{API}/household", headers=owner_h, json={"name": "Home"}).status_code == 201
    client.post(f"{API}/household/invite", headers=owner_h, json={"email": member_email})
    invite = client.get(f"{API}/household", headers=member_h).json()["invites"][0]
    assert client.post(f"{API}/household/invites/{invite['id']}/accept", headers=member_h).status_code == 200

    uid = db.scalar(select(User.id).where(User.email == owner_email))
    assert client.request("DELETE", f"{API}/me", headers=owner_h, json={"confirm": "nope"}).status_code == 422
    assert client.request("DELETE", f"{API}/me", headers=owner_h, json={"confirm": "DELETE"}).status_code == 204

    db.expire_all()
    assert db.get(User, uid) is None
    for model, col in [
        (PantryItem, PantryItem.owner_user_id),
        (ShoppingList, ShoppingList.owner_user_id),
        (Purchase, Purchase.user_id),
        (WaterLog, WaterLog.user_id),
        (FamilyProfile, FamilyProfile.owner_user_id),
        (Household, Household.owner_user_id),
    ]:
        assert db.scalars(select(model).where(col == uid)).all() == [], model.__name__
    # The other household member keeps their account, and is no longer in a household.
    assert db.scalars(select(HouseholdMember).where(HouseholdMember.invited_email == member_email)).all() == []
    assert client.get(f"{API}/me", headers=member_h).status_code == 200
    assert client.get(f"{API}/household", headers=member_h).json()["household"] is None
    # The deleted account's session no longer works and the email can sign up again.
    assert client.get(f"{API}/me", headers=owner_h).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": owner_email, "password": "Sup3rSecret"}).status_code == 401


def test_next_plan_is_the_cheapest_with_a_bigger_allowance(db):
    assert ent.next_tier(db, "free", "ai_assistant") == "plus"
    assert ent.next_tier(db, "plus", "ai_assistant") == "premium"
    assert ent.next_tier(db, "family", "ai_assistant") is None
    assert ent.next_tier(db, "plus", "comparisons") is None  # Plus is already unlimited


def test_free_assistant_allowance_runs_out_with_an_upgrade_hint(respx_mock, client, db, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    respx_mock.post(url__regex=r".*generateContent").respond(
        200, json={"candidates": [{"content": {"parts": [{"text": "High in saturated fat."}]}}], "usageMetadata": {}}
    )
    h, email = new_user(client, db)
    first = client.post(f"{API}/assistant/ask", headers=h, json={"question": "Is palm oil healthy?"})
    assert first.status_code == 200, first.text
    # Use up the rest of the free allowance.
    user = db.scalar(select(User).where(User.email == email))
    limit = ent.limit_for(db, "free", "ai_assistant")
    for _ in range(limit - 1):
        ent.record_usage(db, user, "ai_assistant", "gemini", None)
    second = client.post(f"{API}/assistant/ask", headers=h, json={"question": "And butter?"})
    assert second.status_code == 402
    d = second.json()["detail"]
    assert d["code"] == "quota_exceeded" and d["required_tier"] == "plus"
    assert "AI nutrition assistant questions" in d["message"] and "Plus gives you more" in d["message"]
    usage = client.get(f"{API}/billing/me", headers=h).json()["features"]["ai_assistant"]
    assert usage["used"] == limit and usage["limit"] == limit


def test_hosting_provider_database_urls_use_the_psycopg_driver():
    from app.core.config import Settings

    for raw in ("postgres://u:p@db.example:5432/app", "postgresql://u:p@db.example:5432/app"):
        assert Settings(database_url=raw).database_url == "postgresql+psycopg://u:p@db.example:5432/app"
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


def test_reviews_can_be_reported_blocked_and_moderated(client, db, admin_headers):
    from tests.test_lifestyle import ean13

    p = client.post(
        f"{API}/admin/products",
        headers=admin_headers,
        json={"barcode": ean13("600000009001"), "name": "Review Biscuit", "ingredients_text": "wheat flour, sugar"},
    ).json()
    pid = p.get("id") or p["product"]["id"]
    author_h, _ = new_user(client, db)
    assert (
        client.put(
            f"{API}/products/{pid}/reviews", headers=author_h, json={"rating": 1, "body": "spam spam"}
        ).status_code
        == 200
    )
    review = client.get(f"{API}/products/{pid}/reviews", headers=author_h).json()["reviews"][0]
    assert review["mine"] is True
    rid = review["id"]
    # Authors can't report or block themselves.
    assert client.post(f"{API}/reviews/{rid}/report", headers=author_h, json={"reason": "spam"}).status_code == 400
    assert client.post(f"{API}/reviews/{rid}/block-author", headers=author_h).status_code == 400

    # Reporting hides it for the reporter; blocking hides everything by that author.
    readers = [new_user(client, db)[0] for _ in range(3)]
    r = client.post(f"{API}/reviews/{rid}/report", headers=readers[0], json={"reason": "spam", "note": "ads"})
    assert r.status_code == 201 and r.json()["hidden_for_everyone"] is False
    assert client.get(f"{API}/products/{pid}/reviews", headers=readers[0]).json()["reviews"] == []
    assert len(client.get(f"{API}/products/{pid}/reviews").json()["reviews"]) == 1
    assert client.post(f"{API}/reviews/{rid}/block-author", headers=readers[1]).status_code == 201
    assert client.get(f"{API}/products/{pid}/reviews", headers=readers[1]).json()["reviews"] == []
    block = client.get(f"{API}/me/blocks", headers=readers[1]).json()
    assert len(block) == 1 and set(block[0]) == {"id", "created_at"}  # the blocked person isn't revealed
    assert client.delete(f"{API}/me/blocks/{block[0]['id']}", headers=readers[2]).status_code == 404
    assert client.delete(f"{API}/me/blocks/{block[0]['id']}", headers=readers[1]).status_code == 204
    assert len(client.get(f"{API}/products/{pid}/reviews", headers=readers[1]).json()["reviews"]) == 1

    # Three distinct reports hide it for everyone until a moderator decides.
    client.post(f"{API}/reviews/{rid}/report", headers=readers[1], json={"reason": "offensive"})
    r = client.post(f"{API}/reviews/{rid}/report", headers=readers[2], json={"reason": "spam"})
    assert r.json()["hidden_for_everyone"] is True
    assert client.get(f"{API}/products/{pid}/reviews").json()["reviews"] == []
    assert client.get(f"{API}/admin/reviews/reported", headers=readers[0]).status_code == 403
    queue = client.get(f"{API}/admin/reviews/reported", headers=admin_headers).json()
    item = next(q for q in queue if q["id"] == rid)
    assert item["reports"] == 3 and item["status"] == "hidden" and item["reasons"] == ["offensive", "spam"]
    assert (
        client.post(f"{API}/admin/reviews/{rid}/moderate", headers=admin_headers, json={"action": "publish"}).json()[
            "status"
        ]
        == "published"
    )
    assert all(q["id"] != rid for q in client.get(f"{API}/admin/reviews/reported", headers=admin_headers).json())
    assert len(client.get(f"{API}/products/{pid}/reviews").json()["reviews"]) == 1
