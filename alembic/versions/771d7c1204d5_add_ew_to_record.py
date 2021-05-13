"""add ew to record

Revision ID: 771d7c1204d5
Revises: 6252a49447cc
Create Date: 2021-02-01 21:23:53.159721

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '771d7c1204d5'
down_revision = '6252a49447cc'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('record', 'score', new_column_name='qb_score')
    op.add_column('record', sa.Column('ew_score', sa.Float))


def downgrade():
    op.alter_column('record', 'qb_score', new_column_name='score')
    op.drop_column('record', 'ew_score')
