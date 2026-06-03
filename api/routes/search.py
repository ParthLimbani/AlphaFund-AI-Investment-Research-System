from fastapi import APIRouter

router = APIRouter()


@router.get("/search")
def search_tickers(q: str = ""):
    if len(q.strip()) < 1:
        return []
    try:
        from yfinance import Search
        results = Search(q.strip(), max_results=8, news_count=0).quotes
        return [
            {
                "symbol": r.get("symbol", ""),
                "name": r.get("shortname") or r.get("longname") or "",
                "exchange": r.get("exchange", ""),
            }
            for r in results
            if r.get("symbol")
        ]
    except Exception:
        return []
