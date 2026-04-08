from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import LoginIn, TokenOut, UserPublic
from app.security import create_access_token, verify_password
from app.deps import get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    token = create_access_token(str(user.id))
    return TokenOut(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserPublic)
def me(user: models.User = Depends(get_current_active_user)) -> UserPublic:
    return UserPublic(id=str(user.id), email=user.email, full_name=user.full_name, role=getattr(user, "role", "staff"))

