"""Notifications that come from what users scan, and scheduled jobs (expiry, weekly reports, tips).

Allergen and recall alerts are free. Watchlist (avoid-list) ingredient alerts need Plus.
Run the scheduled jobs daily: `python -m app.services.alerts` (or POST /admin/jobs/daily).
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, FamilyProfile, Notification, PantryItem, Product, User
from app.services import entitlements as ent
from app.services import tracking


def _recent(db: Session, user_id: str, kind: str, key: str, hours: int = 24) -> bool:
    since = datetime.now(UTC) - timedelta(hours=hours)
    rows = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id, Notification.kind == kind, Notification.created_at >= since
        )
    ).all()
    return any((n.data or {}).get("key") == key for n in rows)


def _prefs(user: User) -> dict:
    return (user.settings.notification_prefs if user.settings else None) or {}


def scan_alerts(db: Session, user: User | None, product: Product, analysis: dict) -> int:
    """Create allergen / watchlist notifications for a scan. Returns how many were created."""
    if user is None:
        return 0
    prefs = _prefs(user)
    allergen_on = prefs.get("allergen_alerts", True)
    watchlist = prefs.get("ingredient_alerts", True) and ent.has_feature(db, user, "ingredient_alerts")
    n = 0
    for c in analysis.get("compatibility", []):
        for a in c.get("critical_allergen_alerts", []) if allergen_on else []:
            key = f"{product.id}:{c.get('profile_id')}:{a['allergen']}"
            if not _recent(db, user.id, "allergen_alert", key):
                db.add(
                    Notification(
                        user_id=user.id,
                        kind="allergen_alert",
                        title=f"Allergen alert for {c.get('profile_name')}: {product.name or 'scanned product'}",
                        body=a["message"],
                        data={"key": key, "product_id": product.id},
                    )
                )
                n += 1
        if not watchlist:
            continue
        for r in c.get("reasons", []):
            if r["rule"].startswith("avoid.") and r["severity"] == "red":
                key = f"{product.id}:{c.get('profile_id')}:{r['rule']}"
                if not _recent(db, user.id, "ingredient_alert", key):
                    db.add(
                        Notification(
                            user_id=user.id,
                            kind="ingredient_alert",
                            title=f"Watchlist ingredient in {product.name or 'a scanned product'}",
                            body=f"{c.get('profile_name')}: {r['message']}",
                            data={"key": key, "product_id": product.id},
                        )
                    )
                    n += 1
    if n:
        db.commit()
    return n


def expiry_reminders(db: Session, days: int = 3) -> int:
    """One reminder per pantry item expiring within `days` (Plus users only)."""
    rows = db.scalars(
        select(PantryItem).where(
            PantryItem.used_up_at.is_(None),
            PantryItem.reminded_at.is_(None),
            PantryItem.expires_on.is_not(None),
            PantryItem.expires_on <= date.today() + timedelta(days=days),
        )
    ).all()
    n = 0
    for i in rows:
        owner = db.get(User, i.owner_user_id)
        if not owner or not ent.has_feature(db, owner, "pantry") or _prefs(owner).get("expiry") is False:
            continue
        left = (i.expires_on - date.today()).days
        when = "has expired" if left < 0 else "expires today" if left == 0 else f"expires in {left} day(s)"
        db.add(
            Notification(
                user_id=owner.id,
                kind="expiry",
                title=f"{i.name} {when}",
                body="Use it soon, freeze it if suitable, or mark it as used up.",
                data={"pantry_item_id": i.id},
            )
        )
        i.reminded_at = datetime.now(UTC)
        n += 1
    db.commit()
    return n


def weekly_reports(db: Session, today: date | None = None) -> int:
    """Monday summary of last week's diary for Plus users who logged at least one day."""
    today = today or date.today()
    start, end = today - timedelta(days=7), today - timedelta(days=1)
    n = 0
    for u in db.scalars(select(User).where(User.is_active.is_(True))).all():
        if not ent.has_feature(db, u, "nutrition_reports"):
            continue
        if _prefs(u).get("weekly_report") is False:
            continue
        for fp in db.scalars(select(FamilyProfile).where(FamilyProfile.owner_user_id == u.id)).all():
            rep = tracking.period_report(db, fp.id, start, end, fp.goals)
            if not rep["days_logged"] or _recent(db, u.id, "weekly_report", f"{fp.id}:{start}", hours=24 * 6):
                continue
            avg = rep["averages"] or {}
            db.add(
                Notification(
                    user_id=u.id,
                    kind="weekly_report",
                    title=f"{fp.name}'s week: {rep['days_logged']} day(s) logged",
                    body=f"Average {round(avg.get('energy_kcal', 0))} kcal, {round(avg.get('protein', 0))} g protein, "
                    f"{round(avg.get('fiber', 0))} g fiber a day. Open the diary for the full report.",
                    data={"key": f"{fp.id}:{start}", "profile_id": fp.id, "start": start.isoformat()},
                )
            )
            n += 1
    db.commit()
    return n


def weekly_tip(db: Session, today: date | None = None) -> int:
    """One educational article a week to users who opted in to tips."""
    today = today or date.today()
    arts = db.scalars(select(Article).where(Article.status == "published").order_by(Article.slug)).all()
    if not arts:
        return 0
    a = arts[today.isocalendar()[1] % len(arts)]
    n = 0
    for u in db.scalars(select(User).where(User.is_active.is_(True))).all():
        if not _prefs(u).get("tips"):
            continue
        if _recent(db, u.id, "tip", a.slug, hours=24 * 6):
            continue
        db.add(
            Notification(
                user_id=u.id, kind="tip", title=a.title, body=a.summary, data={"key": a.slug, "article": a.slug}
            )
        )
        n += 1
    db.commit()
    return n


def run_daily(db: Session, today: date | None = None) -> dict:
    today = today or date.today()
    out = {"expiry": expiry_reminders(db)}
    if today.weekday() == 0:  # Monday
        out["weekly_reports"] = weekly_reports(db, today)
        out["tips"] = weekly_tip(db, today)
    return out


if __name__ == "__main__":
    import app.models  # noqa: F401
    from app.db.session import SessionLocal

    with SessionLocal() as s:
        print(run_daily(s))
