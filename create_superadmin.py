"""
Запуск: python create_superadmin.py
Создаёт суперадмина если его ещё нет.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models import *  # noqa — регистрируем все модели
from app.models.user import User, UserRole
from app.auth import hash_password

EMAIL    = os.getenv("SUPERADMIN_EMAIL", "admin@rental.kg")
PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "changeme123")

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    existing = db.query(User).filter(User.email == EMAIL).first()
    if existing:
        print(f"Суперадмин уже существует: {EMAIL}")
    else:
        user = User(email=EMAIL, full_name="Superadmin", hashed_password=hash_password(PASSWORD),
                    role=UserRole.superadmin, business_center_id=None)
        db.add(user)
        db.commit()
        print(f"Суперадмин создан: {EMAIL} / {PASSWORD}")
finally:
    db.close()
