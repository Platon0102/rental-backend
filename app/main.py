from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.config import settings
from app.routers import rooms, tenants, contracts, payments, utilities, dashboard

# Создать все таблицы (в продакшене используйте Alembic)
Base.metadata.create_all(bind=engine)

# Создать папку для файлов
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="БЦ «Золотой» — API системы аренды",
    description="Управление помещениями, договорами, платежами и коммунальными услугами",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — разрешить запросы от фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика для загруженных файлов
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Роутеры
app.include_router(dashboard.router)
app.include_router(rooms.router)
app.include_router(tenants.router)
app.include_router(contracts.router)
app.include_router(payments.router)
app.include_router(utilities.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "БЦ Золотой API"}
