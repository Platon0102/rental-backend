from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.business_center import BusinessCenter
from app.auth import hash_password, verify_password, create_access_token, get_current_user, require_admin, require_superadmin

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.manager
    business_center_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: UserRole
    business_center_id: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/register", response_model=UserResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email уже занят")

    # superadmin может создавать любых пользователей
    # bc_admin может создавать только пользователей своего БЦ
    if current_user.role == UserRole.bc_admin:
        bc_id = current_user.business_center_id
    else:
        bc_id = data.business_center_id

    # superadmin не требует bc_id
    if data.role != UserRole.superadmin and bc_id is None:
        raise HTTPException(status_code=400, detail="Укажите business_center_id")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        business_center_id=bc_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if current_user.role == UserRole.superadmin:
        return db.query(User).all()
    return db.query(User).filter(User.business_center_id == current_user.business_center_id).all()


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if current_user.role == UserRole.bc_admin and user.business_center_id != current_user.business_center_id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    user.is_active = False
    db.commit()
    return {"ok": True}
