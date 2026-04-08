from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import require_admin
from app.schemas import UserCreate, UserPublic, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db)) -> list[UserPublic]:
    rows = db.query(models.User).order_by(models.User.email).all()
    return [
        UserPublic(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=getattr(u, "role", "staff"),
        )
        for u in rows
    ]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> UserPublic:
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    u = models.User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=body.is_active,
        role=body.role or "staff",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return UserPublic(id=str(u.id), email=u.email, full_name=u.full_name, role=getattr(u, "role", "staff"))


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: UUID, body: UserUpdate, db: Session = Depends(get_db)) -> UserPublic:
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        exists = db.query(models.User).filter(models.User.email == data["email"], models.User.id != u.id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        u.email = data["email"]
    if "full_name" in data and data["full_name"] is not None:
        u.full_name = data["full_name"]
    if "role" in data and data["role"] is not None:
        u.role = data["role"]
    if "is_active" in data and data["is_active"] is not None:
        u.is_active = data["is_active"]
    if "password" in data and data["password"]:
        u.hashed_password = hash_password(data["password"])

    db.commit()
    db.refresh(u)
    return UserPublic(id=str(u.id), email=u.email, full_name=u.full_name, role=getattr(u, "role", "staff"))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> None:
    u = db.get(models.User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(u)
    db.commit()

