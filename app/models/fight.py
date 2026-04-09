from sqlalchemy import Column, Integer, String, Date
from app.db.database import Base


class Fight(Base):
    __tablename__ = "fights"

    id = Column(Integer, primary_key=True, index=True)
    fighter_a = Column(String, nullable=False)
    fighter_b = Column(String, nullable=False)
    event_name = Column(String, nullable=False)
    date = Column(Date)
    result = Column(String)
    weight_class = Column(String)
    is_main_event = Column(Integer, default=0)
