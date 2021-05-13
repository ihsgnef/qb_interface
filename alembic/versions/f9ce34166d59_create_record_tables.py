"""create record tables

Revision ID: f9ce34166d59
Revises: 1bdc199a8ef5
Create Date: 2021-01-09 18:27:36.681578

"""
from tqdm import tqdm
from alembic import op
from sqlalchemy import orm
from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

from augment.models import Player, Question

# revision identifiers, used by Alembic.
revision = 'f9ce34166d59'
down_revision = '1bdc199a8ef5'
branch_labels = None
depends_on = None


def schema_upgrade():
    op.create_table(
        'record',
        Column('id', String, primary_key=True, index=True),
        Column('player_id', String, ForeignKey(Player.id), index=True),
        Column('question_id', String, ForeignKey(Question.id), index=True),
        Column('position_start', Integer, nullable=False),
        Column('position_buzz', Integer),
        Column('guess', String),
        Column('result', Integer),
        Column('score', Integer),
        Column('enabled_viz', String),
        Column('viz_control', String),
        Column('date', TIMESTAMP(timezone=True)),
    )


def schema_downgrade():
    op.drop_table('record')


def upgrade():
    schema_upgrade()


def downgrade():
    schema_downgrade()
