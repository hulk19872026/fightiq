from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.models.fighter import Fighter
from app.agents.stats_agent import get_fighter_stats

router = APIRouter()


@router.get("")
async def fighter_stats(name: str = Query(...), db: AsyncSession = Depends(get_db)):
    stats = await get_fighter_stats(name, db)
    if not stats:
        return {"error": "Fighter not found"}
    return stats


@router.get("/all")
async def all_fighters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fighter).order_by(Fighter.name))
    fighters = result.scalars().all()
    return [
        {
            "name": f.name,
            "weight": f.weight,
            "wins": f.wins,
            "losses": f.losses,
            "win_streak": f.win_streak,
            "strikes_per_min": f.strikes_per_min,
            "takedowns_avg": f.takedowns_avg,
        }
        for f in fighters
    ]
