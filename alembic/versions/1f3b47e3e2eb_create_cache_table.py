"""create cache table

Revision ID: 1f3b47e3e2eb
Revises: f9ce34166d59
Create Date: 2021-01-09 18:48:26.657057

"""
import json
from alembic import op
from sqlalchemy import orm
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from augment.config import settings
from augment.models import Question, QantaCache


# revision identifiers, used by Alembic.
revision = '1f3b47e3e2eb'
down_revision = 'f9ce34166d59'
branch_labels = None
depends_on = None


def schema_upgrade():
    op.create_table(
        'qantacache',
        Column('question_id', String, ForeignKey(Question.id), primary_key=True),
        Column('position', Integer, primary_key=True),
        Column('answer', String, nullable=False),
        Column('guesses', JSONB),
        Column('buzz_scores', JSONB),
        Column('matches', JSONB),
        Column('text_highlight', JSONB),
        Column('matches_highlight', JSONB),
    )


def data_upgrade():
    with open(f'{settings.DATA_DIR}/pace_cache.json') as f:
        qanta_cache = json.load(f)  # qid -> position -> entry

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    for qid, question_cache in qanta_cache.items():
        for position, entry in question_cache.items():
            qid = entry['qid']
            qid = f'pace_{qid}'
            entry = QantaCache(
                question_id=qid,
                position=position,
                answer=entry['answer'],
                guesses=entry['guesses'],
                buzz_scores=entry['buzz_scores'],
                matches=entry['matches'],
                text_highlight=entry['text_highlight'],
                matches_highlight=entry['matches_highlight'],
            )
            session.add(entry)

    session.commit()


def schema_downgrade():
    op.drop_table('qantacache')


def upgrade():
    schema_upgrade()
    data_upgrade()


def downgrade():
    schema_downgrade()
