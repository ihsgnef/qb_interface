from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from centaur.db.base_class import Base
from centaur.models import Question


class QantaCache(Base):
    question_id = Column(String, ForeignKey(Question.id), primary_key=True)
    position = Column(Integer, primary_key=True)
    answer = Column(String, nullable=False)
    guesses = Column(JSONB)
    buzz_scores = Column(JSONB)
    matches = Column(JSONB)
    text_highlight = Column(JSONB)
    matches_highlight = Column(JSONB)

    question = relationship("Question", back_populates="caches")
