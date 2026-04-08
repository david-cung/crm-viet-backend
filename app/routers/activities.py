from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.schemas import ActivityCreate, ActivityOut

router = APIRouter(prefix="/activities", tags=["activities"], dependencies=[Depends(get_current_active_user)])


def _fmt_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")


@router.get("", response_model=list[ActivityOut])
def list_activities(
    db: Session = Depends(get_db),
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[ActivityOut]:
    q = db.query(models.Activity).options(joinedload(models.Activity.deal))
    if contact_id:
        q = q.filter(models.Activity.contact_id == contact_id)
    if deal_id:
        q = q.filter(models.Activity.deal_id == deal_id)
    rows = q.order_by(models.Activity.occurred_at.desc()).limit(limit).all()
    return [ActivityOut.from_row(a) for a in rows]


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    body: ActivityCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> ActivityOut:
    contact_name = None
    if body.contact_id:
        c = db.get(models.Contact, body.contact_id)
        if not c:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_id")
        contact_name = c.name
    if body.deal_id:
        d = db.get(models.Deal, body.deal_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid deal_id")
    now = datetime.now(timezone.utc)
    a = models.Activity(
        type=body.type,
        description=body.description,
        contact_id=body.contact_id,
        deal_id=body.deal_id,
        contact_name=contact_name,
        time=_fmt_time(now),
        user=user.full_name or user.email,
        occurred_at=now,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    a = (
        db.query(models.Activity)
        .options(joinedload(models.Activity.deal))
        .filter(models.Activity.id == a.id)
        .first()
    )
    assert a
    return ActivityOut.from_row(a)
