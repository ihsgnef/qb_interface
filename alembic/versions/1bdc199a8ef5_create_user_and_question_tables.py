"""create user and question tables

Revision ID: 1bdc199a8ef5
Revises: 
Create Date: 2021-01-09 18:22:56.597636

"""
import json
from tqdm import tqdm
from alembic import op
from sqlalchemy import orm
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import JSONB

from augment.config import settings
from augment.models import Question


# revision identifiers, used by Alembic.
revision = '1bdc199a8ef5'
down_revision = None
branch_labels = None
depends_on = None


def schema_upgrade():
    op.create_table(
        'player',
        Column('id', String, primary_key=True, index=True),
        Column('ip_addr', String, index=True),
        Column('name', String),
        Column('viz_control', String),
        Column('score', Integer),
        Column('questions_seen', JSONB),
        Column('questions_answered', JSONB),
        Column('questions_correct', JSONB),
    )

    op.create_table(
        'question',
        Column('id', String, primary_key=True, index=True),
        Column('answer', String, nullable=False),
        Column('raw_text', JSONB, nullable=False),
        Column('length', Integer, nullable=False),
        Column('tokens', JSONB, nullable=False),
    )


def data_upgrade():
    with open(f'{settings.DATA_DIR}/pace_questions.json') as f:
        qb_questions = json.load(f)

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for q in tqdm(qb_questions):
        new_question = Question(
            id=f'pace_{q["qid"]}',
            answer=q['answer'].replace('_', ' '),
            raw_text=q['raw_text'],
            length=q['length'],
            tokens=q['tokens'],
        )
        session.add(new_question)
    session.commit()


def schema_downgrade():
    op.drop_table('player')
    op.drop_table('question')


def upgrade():
    schema_upgrade()
    data_upgrade()


def downgrade():
    schema_downgrade()
