"""
Fetches Reddit sentiment from finance-related subreddits via PRAW (free API).
Falls back gracefully if credentials are not set.
"""
from src.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT


FINANCE_SUBREDDITS = ["investing", "stocks", "StockMarket", "wallstreetbets", "SecurityAnalysis"]


def get_reddit_sentiment(ticker: str, max_posts: int = 20) -> dict:
    """
    Searches for recent posts mentioning the ticker across finance subreddits.
    Returns posts with title, score, num_comments, and created_at.
    """
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return {
            "ticker": ticker,
            "posts": [],
            "sentiment_summary": "unavailable — Reddit credentials not set",
            "error": "REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not configured",
        }

    try:
        import praw
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

        posts = []
        for sub_name in FINANCE_SUBREDDITS:
            sub = reddit.subreddit(sub_name)
            for post in sub.search(ticker, limit=max_posts // len(FINANCE_SUBREDDITS) + 1, sort="new"):
                posts.append({
                    "title": post.title,
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "subreddit": sub_name,
                    "created_utc": post.created_utc,
                    "selftext_snippet": post.selftext[:300] if post.selftext else "",
                })

        posts = sorted(posts, key=lambda x: x["score"], reverse=True)[:max_posts]

        avg_score = sum(p["score"] for p in posts) / len(posts) if posts else 0
        high_engagement = [p for p in posts if p["num_comments"] > 50]

        return {
            "ticker": ticker,
            "posts": posts,
            "avg_score": avg_score,
            "high_engagement_posts": len(high_engagement),
            "sentiment_summary": _score_to_sentiment(avg_score, len(posts)),
        }

    except Exception as e:
        return {"ticker": ticker, "posts": [], "error": str(e), "sentiment_summary": "error"}


def _score_to_sentiment(avg_score: float, num_posts: int) -> str:
    if num_posts == 0:
        return "no data"
    if avg_score > 500:
        return "very bullish"
    elif avg_score > 100:
        return "bullish"
    elif avg_score > 20:
        return "slightly bullish"
    elif avg_score > -20:
        return "neutral"
    elif avg_score > -100:
        return "slightly bearish"
    return "bearish"
