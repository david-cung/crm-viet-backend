from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user, require_admin
from app import models
from app.schemas import CompanyOut, CompanyUpdate, StaffMemberCreate, StaffMemberOut, StaffMemberUpdate

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_active_user)])

_COMPANY_ID = 1


def _get_company_row(db: Session) -> models.CompanySettings:
    row = db.get(models.CompanySettings, _COMPANY_ID)
    if not row:
        row = models.CompanySettings(id=_COMPANY_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/company", response_model=CompanyOut)
def get_company(db: Session = Depends(get_db)) -> CompanyOut:
    return CompanyOut.from_row(_get_company_row(db))


@router.patch("/company", response_model=CompanyOut)
def patch_company(
    body: CompanyUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
) -> CompanyOut:
    row = _get_company_row(db)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return CompanyOut.from_row(row)


@router.get("/staff", response_model=list[StaffMemberOut])
def list_staff(db: Session = Depends(get_db)) -> list[StaffMemberOut]:
    rows = db.query(models.StaffMember).order_by(models.StaffMember.sort_order).all()
    return [StaffMemberOut.from_row(s) for s in rows]


@router.post("/staff", response_model=StaffMemberOut, status_code=status.HTTP_201_CREATED)
def create_staff(body: StaffMemberCreate, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)) -> StaffMemberOut:
    s = models.StaffMember(name=body.name, sort_order=body.sort_order)
    db.add(s)
    db.commit()
    db.refresh(s)
    return StaffMemberOut.from_row(s)


@router.patch("/staff/{staff_id}", response_model=StaffMemberOut)
def update_staff(
    staff_id: UUID,
    body: StaffMemberUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(require_admin),
) -> StaffMemberOut:
    s = db.get(models.StaffMember, staff_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return StaffMemberOut.from_row(s)


@router.delete("/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(staff_id: UUID, db: Session = Depends(get_db), _admin: models.User = Depends(require_admin)) -> None:
    s = db.get(models.StaffMember, staff_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    db.delete(s)
    db.commit()

