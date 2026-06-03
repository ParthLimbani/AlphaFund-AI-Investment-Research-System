"""
Fetches stock price data, financials, and volatility metrics via yfinance.
All free, no API key required.
"""
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


def get_price_history(ticker: str, days: int = 252) -> dict:
    """OHLCV for the last `days` trading days."""
    end = datetime.today()
    start = end - timedelta(days=days + 60)  # buffer for non-trading days
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return {"error": f"No price data found for {ticker}"}
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.tail(days)
    return {
        "ticker": ticker,
        "start": str(df.index[0].date()),
        "end": str(df.index[-1].date()),
        "close": df["Close"].tolist(),
        "volume": df["Volume"].tolist(),
        "dates": [str(d.date()) for d in df.index],
        "current_price": float(df["Close"].iloc[-1]),
        "52w_high": float(df["High"].max()),
        "52w_low": float(df["Low"].min()),
    }


def get_fundamentals(ticker: str) -> dict:
    """Key financial ratios and income statement data."""
    t = yf.Ticker(ticker)
    info = t.info or {}
    keys = [
        "marketCap", "trailingPE", "forwardPE", "priceToBook",
        "priceToSalesTrailing12Months", "debtToEquity", "returnOnEquity",
        "returnOnAssets", "grossMargins", "operatingMargins", "profitMargins",
        "revenueGrowth", "earningsGrowth", "currentRatio", "quickRatio",
        "totalRevenue", "netIncomeToCommon", "freeCashflow",
        "dividendYield", "beta", "sector", "industry", "longBusinessSummary",
        "fullTimeEmployees", "country",
    ]
    fundamentals = {k: info.get(k) for k in keys}
    fundamentals["ticker"] = ticker
    return fundamentals


def get_volatility_metrics(ticker: str, window: int = 252) -> dict:
    """
    Computes CVaR (95%), annualized vol, and max drawdown.
    Used by the risk manager agent.
    """
    data = get_price_history(ticker, days=window)
    if "error" in data:
        return data

    closes = np.array(data["close"])
    returns = np.diff(closes) / closes[:-1]

    # CVaR (Conditional Value at Risk at 95% confidence)
    sorted_returns = np.sort(returns)
    cutoff_idx = int(len(sorted_returns) * 0.05)
    cvar_95 = float(np.mean(sorted_returns[:cutoff_idx]))

    # Annualized volatility
    ann_vol = float(np.std(returns) * np.sqrt(252))

    # Max drawdown
    peak = np.maximum.accumulate(closes)
    drawdown = (closes - peak) / peak
    max_drawdown = float(np.min(drawdown))

    # 30-day rolling vol
    recent_returns = returns[-30:] if len(returns) >= 30 else returns
    vol_30d = float(np.std(recent_returns) * np.sqrt(252))

    return {
        "ticker": ticker,
        "cvar_95": cvar_95,
        "annualized_vol": ann_vol,
        "vol_30d": vol_30d,
        "max_drawdown": max_drawdown,
        "n_days": len(returns),
    }


def get_sector_volatility(ticker: str) -> dict:
    """
    Approximates sector vol by fetching the sector ETF for comparison.
    Used by risk manager to flag stocks with 2x sector vol.
    """
    sector_etf_map = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Basic Materials": "XLB",
        "Real Estate": "XLRE",
        "Utilities": "XLU",
        "Communication Services": "XLC",
    }
    t = yf.Ticker(ticker)
    sector = (t.info or {}).get("sector", "")
    etf = sector_etf_map.get(sector, "SPY")

    etf_metrics = get_volatility_metrics(etf, window=30)
    stock_metrics = get_volatility_metrics(ticker, window=30)

    return {
        "ticker": ticker,
        "sector": sector,
        "sector_etf": etf,
        "sector_vol_30d": etf_metrics.get("vol_30d"),
        "stock_vol_30d": stock_metrics.get("vol_30d"),
        "vol_ratio": (
            stock_metrics.get("vol_30d", 0) / etf_metrics.get("vol_30d", 1)
            if etf_metrics.get("vol_30d")
            else None
        ),
    }
