from fastapi import APIRouter, Query
from app.services.odds_api import fetch_odds

router = APIRouter()


@router.get("")
async def get_odds(fight: str = Query(default="")):
    all_odds = await fetch_odds()
    if fight:
        filtered = [o for o in all_odds if fight.lower() in o["fight"].lower()]
        return {"odds": filtered if filtered else all_odds}
    return {"odds": all_odds}
