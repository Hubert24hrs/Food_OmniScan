"""Pantry and expiry tracking, households, grocery budget and shopping history."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select

from app.core.deps import DB, CurrentUser
from app.models import (
    Budget,
    Household,
    HouseholdMember,
    Notification,
    PantryItem,
    Product,
    Purchase,
    ShoppingList,
    User,
)
from app.services import entitlements as ent
from app.services import households as hh

router = APIRouter(tags=["kitchen"])


# ------------------------------------------------------------------ pantry (Plus)


def pantry_out(i: PantryItem) -> dict:
    days_left = (i.expires_on - date.today()).days if i.expires_on else None
    return {
        "id": i.id,
        "name": i.name,
        "product_id": i.product_id,
        "quantity": i.quantity,
        "location": i.location,
        "expires_on": i.expires_on.isoformat() if i.expires_on else None,
        "opened_on": i.opened_on.isoformat() if i.opened_on else None,
        "days_left": days_left,
        "status": None if days_left is None else "expired" if days_left < 0 else "soon" if days_left <= 3 else "ok",
        "shared": i.household_id is not None,
        "used_up": i.used_up_at is not None,
    }


def _pantry_scope(db, user):
    hid = hh.household_id(db, user)
    cond = PantryItem.owner_user_id == user.id
    return or_(cond, PantryItem.household_id == hid) if hid else cond


class PantryIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    product_id: str | None = None
    quantity: str | None = Field(default=None, max_length=40)
    location: str = Field("cupboard", pattern="^(fridge|freezer|cupboard)$")
    expires_on: date | None = None
    opened_on: date | None = None
    shared: bool = True


@router.get("/pantry")
def list_pantry(db: DB, user: CurrentUser, include_used: bool = False):
    ent.require_feature(db, user, "pantry")
    stmt = select(PantryItem).where(_pantry_scope(db, user))
    if not include_used:
        stmt = stmt.where(PantryItem.used_up_at.is_(None))
    rows = db.scalars(stmt).all()
    rows = sorted(rows, key=lambda i: (i.expires_on is None, i.expires_on or date.max, i.name.lower()))
    return [pantry_out(i) for i in rows]


@router.post("/pantry", status_code=201)
def add_pantry(body: PantryIn, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "pantry")
    name = body.name
    if body.product_id:
        p = db.get(Product, body.product_id)
        if not p:
            raise HTTPException(404, "Product not found")
        name = name or " ".join(filter(None, [p.brand_text, p.name])) or "Product"
    if not name:
        raise HTTPException(422, "Provide a name or product_id")
    item = PantryItem(
        owner_user_id=user.id,
        household_id=hh.household_id(db, user) if body.shared else None,
        product_id=body.product_id,
        name=name,
        quantity=body.quantity,
        location=body.location,
        expires_on=body.expires_on,
        opened_on=body.opened_on,
    )
    db.add(item)
    db.commit()
    return pantry_out(item)


class PantryPatch(BaseModel):
    quantity: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, pattern="^(fridge|freezer|cupboard)$")
    expires_on: date | None = None
    opened_on: date | None = None
    used_up: bool | None = None


def _pantry_item(db, user, item_id) -> PantryItem:
    i = db.get(PantryItem, item_id)
    if not i or not hh.can_access(db, user, i.owner_user_id, i.household_id):
        raise HTTPException(404, "Item not found")
    return i


@router.patch("/pantry/{item_id}")
def patch_pantry(item_id: str, body: PantryPatch, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "pantry")
    i = _pantry_item(db, user, item_id)
    data = body.model_dump(exclude_unset=True)
    used = data.pop("used_up", None)
    for k, v in data.items():
        setattr(i, k, v)
    if "expires_on" in data:
        i.reminded_at = None
    if used is not None:
        i.used_up_at = func.now() if used else None
    db.commit()
    db.refresh(i)
    return pantry_out(i)


@router.delete("/pantry/{item_id}", status_code=204)
def delete_pantry(item_id: str, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "pantry")
    db.delete(_pantry_item(db, user, item_id))
    db.commit()


@router.get("/pantry/expiring")
def expiring(db: DB, user: CurrentUser, days: int = Query(3, ge=0, le=30)):
    ent.require_feature(db, user, "pantry")
    rows = db.scalars(
        select(PantryItem).where(
            _pantry_scope(db, user),
            PantryItem.used_up_at.is_(None),
            PantryItem.expires_on.is_not(None),
            PantryItem.expires_on <= date.today() + timedelta(days=days),
        )
    ).all()
    return [pantry_out(i) for i in sorted(rows, key=lambda i: i.expires_on)]


# ------------------------------------------------------------------ household (Family plan to create/invite)


@router.get("/household")
def my_household(db: DB, user: CurrentUser):
    h = hh.household_of(db, user)
    invites = db.scalars(
        select(HouseholdMember).where(
            func.lower(HouseholdMember.invited_email) == user.email.lower(), HouseholdMember.status == "invited"
        )
    ).all()
    return {
        "household": hh.household_out(db, h) if h else None,
        "invites": [{"id": m.id, "household": db.get(Household, m.household_id).name} for m in invites],
        "can_create": ent.has_feature(db, user, "household"),
    }


class HouseholdIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@router.post("/household", status_code=201)
def create_household(body: HouseholdIn, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "household")
    if hh.household_of(db, user):
        raise HTTPException(409, "You're already in a household")
    h = Household(name=body.name, owner_user_id=user.id)
    db.add(h)
    db.flush()
    db.add(HouseholdMember(household_id=h.id, user_id=user.id, invited_email=user.email, role="owner", status="active"))
    db.commit()
    db.refresh(h)
    return hh.household_out(db, h)


class InviteIn(BaseModel):
    email: EmailStr


MAX_MEMBERS = 8


@router.post("/household/invite", status_code=201)
def invite(body: InviteIn, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "household")
    h = hh.household_of(db, user)
    if not h or h.owner_user_id != user.id:
        raise HTTPException(403, "Only the household owner can invite people")
    if len(h.members) >= MAX_MEMBERS:
        raise HTTPException(409, f"A household can have up to {MAX_MEMBERS} members")
    email = body.email.lower()
    if any(m.invited_email.lower() == email for m in h.members):
        raise HTTPException(409, "Already invited")
    db.add(HouseholdMember(household_id=h.id, invited_email=email, role="member", status="invited"))
    invitee = db.scalar(select(User).where(func.lower(User.email) == email))
    if invitee:
        db.add(
            Notification(
                user_id=invitee.id,
                kind="household",
                title=f"{user.display_name or 'Someone'} invited you to a household",
                body=f"Join '{h.name}' to share a pantry, shopping lists and a grocery budget.",
                data={"household_id": h.id},
            )
        )
    db.commit()
    db.refresh(h)
    return hh.household_out(db, h)


@router.post("/household/invites/{member_id}/accept")
def accept_invite(member_id: str, db: DB, user: CurrentUser):
    m = db.get(HouseholdMember, member_id)
    if not m or m.status != "invited" or m.invited_email.lower() != user.email.lower():
        raise HTTPException(404, "Invite not found")
    if hh.household_of(db, user):
        raise HTTPException(409, "Leave your current household first")
    m.user_id, m.status = user.id, "active"
    db.commit()
    return hh.household_out(db, db.get(Household, m.household_id))


@router.delete("/household/members/{member_id}", status_code=204)
def remove_member(member_id: str, db: DB, user: CurrentUser):
    m = db.get(HouseholdMember, member_id)
    h = db.get(Household, m.household_id) if m else None
    if not m or not h:
        raise HTTPException(404, "Member not found")
    is_self = m.user_id == user.id
    if not is_self and h.owner_user_id != user.id:
        raise HTTPException(403, "Only the owner can remove other members")
    if m.role == "owner":
        # Owner leaving dissolves the household; shared items go back to their creators.
        for model in (PantryItem, Purchase, ShoppingList):
            for row in db.scalars(select(model).where(model.household_id == h.id)).all():
                row.household_id = None
        for b in db.scalars(select(Budget).where(Budget.household_id == h.id)).all():
            db.delete(b)
        db.delete(h)
    else:
        db.delete(m)
    db.commit()


# ------------------------------------------------------------------ budget & shopping history (Plus)


def _budget_row(db, user) -> Budget | None:
    hid = hh.household_id(db, user)
    if hid:
        return db.scalar(select(Budget).where(Budget.household_id == hid))
    return db.scalar(select(Budget).where(Budget.user_id == user.id))


class BudgetIn(BaseModel):
    monthly_amount: float = Field(gt=0, le=10_000_000)
    currency: str = Field(pattern="^[A-Z]{3}$")


@router.put("/budget")
def set_budget(body: BudgetIn, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "budget")
    row = _budget_row(db, user)
    if row is None:
        hid = hh.household_id(db, user)
        row = Budget(
            user_id=None if hid else user.id,
            household_id=hid,
            monthly_amount=body.monthly_amount,
            currency=body.currency,
        )
        db.add(row)
    else:
        row.monthly_amount, row.currency = body.monthly_amount, body.currency
    db.commit()
    return {"monthly_amount": row.monthly_amount, "currency": row.currency, "shared": row.household_id is not None}


class PurchaseIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    product_id: str | None = None
    quantity: str | None = Field(default=None, max_length=40)
    price: float = Field(ge=0, le=10_000_000)
    currency: str = Field(pattern="^[A-Z]{3}$")
    store: str | None = Field(default=None, max_length=120)
    purchased_on: date | None = None
    add_to_pantry: bool = False
    expires_on: date | None = None


def purchase_out(p: Purchase) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "product_id": p.product_id,
        "quantity": p.quantity,
        "price": p.price,
        "currency": p.currency,
        "store": p.store,
        "purchased_on": p.purchased_on.isoformat(),
    }


@router.post("/purchases", status_code=201)
def add_purchase(body: PurchaseIn, db: DB, user: CurrentUser):
    ent.require_feature(db, user, "budget")
    name = body.name
    if body.product_id:
        prod = db.get(Product, body.product_id)
        if not prod:
            raise HTTPException(404, "Product not found")
        name = name or " ".join(filter(None, [prod.brand_text, prod.name])) or "Product"
    if not name:
        raise HTTPException(422, "Provide a name or product_id")
    hid = hh.household_id(db, user)
    p = Purchase(
        user_id=user.id,
        household_id=hid,
        product_id=body.product_id,
        name=name,
        quantity=body.quantity,
        price=body.price,
        currency=body.currency,
        store=body.store,
        purchased_on=body.purchased_on or date.today(),
    )
    db.add(p)
    if body.add_to_pantry and ent.has_feature(db, user, "pantry"):
        db.add(
            PantryItem(
                owner_user_id=user.id,
                household_id=hid,
                product_id=body.product_id,
                name=name,
                quantity=body.quantity,
                expires_on=body.expires_on,
            )
        )
    db.commit()
    return purchase_out(p)


def _purchase_scope(db, user):
    hid = hh.household_id(db, user)
    cond = Purchase.user_id == user.id
    return or_(cond, Purchase.household_id == hid) if hid else cond


@router.get("/purchases")
def purchases(db: DB, user: CurrentUser, limit: int = Query(50, ge=1, le=200)):
    ent.require_feature(db, user, "budget")
    rows = db.scalars(
        select(Purchase).where(_purchase_scope(db, user)).order_by(Purchase.purchased_on.desc()).limit(limit)
    ).all()
    return [purchase_out(p) for p in rows]


@router.delete("/purchases/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: str, db: DB, user: CurrentUser):
    p = db.get(Purchase, purchase_id)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(p)
    db.commit()


@router.get("/budget")
def budget_summary(db: DB, user: CurrentUser, month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$")):
    ent.require_feature(db, user, "budget")
    today = date.today()
    y, m = (int(month[:4]), int(month[5:])) if month else (today.year, today.month)
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1)
    rows = db.scalars(
        select(Purchase).where(_purchase_scope(db, user), Purchase.purchased_on >= start, Purchase.purchased_on < end)
    ).all()
    b = _budget_row(db, user)
    currency = b.currency if b else (user.currency or "USD")
    spent: dict[str, float] = {}
    by_store: dict[str, float] = {}
    for p in rows:
        spent[p.currency] = spent.get(p.currency, 0) + p.price
        if p.currency == currency:
            by_store[p.store or "Other"] = by_store.get(p.store or "Other", 0) + p.price
    total = round(spent.get(currency, 0), 2)
    return {
        "month": start.strftime("%Y-%m"),
        "currency": currency,
        "budget": b.monthly_amount if b else None,
        "spent": total,
        "remaining": round(b.monthly_amount - total, 2) if b else None,
        "other_currencies": {c: round(v, 2) for c, v in spent.items() if c != currency},
        "by_store": {k: round(v, 2) for k, v in sorted(by_store.items(), key=lambda kv: -kv[1])},
        "purchases": len(rows),
        "shared": bool(b and b.household_id),
    }
