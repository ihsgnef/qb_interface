from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from augment.db.base_class import Base
from augment.models import Question


class QantaCache(Base):
    id = Column(String, primary_key=True, index=True)
    question_id = Column(String, ForeignKey(Question.id), primary_key=True, index=True)
    position = Column(Integer, nullable=False, index=True)
    answer = Column(String, nullable=False)
    guesses = Column(JSONB)
    buzz_scores = Column(JSONB)
    matches = Column(JSONB)
    text_highlight = Column(JSONB)
    matches_highlight = Column(JSONB)

    question = relationship("Question", back_populates="caches")
