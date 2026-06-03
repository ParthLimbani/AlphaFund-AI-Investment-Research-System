import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter
from src.memory.episodic_memory import get_recent_decisions, get_all_decisions

router = APIRouter()


@router.get("/history")
async def all_history(limit: int = 50):
    return {"decisions": get_all_decisions(limit=limit)}


@router.get("/history/{ticker}")
async def ticker_history(ticker: str, limit: int = 20):
    return {"ticker": ticker.upper(), "decisions": get_recent_decisions(ticker.upper(), limit=limit)}
