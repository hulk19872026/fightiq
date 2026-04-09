from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.agents.stats_agent import compare_fighters
from app.agents.research_agent import analyze_matchup
from app.agents.betting_agent import analyze_betting
from app.services.odds_api import fetch_odds

router = APIRouter()


@router.get("")
async def fight_analysis(
    fighterA: str = Query(...),
    fighterB: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    comp = await compare_fighters(fighterA, fighterB, db)
    a = comp.get("fighter_a")
    b = comp.get("fighter_b")
    if not a or not b:
        return {"error": "One or both fighters not found", "detail": comp}

    prediction = analyze_matchup(a, b)

    all_odds = await fetch_odds()
    fight_odds = None
    a_last = fighterA.split()[-1].lower()
    b_last = fighterB.split()[-1].lower()
    for o in all_odds:
        fl = o["fight"].lower()
        if a_last in fl or b_last in fl:
            fight_odds = o
            break

    betting = analyze_betting(a, b, fight_odds, prediction)

    return {
        "fighters": comp,
        "prediction": prediction,
        "betting": betting,
    }
