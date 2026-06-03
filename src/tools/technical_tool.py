"""
Technical indicator calculations using pandas-ta.
Returns structured dict consumed by the TechnicalAgent.
"""
import numpy as np
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from datetime import datetime, timedelta


def get_technical_indicators(ticker: str, days: int = 120) -> dict:
    """
    Calculates RSI, MACD, Bollinger Bands, ATR, EMA crossovers,
    OBV, and Stochastic for the last `days` trading days.
    """
    end = datetime.today()
    start = end - timedelta(days=days + 80)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return {"error": f"No price data for {ticker}"}

    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.tail(days).copy()

    # RSI (14)
    df.ta.rsi(length=14, append=True)

    # MACD (12, 26, 9)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    # Bollinger Bands (20, 2)
    df.ta.bbands(length=20, std=2, append=True)

    # ATR (14) — volatility proxy
    df.ta.atr(length=14, append=True)

    # EMA 20 and 50 crossover
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)

    # OBV (volume-price momentum)
    df.ta.obv(append=True)

    # Stochastic (14, 3)
    df.ta.stoch(k=14, d=3, append=True)

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    def safe(val):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return float(val)

    # Determine MACD column names (pandas-ta dynamic naming)
    macd_col = next((c for c in df.columns if c.startswith("MACD_") and "s" not in c.lower() and "h" not in c.lower()), None)
    macd_signal_col = next((c for c in df.columns if c.startswith("MACDs_")), None)
    macd_hist_col = next((c for c in df.columns if c.startswith("MACDh_")), None)

    bb_upper = next((c for c in df.columns if c.startswith("BBU_")), None)
    bb_lower = next((c for c in df.columns if c.startswith("BBL_")), None)
    bb_mid = next((c for c in df.columns if c.startswith("BBM_")), None)

    stoch_k = next((c for c in df.columns if c.startswith("STOCHk_")), None)
    stoch_d = next((c for c in df.columns if c.startswith("STOCHd_")), None)

    current_price = safe(last.get("Close"))
    ema20 = safe(last.get("EMA_20"))
    ema50 = safe(last.get("EMA_50"))
    prev_ema20 = safe(prev.get("EMA_20"))
    prev_ema50 = safe(prev.get("EMA_50"))

    # Golden/death cross detection
    golden_cross = (
        ema20 and ema50 and prev_ema20 and prev_ema50
        and prev_ema20 < prev_ema50 and ema20 > ema50
    )
    death_cross = (
        ema20 and ema50 and prev_ema20 and prev_ema50
        and prev_ema20 > prev_ema50 and ema20 < ema50
    )

    rsi = safe(last.get("RSI_14"))
    rsi_signal = (
        "oversold" if rsi and rsi < 30
        else "overbought" if rsi and rsi > 70
        else "neutral"
    )

    macd_val = safe(last[macd_col]) if macd_col else None
    macd_sig = safe(last[macd_signal_col]) if macd_signal_col else None
    macd_hist = safe(last[macd_hist_col]) if macd_hist_col else None
    prev_macd_hist = safe(prev[macd_hist_col]) if macd_hist_col else None
    macd_crossover = (
        "bullish" if macd_hist and prev_macd_hist and prev_macd_hist < 0 and macd_hist > 0
        else "bearish" if macd_hist and prev_macd_hist and prev_macd_hist > 0 and macd_hist < 0
        else "neutral"
    )

    bb_upper_val = safe(last[bb_upper]) if bb_upper else None
    bb_lower_val = safe(last[bb_lower]) if bb_lower else None
    bb_mid_val = safe(last[bb_mid]) if bb_mid else None
    bb_position = None
    if current_price and bb_upper_val and bb_lower_val:
        bb_range = bb_upper_val - bb_lower_val
        bb_position = (current_price - bb_lower_val) / bb_range if bb_range else 0.5

    return {
        "ticker": ticker,
        "current_price": current_price,
        "rsi": {"value": rsi, "signal": rsi_signal},
        "macd": {
            "macd": macd_val,
            "signal": macd_sig,
            "histogram": macd_hist,
            "crossover": macd_crossover,
        },
        "bollinger_bands": {
            "upper": bb_upper_val,
            "middle": bb_mid_val,
            "lower": bb_lower_val,
            "price_position": bb_position,  # 0=at lower, 1=at upper
        },
        "atr": safe(last.get("ATRr_14")),
        "ema": {
            "ema20": ema20,
            "ema50": ema50,
            "price_above_ema20": current_price > ema20 if current_price and ema20 else None,
            "price_above_ema50": current_price > ema50 if current_price and ema50 else None,
            "golden_cross": golden_cross,
            "death_cross": death_cross,
        },
        "obv": safe(last.get("OBV")),
        "stochastic": {
            "k": safe(last[stoch_k]) if stoch_k else None,
            "d": safe(last[stoch_d]) if stoch_d else None,
        },
        "trend_summary": _summarize_trend(rsi, macd_hist, bb_position, golden_cross, death_cross),
    }


def _summarize_trend(rsi, macd_hist, bb_position, golden_cross, death_cross) -> str:
    bullish_signals = 0
    bearish_signals = 0

    if rsi:
        if rsi < 35:
            bullish_signals += 1
        elif rsi > 65:
            bearish_signals += 1

    if macd_hist:
        if macd_hist > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1

    if bb_position is not None:
        if bb_position < 0.25:
            bullish_signals += 1
        elif bb_position > 0.75:
            bearish_signals += 1

    if golden_cross:
        bullish_signals += 2
    if death_cross:
        bearish_signals += 2

    if bullish_signals > bearish_signals + 1:
        return "bullish"
    elif bearish_signals > bullish_signals + 1:
        return "bearish"
    return "neutral"
