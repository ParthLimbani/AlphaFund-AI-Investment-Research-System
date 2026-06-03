"""
Fetches recent news articles about a ticker using NewsAPI (free tier: 100 req/day).
Falls back to yfinance news if NewsAPI key is not set.
"""
import os
import requests
from datetime import datetime, timedelta
from src.config import NEWSAPI_KEY


def get_news(ticker: str, company_name: str = "", days: int = 7, max_articles: int = 10) -> dict:
    """
    Fetches recent news. Uses NewsAPI if key is available, else yfinance news.
    Returns list of {title, description, source, published_at, url}.
    """
    if NEWSAPI_KEY:
        return _newsapi_fetch(ticker, company_name, days, max_articles)
    return _yfinance_news_fetch(ticker, max_articles)


def _newsapi_fetch(ticker: str, company_name: str, days: int, max_articles: int) -> dict:
    query = company_name if company_name else ticker
    from_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f"{query} stock",
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": max_articles,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
                "url": a.get("url", ""),
            }
            for a in data.get("articles", [])
        ]
        return {"ticker": ticker, "source": "newsapi", "articles": articles}
    except Exception as e:
        return {"ticker": ticker, "source": "newsapi", "articles": [], "error": str(e)}


def _yfinance_news_fetch(ticker: str, max_articles: int) -> dict:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        raw = t.news or []
        articles = [
            {
                "title": item.get("content", {}).get("title", ""),
                "description": item.get("content", {}).get("summary", ""),
                "source": item.get("content", {}).get("provider", {}).get("displayName", ""),
                "published_at": item.get("content", {}).get("pubDate", ""),
                "url": item.get("content", {}).get("canonicalUrl", {}).get("url", ""),
            }
            for item in raw[:max_articles]
        ]
        return {"ticker": ticker, "source": "yfinance", "articles": articles}
    except Exception as e:
        return {"ticker": ticker, "source": "yfinance", "articles": [], "error": str(e)}
