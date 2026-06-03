"""
Episodic memory using SQLite.
Stores completed decision cycles and CVRF-extracted investment beliefs.
Inspired by FINCON's manager-exclusive episodic memory.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.config import SQLITE_DB_PATH


def _get_conn() -> sqlite3.Connection:
    Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,
            confidence REAL,
            explanation TEXT,
            debate_winner TEXT,
            risk_flag INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS beliefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            belief TEXT NOT NULL,
            relevant_agents TEXT,
            source_decision_ids TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_ticker ON decisions(ticker);
        CREATE INDEX IF NOT EXISTS idx_beliefs_ticker ON beliefs(ticker);
    """)
    conn.commit()


def store_decision(
    ticker: str,
    action: str,
    confidence: float,
    explanation: str,
    debate_winner: Optional[str] = None,
    risk_flag: bool = False,
) -> int:
    """Persists a completed decision. Returns the row ID."""
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO decisions
           (ticker, action, confidence, explanation, debate_winner, risk_flag, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker, action, confidence, explanation, debate_winner, int(risk_flag),
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_recent_decisions(ticker: str, limit: int = 10) -> list[dict]:
    """Returns the most recent N decisions for a ticker."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM decisions WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
        (ticker, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def store_belief(
    ticker: Optional[str],
    belief: str,
    relevant_agents: list[str],
    source_decision_ids: list[int],
):
    """Stores a CVRF-extracted investment belief."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO beliefs
           (ticker, belief, relevant_agents, source_decision_ids, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            ticker,
            belief,
            json.dumps(relevant_agents),
            json.dumps(source_decision_ids),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_beliefs(ticker: Optional[str] = None, limit: int = 20) -> list[dict]:
    """
    Returns recent investment beliefs.
    If ticker is None, returns global beliefs (not ticker-specific).
    """
    conn = _get_conn()
    if ticker:
        rows = conn.execute(
            "SELECT * FROM beliefs WHERE ticker = ? OR ticker IS NULL ORDER BY created_at DESC LIMIT ?",
            (ticker, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM beliefs WHERE ticker IS NULL ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["relevant_agents"] = json.loads(d.get("relevant_agents") or "[]")
        d["source_decision_ids"] = json.loads(d.get("source_decision_ids") or "[]")
        results.append(d)
    return results


def get_all_decisions(limit: int = 50) -> list[dict]:
    """Returns the most recent decisions across all tickers."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
