from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fighter import Fighter
from app.services.search import search_fighter_stats


async def get_fighter_stats(name: str, db: AsyncSession) -> dict | None:
    # Try DB first
    result = await db.execute(
        select(Fighter).where(func.lower(Fighter.name).contains(name.lower()))
    )
    fighter = result.scalars().first()
    if fighter:
        return _fighter_to_dict(fighter)

    # Fallback: search the web
    web_stats = await search_fighter_stats(name)
    if web_stats:
        return _normalize_web_stats(web_stats)

    return None


async def compare_fighters(name_a: str, name_b: str, db: AsyncSession) -> dict:
    a = await get_fighter_stats(name_a, db)
    b = await get_fighter_stats(name_b, db)
    if not a or not b:
        return {"error": "Fighter not found", "fighter_a": a, "fighter_b": b}
    return {"fighter_a": a, "fighter_b": b}


def _fighter_to_dict(fighter: Fighter) -> dict:
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
        "source": "database",
    }


def _normalize_web_stats(stats: dict) -> dict:
    """Fill in defaults for any missing fields from web search."""
    return {
        "name": stats.get("name", "Unknown"),
        "height": stats.get("height", "N/A"),
        "weight": stats.get("weight", 0),
        "reach": stats.get("reach", 0),
        "stance": stats.get("stance", "N/A"),
        "strikes_per_min": stats.get("strikes_per_min", 0),
        "takedowns_avg": stats.get("takedowns_avg", 0),
        "submission_avg": stats.get("submission_avg", 0),
        "defense": stats.get("defense", 50),
        "striking": stats.get("striking", 50),
        "wrestling": stats.get("wrestling", 50),
        "cardio": stats.get("cardio", 50),
        "wins": stats.get("wins", 0),
        "losses": stats.get("losses", 0),
        "win_streak": stats.get("win_streak", 0),
        "strike_accuracy": stats.get("strike_accuracy", 0),
        "td_defense": stats.get("td_defense", 0),
        "source": "web_search",
    }
