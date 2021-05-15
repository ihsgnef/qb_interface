from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from centaur.db.base_class import Base
from centaur.models import Player


class PlayerRoundStat(Base):
    player_id = Column(String, ForeignKey(Player.id), primary_key=True, nullable=False, index=True)
    room_id = Column(String, primary_key=True, nullable=False, index=True)
    qb_score = Column(Integer)
    ew_score = Column(Float)
    questions_answered = Column(JSONB)
    questions_correct = Column(JSONB)
