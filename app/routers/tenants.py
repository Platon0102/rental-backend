from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantOut
from app.auth import get_current_user, require_manager, require_admin

router = APIRouter(prefix="/tenants", tags=["Арендаторы"])


def _bc_filter(q, current_user: User):
    if current_user.role != UserRole.superadmin:
        q = q.filter(Tenant.business_center_id == current_user.business_center_id)
    return q


@router.get("/", response_model=List[TenantOut])
def list_tenants(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = _bc_filter(db.query(Tenant), current_user)
    if search:
        q = q.filter(Tenant.name.ilike(f"%{search}%") | Tenant.inn.ilike(f"%{search}%"))
    return q.order_by(Tenant.name).all()


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = _bc_filter(db.query(Tenant), current_user)
    tenant = q.filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Арендатор не найден")
    return tenant


@router.post("/", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(data: TenantCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    bc_id = current_user.business_center_id
    tenant = Tenant(**data.model_dump(), business_center_id=bc_id)
    db.add(tenant)
    try:
        db.commit()
        db.refresh(tenant)
        return tenant
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Арендатор с таким ИНН уже существует")


@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(tenant_id: int, data: TenantUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    q = _bc_filter(db.query(Tenant), current_user)
    tenant = q.filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Арендатор не найден")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)
    try:
        db.commit()
        db.refresh(tenant)
        return tenant
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Арендатор с таким ИНН уже существует")


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    q = _bc_filter(db.query(Tenant), current_user)
    tenant = q.filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Арендатор не найден")
    db.delete(tenant)
    db.commit()
