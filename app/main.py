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


# Serve React frontend
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(STATIC_DIR / "index.html"))
