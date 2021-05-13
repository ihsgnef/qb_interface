"""viz_control to mediator

Revision ID: 783a124c9757
Revises: 1f3b47e3e2eb
Create Date: 2021-01-22 06:50:46.182716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '783a124c9757'
down_revision = '1f3b47e3e2eb'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('player', 'viz_control', new_column_name='mediator_name')
    op.alter_column('record', 'viz_control', new_column_name='mediator_name')


def downgrade():
    op.alter_column('player', 'mediator_name', new_column_name='viz_control')
    op.alter_column('record', 'mediator_name', new_column_name='viz_control')
