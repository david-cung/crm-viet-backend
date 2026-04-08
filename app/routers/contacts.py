import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.activity_log import add_activity
from app.deps import get_current_active_user
from app import models
from app.schemas import ContactCreate, ContactOut, ContactUpdate, ImportContactsResult, PaginatedContacts

router = APIRouter(
    prefix="/contacts",
    tags=["contacts"],
    dependencies=[Depends(get_current_active_user)],
)


def _contact_filter(db: Session, q: str | None, status_v: str | None, assigned_to: str | None):
    query = db.query(models.Contact)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Contact.name.ilike(like),
                models.Contact.company.ilike(like),
                models.Contact.email.ilike(like),
                models.Contact.phone.ilike(like),
            )
        )
    if status_v:
        query = query.filter(models.Contact.status == status_v)
    if assigned_to:
        query = query.filter(models.Contact.assigned_to == assigned_to)
    return query


@router.get("/export/csv")
def export_contacts_csv(
    db: Session = Depends(get_db),
    q: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
):
    rows = _contact_filter(db, q, status, assigned_to).order_by(models.Contact.created_at.desc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "name",
            "phone",
            "email",
            "company",
            "address",
            "status",
            "source",
            "assignedTo",
            "birthday",
            "zalo",
            "facebook",
            "tags",
        ]
    )
    for c in rows:
        w.writerow(
            [
                c.name,
                c.phone,
                c.email,
                c.company,
                c.address,
                c.status,
                c.source,
                c.assigned_to,
                c.birthday or "",
                c.zalo,
                c.facebook,
                "|".join(list(c.tags or [])),
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="contacts.csv"'},
    )


@router.post("/import/csv", response_model=ImportContactsResult)
async def import_contacts_csv(db: Session = Depends(get_db), file: UploadFile = File(...)) -> ImportContactsResult:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    imported = 0
    skipped = 0
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        name = (row.get("name") or row.get("Name") or "").strip()
        if not name:
            skipped += 1
            continue
        tags_raw = (row.get("tags") or row.get("Tags") or "").strip()
        tags = [t.strip() for t in tags_raw.replace(";", "|").split("|") if t.strip()]
        try:
            c = models.Contact(
                name=name,
                phone=(row.get("phone") or row.get("Phone") or "").strip(),
                email=(row.get("email") or row.get("Email") or "").strip(),
                company=(row.get("company") or row.get("Company") or "").strip(),
                address=(row.get("address") or row.get("Address") or "").strip(),
                birthday=(row.get("birthday") or row.get("Birthday") or "").strip() or None,
                zalo=(row.get("zalo") or row.get("Zalo") or "").strip(),
                facebook=(row.get("facebook") or row.get("Facebook") or "").strip(),
                tags=tags,
                status=(row.get("status") or row.get("Status") or "new").strip() or "new",
                source=(row.get("source") or row.get("Source") or "").strip(),
                assigned_to=(row.get("assignedTo") or row.get("assigned_to") or "").strip(),
            )
            db.add(c)
            imported += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"Dòng {i}: {e}")
    db.commit()
    return ImportContactsResult(imported=imported, skipped=skipped, errors=errors[:50])


@router.get("", response_model=PaginatedContacts)
def list_contacts(
    db: Session = Depends(get_db),
    q: str | None = None,
    status: str | None = None,
    assigned_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> PaginatedContacts:
    base = _contact_filter(db, q, status, assigned_to)
    total = base.count()
    rows = (
        base.order_by(models.Contact.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedContacts(items=[ContactOut.from_row(c) for c in rows], total=total, page=page, page_size=page_size)


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: UUID, db: Session = Depends(get_db)) -> ContactOut:
    c = db.get(models.Contact, contact_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return ContactOut.from_row(c)


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    body: ContactCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> ContactOut:
    c = models.Contact(
        name=body.name,
        phone=body.phone,
        email=body.email,
        company=body.company,
        address=body.address,
        birthday=body.birthday,
        zalo=body.zalo,
        facebook=body.facebook,
        tags=body.tags,
        status=body.status,
        source=body.source,
        assigned_to=body.assigned_to,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    add_activity(db=db, actor=user, type="contact", description=f"Tạo liên hệ: {c.name}", contact_id=c.id)
    db.commit()
    return ContactOut.from_row(c)


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: UUID,
    body: ContactUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> ContactOut:
    c = db.get(models.Contact, contact_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    add_activity(db=db, actor=user, type="contact", description=f"Cập nhật liên hệ: {c.name}", contact_id=c.id)
    db.commit()
    return ContactOut.from_row(c)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> None:
    c = db.get(models.Contact, contact_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    add_activity(db=db, actor=user, type="contact", description=f"Xóa liên hệ: {c.name}", contact_id=c.id)
    db.delete(c)
    db.commit()
