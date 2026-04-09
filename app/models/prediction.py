from sqlalchemy import Column, Integer, String, Float
from app.db.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    fight_id = Column(Integer, index=True)
    fighter_a = Column(String)
    fighter_b = Column(String)
    predicted_winner = Column(String)
    method = Column(String)
    confidence_score = Column(Float)
    risk_level = Column(String)
    reasoning = Column(String)
