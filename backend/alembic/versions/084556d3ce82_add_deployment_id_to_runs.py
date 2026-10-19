"""add_deployment_id_to_runs

Revision ID: 084556d3ce82
Revises: d2b26372f7ff
Create Date: 2026-10-19 22:21:21.670990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '084556d3ce82'
down_revision: Union[str, None] = 'd2b26372f7ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('runs') as batch_op:
        batch_op.add_column(sa.Column('deployment_id', sa.String(length=36), nullable=True))
        batch_op.create_index(op.f('ix_runs_deployment_id'), ['deployment_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_runs_deployment_id',
            'deployments',
            ['deployment_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('runs') as batch_op:
        batch_op.drop_constraint('fk_runs_deployment_id', type_='foreignkey')
        batch_op.drop_index('ix_runs_deployment_id')
        batch_op.drop_column('deployment_id')
