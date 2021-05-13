from sqlalchemy import Column, String, Integer, Float, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship

from centaur.db.base_class import Base
from centaur.models import Player, Question


class Record(Base):
    id = Column(String, primary_key=True, index=True)
    player_id = Column(String, ForeignKey(Player.id), nullable=False, index=True)
    question_id = Column(String, ForeignKey(Question.id), nullable=False, index=True)
    position_start = Column(Integer, nullable=False)
    position_buzz = Column(Integer, nullable=False)
    guess = Column(String)
    result = Column(Integer)
    qb_score = Column(Integer)
    ew_score = Column(Float)
    explanation_config = Column(String)
    mediator_name = Column(String)
    date = Column(TIMESTAMP(timezone=True))

    player = relationship("Player", back_populates="records")
    question = relationship("Question", back_populates="records")
