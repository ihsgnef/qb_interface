from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from augment.db.base_class import Base


class Player(Base):
    id = Column(String, primary_key=True, index=True)
    ip_addr = Column(String, index=True)
    name = Column(String)
    viz_control = Column(String)

    records = relationship('Record', order_by='Record.date', back_populates='player')