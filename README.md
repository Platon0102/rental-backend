# БЦ «Золотой» — Backend API

FastAPI + PostgreSQL + SQLAlchemy + Alembic

## Быстрый старт

### 1. Через Docker (рекомендуется)
```bash
cp .env.example .env
docker-compose up --build
```
API доступен на http://localhost:8000  
Swagger UI: http://localhost:8000/docs

### 2. Локально
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # настройте DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

## Структура проекта
```
backend/
├── app/
│   ├── main.py          # точка входа, CORS, подключение роутеров
│   ├── config.py        # настройки из .env
│   ├── database.py      # SQLAlchemy engine + get_db
│   ├── models/          # ORM-модели
│   │   ├── room.py      # Room, RoomStatusHistory
│   │   ├── tenant.py    # Tenant
│   │   ├── contract.py  # Contract
│   │   ├── payment.py   # Payment
│   │   ├── utility.py   # UtilityReading, UtilityBill
│   │   └── user.py      # User
│   ├── schemas/         # Pydantic-схемы (валидация)
│   └── routers/         # API endpoints
│       ├── dashboard.py # /dashboard — статистика
│       ├── rooms.py     # /rooms — CRUD + смена статуса
│       ├── tenants.py   # /tenants — CRUD
│       ├── contracts.py # /contracts — CRUD + загрузка файла + расторжение
│       ├── payments.py  # /payments — начисление + оплата
│       └── utilities.py # /utilities — показания + счета
├── alembic/             # миграции БД
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Ключевые endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET  | /dashboard/stats | Главная статистика |
| GET  | /dashboard/expiring-contracts | Истекающие договоры |
| GET  | /rooms/ | Список помещений (фильтр: floor, status) |
| POST | /rooms/ | Создать помещение |
| POST | /rooms/{id}/status | Сменить статус помещения |
| GET  | /rooms/{id}/history | История статусов |
| GET  | /tenants/ | Список арендаторов |
| POST | /contracts/ | Создать договор → помещение → Занято |
| POST | /contracts/{id}/upload | Прикрепить скан договора |
| POST | /contracts/{id}/terminate | Расторгнуть договор → помещение → Свободно |
| POST | /payments/ | Создать начисление |
| PATCH| /payments/{id} | Зафиксировать оплату |
| GET  | /payments/debts | Задолженности по всем договорам |
| POST | /utilities/readings/ | Ввести показания счётчика |
| POST | /utilities/bills/generate | Сгенерировать счета за месяц |

## Миграции
```bash
# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "описание"

# Применить миграции
alembic upgrade head

# Откат
alembic downgrade -1
```
