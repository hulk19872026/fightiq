from fastapi import APIRouter
from app.services.espn import fetch_events

router = APIRouter()


@router.get("")
async def get_events():
    events = await fetch_events()
    return {"events": events}
