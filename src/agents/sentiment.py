"""
Sentiment Analyst Agent.
Aggregates news data and uses LLM to score market sentiment.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.tools.news_tool import get_news
import yfinance as yf


class SentimentOutput(BaseModel):
    overall_sentiment: str         # 'very_bullish' | 'bullish' | 'neutral' | 'bearish' | 'very_bearish'
    news_sentiment: str
    social_sentiment: str
    sentiment_score: float         # -1.0 (very bearish) to +1.0 (very bullish)
    key_themes: list[str]          # top 3 narrative themes from news/social
    catalyst_events: list[str]     # upcoming events mentioned (earnings, product launches, etc.)
    summary: str
    confidence: float


SYSTEM_PROMPT = """You are a market sentiment analyst specializing in qualitative signal extraction from financial news.
Analyze the provided news articles for the given stock.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "overall_sentiment": "<very_bullish|bullish|neutral|bearish|very_bearish>",
  "news_sentiment": "<very_bullish|bullish|neutral|bearish|very_bearish>",
  "social_sentiment": "unavailable",
  "sentiment_score": <-1.0 to 1.0>,
  "key_themes": ["<theme1>", "<theme2>", "<theme3>"],
  "catalyst_events": ["<event1>", "<event2>"],
  "summary": "<2-3 sentence sentiment summary>",
  "confidence": <0.0-1.0>
}}"""


def sentiment_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    beliefs = state.get("investment_beliefs", [])

    # Get company name for better news search
    try:
        t = yf.Ticker(ticker)
        company_name = (t.info or {}).get("shortName", ticker)
    except Exception:
        company_name = ticker

    news_data = get_news(ticker, company_name=company_name, days=7, max_articles=10)

    news_texts = "\n".join([
        f"[{a.get('source', '')}] {a.get('title', '')} — {a.get('description', '')[:200]}"
        for a in news_data.get("articles", [])
    ]) or "No news articles found."

    belief_context = ""
    if beliefs:
        belief_context = "\n\nRelevant investment beliefs:\n" + "\n".join(
            f"- {b}" for b in beliefs[:3]
        )

    user_msg = f"""Ticker: {ticker} ({company_name})

Recent News Articles:
{news_texts}
{belief_context}

Provide your sentiment analysis as JSON."""

    llm = get_llm("analyst")
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        validated = SentimentOutput(**parsed)
        return {"sentiment_analysis": validated.model_dump()}
    except (json.JSONDecodeError, ValidationError) as e:
        retry_msg = f"Invalid response: {e}. Output ONLY the JSON object."
        response2 = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
            HumanMessage(content=retry_msg),
        ])
        raw2 = response2.content.strip()
        if raw2.startswith("```"):
            raw2 = raw2.split("```")[1]
            if raw2.startswith("json"):
                raw2 = raw2[4:]
        try:
            validated2 = SentimentOutput(**json.loads(raw2.strip()))
            return {"sentiment_analysis": validated2.model_dump()}
        except Exception as e2:
            return {
                "sentiment_analysis": {},
                "agent_errors": [f"sentiment_agent: {e2}"],
            }
