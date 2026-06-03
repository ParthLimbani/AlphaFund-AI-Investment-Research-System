import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter
from src.memory.episodic_memory import get_beliefs

router = APIRouter()


@router.get("/memory/{ticker}")
async def ticker_memory(ticker: str):
    beliefs = get_beliefs(ticker=ticker.upper(), limit=30)
    return {"ticker": ticker.upper(), "beliefs": beliefs}


@router.get("/memory")
async def global_memory():
    beliefs = get_beliefs(ticker=None, limit=30)
    return {"beliefs": beliefs}
