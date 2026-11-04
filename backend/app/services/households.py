"""Household membership: who can see a shared pantry, shopping list or budget.

Creating a household and inviting people needs the Family plan. Members who accept an invite
can use the shared items on any plan.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Household, HouseholdMember, User


def household_of(db: Session, user: User) -> Household | None:
    m = db.scalar(select(HouseholdMember).where(HouseholdMember.user_id == user.id, HouseholdMember.status == "active"))
    return db.get(Household, m.household_id) if m else None


def household_id(db: Session, user: User) -> str | None:
    h = household_of(db, user)
    return h.id if h else None


def can_access(db: Session, user: User, owner_user_id: str, item_household_id: str | None) -> bool:
    if owner_user_id == user.id:
        return True
    return item_household_id is not None and item_household_id == household_id(db, user)


def member_out(m: HouseholdMember, db: Session) -> dict:
    u = db.get(User, m.user_id) if m.user_id else None
    return {
        "id": m.id,
        "email": m.invited_email,
        "name": u.display_name if u else None,
        "role": m.role,
        "status": m.status,
    }


def household_out(db: Session, h: Household) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "owner_user_id": h.owner_user_id,
        "members": [member_out(m, db) for m in h.members],
    }
