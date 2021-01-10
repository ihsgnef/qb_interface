from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from augment.db.base_class import Base


class Player(Base):
    id = Column(String, primary_key=True, index=True)
    ip_addr = Column(String, index=True)
    name = Column(String)
    viz_control = Column(String)
    score = Column(Integer)
    questions_seen = Column(JSONB)
    questions_answered = Column(JSONB)
    questions_correct = Column(JSONB)

    records = relationship('Record', order_by='Record.date', back_populates='player')