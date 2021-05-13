"""enabled_viz to explanation_config

Revision ID: 6252a49447cc
Revises: 783a124c9757
Create Date: 2021-01-22 11:10:14.838286

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6252a49447cc'
down_revision = '783a124c9757'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('record', 'enabled_viz', new_column_name='explanation_config')


def downgrade():
    op.alter_column('record', 'explanation_config', new_column_name='enabled_viz')
