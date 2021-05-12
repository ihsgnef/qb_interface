"""add meta and tournament to question

Revision ID: 9235bd33b17e
Revises: 771d7c1204d5
Create Date: 2021-05-11 09:30:32.188441

"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '9235bd33b17e'
down_revision = '771d7c1204d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('question', sa.Column('tournament', sa.String))
    op.add_column('question', sa.Column('meta', JSONB))


def downgrade():
    op.drop_column('question', 'tournament')
    op.drop_column('question', 'meta')
