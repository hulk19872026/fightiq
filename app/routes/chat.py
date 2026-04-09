from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.agents.main_agent import process_chat

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await process_chat(req.message, db)
    return result
