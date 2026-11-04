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
