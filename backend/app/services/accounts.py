from sqlalchemy.orm import Session

from app.models import FamilyProfile, Subscription, User, UserProfile


def ensure_user_defaults(db: Session, user: User) -> None:
    """Every account gets settings, a primary eater profile and a free subscription."""
    if user.settings is None:
        db.add(UserProfile(user_id=user.id))
    if not user.family_profiles:
        db.add(
            FamilyProfile(
                owner_user_id=user.id,
                name=user.display_name or "Me",
                is_primary=True,
                relationship_label="self",
                avatar_color="#0F766E",
            )
        )
    db.flush()
    if not db.query(Subscription).filter_by(user_id=user.id).first():
        db.add(Subscription(user_id=user.id, tier="free", status="active", provider="manual"))
    db.flush()
