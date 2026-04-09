from sqlalchemy import Column, Integer, String, Float
from app.db.database import Base


class Fighter(Base):
    __tablename__ = "fighters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    height = Column(String)
    weight = Column(Integer)
    reach = Column(Float)
    stance = Column(String)
    strikes_per_min = Column(Float, default=0)
    takedowns_avg = Column(Float, default=0)
    submission_avg = Column(Float, default=0)
    defense = Column(Integer, default=50)
    striking = Column(Integer, default=50)
    wrestling = Column(Integer, default=50)
    cardio = Column(Integer, default=50)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_streak = Column(Integer, default=0)
    strike_accuracy = Column(Integer, default=50)
    td_defense = Column(Integer, default=50)
