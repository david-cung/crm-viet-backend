from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, nulls_last, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.activity_log import add_activity
from app.deps import get_current_active_user
from app import models
from app.schemas import PaginatedTasks, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_active_user)])


def _load_task(db: Session, task_id: UUID) -> models.Task | None:
    return (
        db.query(models.Task)
        .options(
            joinedload(models.Task.linked_contact),
            joinedload(models.Task.linked_deal),
        )
        .filter(models.Task.id == task_id)
        .first()
    )


def _task_filter(db: Session, q: str | None, status_v: str | None, priority: str | None, assigned_to: str | None):
    query = db.query(models.Task).options(
        joinedload(models.Task.linked_contact),
        joinedload(models.Task.linked_deal),
    )
    if q:
        like = f"%{q}%"
        query = (
            query.outerjoin(models.Contact, models.Task.linked_contact_id == models.Contact.id)
            .outerjoin(models.Deal, models.Task.linked_deal_id == models.Deal.id)
            .filter(or_(models.Task.title.ilike(like), models.Contact.name.ilike(like), models.Deal.title.ilike(like)))
            .distinct()
        )
    if status_v:
        query = query.filter(models.Task.status == status_v)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if assigned_to:
        query = query.filter(models.Task.assigned_to == assigned_to)
    return query


@router.get("", response_model=PaginatedTasks)
def list_tasks(
    db: Session = Depends(get_db),
    q: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> PaginatedTasks:
    base = _task_filter(db, q, status, priority, assigned_to)
    total = base.count()
    rows = (
        base.order_by(nulls_last(desc(models.Task.due_date)))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedTasks(items=[TaskOut.from_row(t) for t in rows], total=total, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: UUID, db: Session = Depends(get_db)) -> TaskOut:
    t = _load_task(db, task_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskOut.from_row(t)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> TaskOut:
    if body.linked_contact_id:
        if not db.get(models.Contact, body.linked_contact_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_contact_id")
    if body.linked_deal_id:
        if not db.get(models.Deal, body.linked_deal_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_deal_id")
    t = models.Task(
        title=body.title,
        status=body.status,
        priority=body.priority,
        assigned_to=body.assigned_to,
        due_date=body.due_date,
        linked_contact_id=body.linked_contact_id,
        linked_deal_id=body.linked_deal_id,
    )
    db.add(t)
    db.commit()
    t = _load_task(db, t.id)
    assert t
    add_activity(
        db=db,
        actor=user,
        type="task",
        description=f'Tạo task: "{t.title}"',
        contact_id=t.linked_contact_id,
        deal_id=t.linked_deal_id,
    )
    db.commit()
    return TaskOut.from_row(t)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: UUID,
    body: TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> TaskOut:
    t = _load_task(db, task_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    old_status = t.status
    data = body.model_dump(exclude_unset=True)
    if data.get("linked_contact_id") is not None and data["linked_contact_id"] is not None:
        if not db.get(models.Contact, data["linked_contact_id"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_contact_id")
    if data.get("linked_deal_id") is not None and data["linked_deal_id"] is not None:
        if not db.get(models.Deal, data["linked_deal_id"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_deal_id")
    for k, v in data.items():
        setattr(t, k, v)
    db.commit()
    t = _load_task(db, task_id)
    assert t
    if old_status != t.status:
        add_activity(
            db=db,
            actor=user,
            type="task",
            description=f'Đổi trạng thái task "{t.title}": {old_status} → {t.status}',
            contact_id=t.linked_contact_id,
            deal_id=t.linked_deal_id,
        )
    else:
        add_activity(
            db=db,
            actor=user,
            type="task",
            description=f'Cập nhật task: "{t.title}"',
            contact_id=t.linked_contact_id,
            deal_id=t.linked_deal_id,
        )
    db.commit()
    return TaskOut.from_row(t)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> None:
    t = db.get(models.Task, task_id)
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    add_activity(
        db=db,
        actor=user,
        type="task",
        description=f'Xóa task: "{t.title}"',
        contact_id=t.linked_contact_id,
        deal_id=t.linked_deal_id,
    )
    db.delete(t)
    db.commit()
