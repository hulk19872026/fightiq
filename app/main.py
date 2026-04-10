import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.db.seed import seed_fighters
from app.routes import events, fighters, odds, analysis, chat

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_fighters()
    yield
    await engine.dispose()


app = FastAPI(title="FightIQ API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(fighters.router, prefix="/fighter-stats", tags=["Fighters"])
app.include_router(odds.router, prefix="/odds", tags=["Odds"])
app.include_router(analysis.router, prefix="/fight-analysis", tags=["Analysis"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/api-status")
async def debug_api_status():
    """Check if the Odds API key is configured and working."""
    import os
    from app.services.odds_api import fetch_events, fetch_odds
    from app.services.cache import _store

    key = os.getenv("ODDS_API_KEY", "")
    key_status = f"set ({len(key)} chars)" if key else "NOT SET"

    events = await fetch_events()
    odds = await fetch_odds()

    events_source = "fallback"
    if events and events[0].get("date", "") not in ("Sat, Apr 11 – 9 PM ET",):
        events_source = "live_api_or_web"

    return {
        "api_key": key_status,
        "events_count": len(events),
        "events_source": events_source,
        "events_preview": [
            {"name": e.get("name"), "date": e.get("date"), "fights": len(e.get("fights", []))}
            for e in events
        ],
        "odds_count": len(odds),
        "cache_keys": list(_store.keys()),
    }


@app.get("/debug/raw-api")
async def debug_raw_api():
    """Dump raw Odds API response to see actual field values."""
    import os
    import httpx

    key = os.getenv("ODDS_API_KEY", "")
    if not key:
        return {"error": "ODDS_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/events",
                params={"apiKey": key},
            )
        raw = resp.json()
        # Show first 5 events with ALL fields so we can see what's available
        return {
            "status": resp.status_code,
            "total_events": len(raw) if isinstance(raw, list) else "not_a_list",
            "sample_events": raw[:5] if isinstance(raw, list) else raw,
            "all_fields": list(raw[0].keys()) if isinstance(raw, list) and raw else [],
            "descriptions": [
                {"home": e.get("home_team"), "away": e.get("away_team"), "desc": e.get("description"), "id": e.get("id", "")[:30]}
                for e in (raw[:15] if isinstance(raw, list) else [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


# Serve React frontend
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(STATIC_DIR / "index.html"))
