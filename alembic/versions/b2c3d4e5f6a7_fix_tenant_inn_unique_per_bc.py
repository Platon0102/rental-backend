"""fix_tenant_inn_unique_per_bc

Revision ID: b2c3d4e5f6a7
Revises: 5ca2be2ae1a7
Create Date: 2026-06-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '5ca2be2ae1a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Удаляем глобальный уникальный индекс на inn
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tenants_inn_key') THEN
                ALTER TABLE tenants DROP CONSTRAINT tenants_inn_key;
            END IF;
        END $$
    """))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_tenants_inn"))

    # Создаём составной уникальный индекс только где inn IS NOT NULL
    conn.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_inn_per_bc
        ON tenants (inn, business_center_id)
        WHERE inn IS NOT NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_tenant_inn_per_bc"))
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_tenants_inn ON tenants (inn) WHERE inn IS NOT NULL"))
