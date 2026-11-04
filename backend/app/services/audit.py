from sqlalchemy.orm import Session

from app.models import AdminAuditLog, User


def audit(
    db: Session,
    actor: User,
    action: str,
    entity: str,
    entity_id: str | None,
    *,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
    note: str | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            actor_id=actor.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before=before,
            after=after,
            ip=ip,
            note=note,
        )
    )


def snapshot(obj, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        v = getattr(obj, f, None)
        out[f] = v.isoformat() if hasattr(v, "isoformat") else v
    return out
