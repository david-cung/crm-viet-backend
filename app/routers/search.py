from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.schemas import SearchHit, SearchOut

router = APIRouter(prefix="/search", tags=["search"], dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=SearchOut)
def global_search(
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> SearchOut:
    like = f"%{q}%"
    contacts = (
        db.query(models.Contact)
        .filter(
            or_(
                models.Contact.name.ilike(like),
                models.Contact.email.ilike(like),
                models.Contact.phone.ilike(like),
                models.Contact.company.ilike(like),
            )
        )
        .limit(limit)
        .all()
    )
    deals = (
        db.query(models.Deal)
        .options(joinedload(models.Deal.contact))
        .join(models.Contact, models.Deal.contact_id == models.Contact.id)
        .filter(or_(models.Deal.title.ilike(like), models.Contact.name.ilike(like)))
        .limit(limit)
        .all()
    )
    tasks = db.query(models.Task).filter(models.Task.title.ilike(like)).limit(limit).all()
    return SearchOut(
        contacts=[
            SearchHit(
                id=str(c.id),
                kind="contact",
                title=c.name,
                subtitle=c.company or c.email or c.phone,
            )
            for c in contacts
        ],
        deals=[
            SearchHit(
                id=str(d.id),
                kind="deal",
                title=d.title,
                subtitle=d.contact.name if d.contact else "",
            )
            for d in deals
        ],
        tasks=[
            SearchHit(
                id=str(t.id),
                kind="task",
                title=t.title,
                subtitle=t.assigned_to,
            )
            for t in tasks
        ],
    )

