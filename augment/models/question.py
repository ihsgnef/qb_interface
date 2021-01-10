from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from augment.db.base_class import Base


class Question(Base):
    id = Column(String, primary_key=True, index=True)
    answer = Column(String, nullable=False)
    raw_text = Column(String, nullable=False)
    length = Column(Integer, nullable=False)
    tokens = Column(JSONB, nullable=False)

    records = relationship('Record', order_by='Record.date', back_populates='question')
    caches = relationship('QantaCache', order_by='QantaCache.position', back_populates='question')
