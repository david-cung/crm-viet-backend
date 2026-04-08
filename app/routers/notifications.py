from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.schemas import NotificationItem

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_active_user)])


def _parse_due(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


@router.get("/reminders", response_model=list[NotificationItem])
def task_reminders(
    db: Session = Depends(get_db),
    days_ahead: int = Query(7, ge=1, le=90),
) -> list[NotificationItem]:
    today = date.today()
    end = today + timedelta(days=days_ahead)
    rows = db.query(models.Task).filter(models.Task.status != "done").all()
    out: list[NotificationItem] = []
    for t in rows:
        d = _parse_due(t.due_date)
        if d is None:
            continue
        if d <= end:
            overdue = d < today
            out.append(
                NotificationItem(
                    id=str(t.id),
                    kind="task_due",
                    title=t.title,
                    subtitle=("Quá hạn" if overdue else f"Hạn: {t.due_date}"),
                    due_date=t.due_date,
                    task_id=str(t.id),
                )
            )
    out.sort(key=lambda x: (x.due_date or ""))
    return out

