from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.business_center import BusinessCenter
from app.models.user import User
from app.auth import require_superadmin, require_admin, get_current_user

router = APIRouter(prefix="/business-centers", tags=["Business Centers"])


class BCCreate(BaseModel):
    name: str
    address: Optional[str] = None


class BCResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=list[BCResponse])
def list_bcs(db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    return db.query(BusinessCenter).all()


@router.post("/", response_model=BCResponse)
def create_bc(data: BCCreate, db: Session = Depends(get_db), current_user: User = Depends(require_superadmin)):
    bc = BusinessCenter(name=data.name, address=data.address)
    db.add(bc)
    db.commit()
    db.refresh(bc)
    return bc


@router.get("/my", response_model=BCResponse)
def my_bc(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.business_center_id:
        raise HTTPException(status_code=404, detail="БЦ не привязан")
    bc = db.query(BusinessCenter).filter(BusinessCenter.id == current_user.business_center_id).first()
    if not bc:
        raise HTTPException(status_code=404, detail="БЦ не найден")
    return bc


@router.patch("/{bc_id}", response_model=BCResponse)
def update_bc(bc_id: int, data: BCCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    bc = db.query(BusinessCenter).filter(BusinessCenter.id == bc_id).first()
    if not bc:
        raise HTTPException(status_code=404, detail="БЦ не найден")
    bc.name = data.name
    if data.address is not None:
        bc.address = data.address
    db.commit()
    db.refresh(bc)
    return bc
