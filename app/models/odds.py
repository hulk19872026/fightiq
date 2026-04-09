from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime, timezone
from app.db.database import Base


class Odds(Base):
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, index=True)
    fight_id = Column(Integer, index=True)
    fighter_a_name = Column(String)
    fighter_b_name = Column(String)
    fighter_a_odds = Column(Integer, default=0)
    fighter_b_odds = Column(Integer, default=0)
    over_under = Column(Float)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
