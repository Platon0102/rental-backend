"""add_business_centers_and_roles

Revision ID: 5ca2be2ae1a7
Revises:
Create Date: 2026-06-08 01:31:19.871318

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '5ca2be2ae1a7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Создаём таблицу business_centers если не существует
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS business_centers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            address VARCHAR(300),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP DEFAULT now()
        )
    """))

    # 2. Вставляем дефолтный БЦ если таблица пустая
    conn.execute(sa.text("""
        INSERT INTO business_centers (name, address)
        SELECT 'БЦ Золотой', ''
        WHERE NOT EXISTS (SELECT 1 FROM business_centers LIMIT 1)
    """))

    # 3. Добавляем business_center_id в rooms
    conn.execute(sa.text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS business_center_id INTEGER"))
    conn.execute(sa.text("UPDATE rooms SET business_center_id = 1 WHERE business_center_id IS NULL"))
    conn.execute(sa.text("ALTER TABLE rooms ALTER COLUMN business_center_id SET NOT NULL"))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rooms_business_center_id_fkey') THEN
                ALTER TABLE rooms ADD CONSTRAINT rooms_business_center_id_fkey
                    FOREIGN KEY (business_center_id) REFERENCES business_centers(id);
            END IF;
        END $$
    """))

    # 4. Добавляем business_center_id в tenants
    conn.execute(sa.text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_center_id INTEGER"))
    conn.execute(sa.text("UPDATE tenants SET business_center_id = 1 WHERE business_center_id IS NULL"))
    conn.execute(sa.text("ALTER TABLE tenants ALTER COLUMN business_center_id SET NOT NULL"))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tenants_business_center_id_fkey') THEN
                ALTER TABLE tenants ADD CONSTRAINT tenants_business_center_id_fkey
                    FOREIGN KEY (business_center_id) REFERENCES business_centers(id);
            END IF;
        END $$
    """))

    # 5. Создаём enum тип userrole
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                CREATE TYPE userrole AS ENUM ('superadmin', 'bc_admin', 'manager', 'accountant');
            END IF;
        END $$
    """))

    # 6. Добавляем role и business_center_id в users
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role userrole"))
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS business_center_id INTEGER"))

    # 7. Заполняем роли для существующих пользователей
    conn.execute(sa.text("UPDATE users SET role = 'bc_admin' WHERE is_admin = true AND role IS NULL"))
    conn.execute(sa.text("UPDATE users SET role = 'manager' WHERE role IS NULL"))
    conn.execute(sa.text("UPDATE users SET business_center_id = 1 WHERE role::text != 'superadmin' AND business_center_id IS NULL"))
    conn.execute(sa.text("ALTER TABLE users ALTER COLUMN role SET NOT NULL"))

    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_business_center_id_fkey') THEN
                ALTER TABLE users ADD CONSTRAINT users_business_center_id_fkey
                    FOREIGN KEY (business_center_id) REFERENCES business_centers(id);
            END IF;
        END $$
    """))

    # 8. Удаляем старую колонку is_admin
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS is_admin"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false"))
    conn.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_business_center_id_fkey"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS business_center_id"))
    conn.execute(sa.text("ALTER TABLE users DROP COLUMN IF EXISTS role"))
    conn.execute(sa.text("DROP TYPE IF EXISTS userrole"))
    conn.execute(sa.text("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_business_center_id_fkey"))
    conn.execute(sa.text("ALTER TABLE tenants DROP COLUMN IF EXISTS business_center_id"))
    conn.execute(sa.text("ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_business_center_id_fkey"))
    conn.execute(sa.text("ALTER TABLE rooms DROP COLUMN IF EXISTS business_center_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS business_centers"))
