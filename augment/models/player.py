from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from augment.db.base_class import Base


class Player(Base):
    id = Column(String, primary_key=True, index=True)
    ip_addr = Column(String, index=True)
    name = Column(String)
    mediator_name = Column(String)
    score = Column(Integer)
    questions_seen = Column(JSONB)
    questions_answered = Column(JSONB)
    questions_correct = Column(JSONB)

    records = relationship('Record', order_by='Record.date', back_populates='player')
    # features = relationship('Features', back_populates='player', uselist=False)


class Features(Base):
    id = Column(String, ForeignKey(Player.id, ondelete="CASCADE"), primary_key=True, index=True)
    enabled_explanation = Column(JSONB)
    enabled_config = Column(JSONB)
    n_seen = Column(Integer)
    n_answered = Column(Integer)
    n_correct = Column(Integer)
    n_seen_by_explanation = Column(JSONB)
    n_seen_by_config = Column(JSONB)
    n_answered_by_explanation = Column(JSONB)
    n_answered_by_config = Column(JSONB)
    n_correct_by_explanation = Column(JSONB)
    n_correct_by_config = Column(JSONB)
