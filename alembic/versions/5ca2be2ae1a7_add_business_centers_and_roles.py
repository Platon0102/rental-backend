"""add_business_centers_and_roles

Revision ID: 5ca2be2ae1a7
Revises:
Create Date: 2026-06-08 01:31:19.871318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ca2be2ae1a7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Создаём таблицу business_centers
    op.create_table(
        'business_centers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('address', sa.String(300), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # 2. Вставляем дефолтный БЦ для существующих данных
    op.execute("INSERT INTO business_centers (name, address) VALUES ('БЦ Золотой', '') RETURNING id")

    # 3. Добавляем колонки как nullable сначала
    op.add_column('rooms', sa.Column('business_center_id', sa.Integer(), nullable=True))
    op.add_column('tenants', sa.Column('business_center_id', sa.Integer(), nullable=True))

    # 4. Заполняем существующие записи дефолтным БЦ (id=1)
    op.execute("UPDATE rooms SET business_center_id = 1")
    op.execute("UPDATE tenants SET business_center_id = 1")

    # 5. Делаем колонки NOT NULL
    op.alter_column('rooms', 'business_center_id', nullable=False)
    op.alter_column('tenants', 'business_center_id', nullable=False)

    # 6. Создаём внешние ключи
    op.create_foreign_key(None, 'rooms', 'business_centers', ['business_center_id'], ['id'])
    op.create_foreign_key(None, 'tenants', 'business_centers', ['business_center_id'], ['id'])

    # 7. Обновляем users: добавляем role и business_center_id
    userrole = sa.Enum('superadmin', 'bc_admin', 'manager', 'accountant', name='userrole')
    userrole.create(op.get_bind(), checkfirst=True)
    op.add_column('users', sa.Column('role', sa.Enum('superadmin', 'bc_admin', 'manager', 'accountant', name='userrole'), nullable=True))
    op.add_column('users', sa.Column('business_center_id', sa.Integer(), nullable=True))
    op.execute("UPDATE users SET role = 'bc_admin' WHERE is_admin = true")
    op.execute("UPDATE users SET role = 'manager' WHERE is_admin = false OR is_admin IS NULL")
    op.execute("UPDATE users SET business_center_id = 1 WHERE role != 'superadmin'")
    op.alter_column('users', 'role', nullable=False)
    op.create_foreign_key(None, 'users', 'business_centers', ['business_center_id'], ['id'])
    op.drop_column('users', 'is_admin')


def downgrade() -> None:
    op.add_column('users', sa.Column('is_admin', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'business_center_id')
    op.drop_column('users', 'role')
    op.execute("DROP TYPE IF EXISTS userrole")
    op.drop_constraint(None, 'tenants', type_='foreignkey')
    op.drop_column('tenants', 'business_center_id')
    op.drop_constraint(None, 'rooms', type_='foreignkey')
    op.drop_column('rooms', 'business_center_id')
    op.drop_table('business_centers')
