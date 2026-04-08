from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.activity_log import add_activity
from app.deps import get_current_active_user
from app import models
from app.schemas import DealCreate, DealOut, DealStagePatch, DealUpdate, PaginatedDeals

router = APIRouter(prefix="/deals", tags=["deals"], dependencies=[Depends(get_current_active_user)])


def _load_deal(db: Session, deal_id: UUID) -> models.Deal | None:
    return (
        db.query(models.Deal)
        .options(joinedload(models.Deal.contact))
        .filter(models.Deal.id == deal_id)
        .first()
    )


def _deal_list_query(db: Session, q: str | None, stage: str | None, assigned_to: str | None):
    query = db.query(models.Deal).options(joinedload(models.Deal.contact))
    if q:
        like = f"%{q}%"
        query = (
            query.join(models.Contact, models.Deal.contact_id == models.Contact.id).filter(
                or_(models.Deal.title.ilike(like), models.Contact.name.ilike(like))
            )
        )
    if stage:
        query = query.filter(models.Deal.stage == stage)
    if assigned_to:
        query = query.filter(models.Deal.assigned_to == assigned_to)
    return query


@router.get("", response_model=PaginatedDeals)
def list_deals(
    db: Session = Depends(get_db),
    q: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> PaginatedDeals:
    base = _deal_list_query(db, q, stage, assigned_to)
    total = base.count()
    rows = (
        base.order_by(models.Deal.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedDeals(items=[DealOut.from_row(d) for d in rows], total=total, page=page, page_size=page_size)


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: UUID, db: Session = Depends(get_db)) -> DealOut:
    d = _load_deal(db, deal_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return DealOut.from_row(d)


@router.post("", response_model=DealOut, status_code=status.HTTP_201_CREATED)
def create_deal(
    body: DealCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> DealOut:
    contact = db.get(models.Contact, body.contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_id")
    d = models.Deal(
        title=body.title,
        value=body.value,
        contact_id=body.contact_id,
        assigned_to=body.assigned_to,
        stage=body.stage,
        probability=body.probability,
        close_date=body.close_date,
        notes=body.notes,
    )
    db.add(d)
    db.commit()
    d = _load_deal(db, d.id)
    assert d
    add_activity(
        db=db,
        actor=user,
        type="deal",
        description=f'Tạo deal: "{d.title}"',
        contact_id=d.contact_id,
        deal_id=d.id,
    )
    db.commit()
    return DealOut.from_row(d)


@router.patch("/{deal_id}", response_model=DealOut)
def update_deal(
    deal_id: UUID,
    body: DealUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> DealOut:
    d = _load_deal(db, deal_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    data = body.model_dump(exclude_unset=True)
    if "contact_id" in data and data["contact_id"] is not None:
        contact = db.get(models.Contact, data["contact_id"])
        if not contact:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_id")
    for k, v in data.items():
        setattr(d, k, v)
    db.commit()
    d = _load_deal(db, deal_id)
    assert d
    add_activity(
        db=db,
        actor=user,
        type="deal",
        description=f'Cập nhật deal: "{d.title}"',
        contact_id=d.contact_id,
        deal_id=d.id,
    )
    db.commit()
    return DealOut.from_row(d)


@router.patch("/{deal_id}/stage", response_model=DealOut)
def patch_deal_stage(
    deal_id: UUID,
    body: DealStagePatch,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> DealOut:
    d = _load_deal(db, deal_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    old = d.stage
    d.stage = body.stage
    if body.stage == "won":
        d.probability = 100
    elif body.stage == "lost":
        d.probability = 0
    db.commit()
    d = _load_deal(db, deal_id)
    assert d
    if old != d.stage:
        add_activity(
            db=db,
            actor=user,
            type="deal",
            description=f'Đổi stage deal "{d.title}": {old} → {d.stage}',
            contact_id=d.contact_id,
            deal_id=d.id,
        )
        db.commit()
    return DealOut.from_row(d)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> None:
    d = db.get(models.Deal, deal_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    add_activity(
        db=db,
        actor=user,
        type="deal",
        description=f'Xóa deal: "{d.title}"',
        contact_id=d.contact_id,
        deal_id=d.id,
    )
    db.delete(d)
    db.commit()
