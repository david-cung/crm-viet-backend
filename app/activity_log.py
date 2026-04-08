from datetime import datetime, timezone
from uuid import UUID

from app import models


def fmt_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")


def add_activity(
    *,
    db,
    actor: models.User,
    type: str,
    description: str,
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
) -> models.Activity:
    now = datetime.now(timezone.utc)
    contact_name = None
    if contact_id:
        c = db.get(models.Contact, contact_id)
        contact_name = c.name if c else None
    a = models.Activity(
        type=type,
        description=description,
        contact_id=contact_id,
        deal_id=deal_id,
        contact_name=contact_name,
        time=fmt_time(now),
        user=actor.full_name or actor.email,
        occurred_at=now,
    )
    db.add(a)
    return a

