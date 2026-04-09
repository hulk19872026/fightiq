from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fighter import Fighter


async def get_fighter_stats(name: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(Fighter).where(func.lower(Fighter.name).contains(name.lower()))
    )
    fighter = result.scalars().first()
    if not fighter:
        return None
    return {
        "name": fighter.name,
        "height": fighter.height,
        "weight": fighter.weight,
        "reach": fighter.reach,
        "stance": fighter.stance,
        "strikes_per_min": fighter.strikes_per_min,
        "takedowns_avg": fighter.takedowns_avg,
        "submission_avg": fighter.submission_avg,
        "defense": fighter.defense,
        "striking": fighter.striking,
        "wrestling": fighter.wrestling,
        "cardio": fighter.cardio,
        "wins": fighter.wins,
        "losses": fighter.losses,
        "win_streak": fighter.win_streak,
        "strike_accuracy": fighter.strike_accuracy,
        "td_defense": fighter.td_defense,
    }


async def compare_fighters(name_a: str, name_b: str, db: AsyncSession) -> dict:
    a = await get_fighter_stats(name_a, db)
    b = await get_fighter_stats(name_b, db)
    if not a or not b:
        return {"error": "Fighter not found", "fighter_a": a, "fighter_b": b}
    return {"fighter_a": a, "fighter_b": b}
