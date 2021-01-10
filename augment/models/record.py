from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship

from augment.db.base_class import Base
from augment.models import Player, Question


class Record(Base):
    id = Column(String, primary_key=True, index=True)
    player_id = Column(String, ForeignKey(Player.id), nullable=False, index=True)
    question_id = Column(String, ForeignKey(Question.id), nullable=False, index=True)
    position_start = Column(Integer, nullable=False)
    position_buzz = Column(Integer, nullable=False)
    guess = Column(String)
    result = Column(Integer)
    score = Column(Integer)
    enabled_viz = Column(String)
    viz_control = Column(String)
    date = Column(TIMESTAMP(timezone=True))

    player = relationship("Player", back_populates="records")
    question = relationship("Question", back_populates="records")
