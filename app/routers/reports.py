from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app import models

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_active_user)])


class MonthlyRevenueRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    year_month: str = Field(serialization_alias="yearMonth")
    label: str
    revenue: float


class ReportSummaryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    contacts_created: int = Field(serialization_alias="contactsCreated")
    deals_won: int = Field(serialization_alias="dealsWon")
    revenue_won: float = Field(serialization_alias="revenueWon")
    tasks_done: int = Field(serialization_alias="tasksDone")


class TrendRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    period: str
    label: str
    revenue: float
    new_contacts: int = Field(serialization_alias="newContacts")
    won_deals: int = Field(serialization_alias="wonDeals")


def _parse_close_date(d: models.Deal) -> date | None:
    if not d.close_date:
        return None
    raw = d.close_date
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _month_key_from_deal(d: models.Deal) -> str | None:
    if d.close_date:
        raw = d.close_date
        if len(raw) >= 10:
            try:
                datetime.strptime(raw[:10], "%Y-%m-%d")
                return raw[:7]
            except ValueError:
                pass
        if len(raw) >= 7 and raw[4] == "-":
            return raw[:7]
    if d.created_at:
        return d.created_at.strftime("%Y-%m")
    return None


@router.get("/monthly-revenue", response_model=list[MonthlyRevenueRow])
def monthly_revenue(
    db: Session = Depends(get_db),
    months: int = Query(default=12, ge=1, le=36),
) -> list[MonthlyRevenueRow]:
    """Doanh thu deal Thắng theo tháng (VND)."""
    today = date.today()
    start_y, start_m = today.year, today.month
    for _ in range(months - 1):
        start_m -= 1
        if start_m < 1:
            start_m = 12
            start_y -= 1

    keys_ordered: list[tuple[int, int]] = []
    cy, cm = start_y, start_m
    for _ in range(months):
        keys_ordered.append((cy, cm))
        cm += 1
        if cm > 12:
            cm = 1
            cy += 1

    buckets: defaultdict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for d in db.query(models.Deal).filter(models.Deal.stage == "won").all():
        key = _month_key_from_deal(d)
        if key:
            buckets[key] += d.value

    out: list[MonthlyRevenueRow] = []
    for y, mo in keys_ordered:
        ym = f"{y:04d}-{mo:02d}"
        rev = buckets.get(ym, Decimal(0))
        label = f"{mo}/{str(y)[-2:]}"
        out.append(MonthlyRevenueRow(year_month=ym, label=label, revenue=float(rev)))
    return out


@router.get("/summary", response_model=ReportSummaryOut)
def report_summary(
    db: Session = Depends(get_db),
    date_from: date = Query(alias="dateFrom"),
    date_to: date = Query(alias="dateTo"),
) -> ReportSummaryOut:
    contacts_created = (
        db.query(models.Contact)
        .filter(models.Contact.created_at >= date_from, models.Contact.created_at <= date_to)
        .count()
    )
    won_deals = [d for d in db.query(models.Deal).filter(models.Deal.stage == "won").all() if _parse_close_date(d)]
    won_in_range = [d for d in won_deals if date_from <= _parse_close_date(d) <= date_to]
    revenue_won = sum((d.value for d in won_in_range), start=Decimal(0))

    tasks_done = 0
    for t in db.query(models.Task).filter(models.Task.status == "done").all():
        du = None
        if t.due_date:
            try:
                du = date.fromisoformat(t.due_date[:10])
            except ValueError:
                pass
        if du and date_from <= du <= date_to:
            tasks_done += 1

    return ReportSummaryOut(
        contacts_created=contacts_created,
        deals_won=len(won_in_range),
        revenue_won=float(revenue_won),
        tasks_done=tasks_done,
    )


def _month_iter(d0: date, d1: date) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    y, m = d0.year, d0.month
    end_key = (d1.year, d1.month)
    while (y, m) <= end_key:
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


@router.get("/trend", response_model=list[TrendRow])
def report_trend(
    db: Session = Depends(get_db),
    date_from: date = Query(alias="dateFrom"),
    date_to: date = Query(alias="dateTo"),
) -> list[TrendRow]:
    months = _month_iter(date_from.replace(day=1), date_to)
    if not months:
        return []

    rev_by_m: defaultdict[str, Decimal] = defaultdict(lambda: Decimal(0))
    won_by_m: defaultdict[str, int] = defaultdict(int)
    for d in db.query(models.Deal).filter(models.Deal.stage == "won").all():
        cd = _parse_close_date(d)
        if not cd or cd < date_from or cd > date_to:
            continue
        key = f"{cd.year:04d}-{cd.month:02d}"
        rev_by_m[key] += d.value
        won_by_m[key] += 1

    contacts_by_m: defaultdict[str, int] = defaultdict(int)
    for c in db.query(models.Contact).all():
        if c.created_at < date_from or c.created_at > date_to:
            continue
        key = f"{c.created_at.year:04d}-{c.created_at.month:02d}"
        contacts_by_m[key] += 1

    out: list[TrendRow] = []
    for y, mo in months:
        key = f"{y:04d}-{mo:02d}"
        label = f"{mo}/{str(y)[-2:]}"
        out.append(
            TrendRow(
                period=key,
                label=label,
                revenue=float(rev_by_m.get(key, Decimal(0))),
                new_contacts=contacts_by_m.get(key, 0),
                won_deals=won_by_m.get(key, 0),
            )
        )
    return out


@router.get("/daily-revenue", response_model=list[dict])
def daily_revenue(
    db: Session = Depends(get_db),
    date_from: date = Query(alias="dateFrom"),
    date_to: date = Query(alias="dateTo"),
) -> list[dict]:
    buckets: defaultdict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for d in db.query(models.Deal).filter(models.Deal.stage == "won").all():
        cd = _parse_close_date(d)
        if not cd or cd < date_from or cd > date_to:
            continue
        buckets[cd.isoformat()] += d.value

    cur = date_from
    out: list[dict] = []
    while cur <= date_to:
        k = cur.isoformat()
        out.append({"date": k, "label": f"{cur.day}/{cur.month}", "revenue": float(buckets.get(k, Decimal(0)))})
        cur += timedelta(days=1)
    return out

