from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import os

from app.database import engine, Base
from app.config import settings
from app.routers import rooms, tenants, contracts, payments, utilities, dashboard, notifications, auth, business_centers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск Telegram-бота в фоне
    if settings.TELEGRAM_TOKEN:
        from app import bot
        task = asyncio.create_task(bot.poll_loop())
    else:
        task = None
    yield
    # Остановка бота
    if task:
        from app import bot
        bot.stop()
        task.cancel()


# Создать все таблицы
Base.metadata.create_all(bind=engine)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="БЦ «Золотой» — API системы аренды",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(business_centers.router)
app.include_router(dashboard.router)
app.include_router(rooms.router)
app.include_router(tenants.router)
app.include_router(contracts.router)
app.include_router(payments.router)
app.include_router(utilities.router)
app.include_router(notifications.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "БЦ Золотой API"}
