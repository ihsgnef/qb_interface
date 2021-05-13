from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from centaur.db.base_class import Base


class Question(Base):
    id = Column(String, primary_key=True, index=True)
    answer = Column(String, nullable=False)
    raw_text = Column(JSONB, nullable=False)
    length = Column(Integer, nullable=False)
    tokens = Column(JSONB, nullable=False)
    tournament = Column(String)
    meta = Column(JSONB)

    records = relationship('Record', order_by='Record.date', back_populates='question')
    caches = relationship('QantaCache', order_by='QantaCache.position', back_populates='question')
