"""
Fetches and extracts key sections from SEC 10-K/10-Q filings via EDGAR REST API.
Uses sec-edgar-downloader for file retrieval and regex extraction for sections.
All free — only requires a contact email in SEC_USER_AGENT.
"""
import os
import re
import json
import requests
from pathlib import Path
from src.config import SEC_USER_AGENT, SEC_FILINGS_DIR


EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=10-K"
EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=5&search_text="


def get_cik(ticker: str) -> str | None:
    """Maps ticker → CIK using EDGAR company search."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-K"
    headers = {"User-Agent": SEC_USER_AGENT}
    try:
        resp = requests.get(
            f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=10&search_text=&action=getcompany&output=atom",
            headers=headers, timeout=10
        )
        match = re.search(r"CIK=(\d+)", resp.text)
        if match:
            return match.group(1).zfill(10)
    except Exception:
        pass
    return None


def get_latest_10k_summary(ticker: str) -> dict:
    """
    Fetches the latest 10-K filing for `ticker` and extracts key sections:
    - Business description
    - Risk factors (first 2000 chars)
    - MD&A highlights
    Returns structured dict.
    """
    headers = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    cik = get_cik(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found for ticker"}

    # Get filing list
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = requests.get(submissions_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"ticker": ticker, "error": f"Failed to fetch submissions: {e}"}

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    # Find most recent 10-K
    ten_k_idx = next((i for i, f in enumerate(forms) if f == "10-K"), None)
    if ten_k_idx is None:
        return {"ticker": ticker, "error": "No 10-K filing found"}

    accession = accessions[ten_k_idx].replace("-", "")
    filing_date = dates[ten_k_idx]

    # Fetch the filing index
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{accessions[ten_k_idx]}-index.htm"
    try:
        resp = requests.get(index_url, headers=headers, timeout=15)
        # Find the main 10-K document link
        doc_match = re.search(r'href="(/Archives/edgar/data/[^"]+\.htm)"', resp.text)
        if not doc_match:
            return {"ticker": ticker, "error": "Could not find 10-K document URL"}
        doc_url = "https://www.sec.gov" + doc_match.group(1)
    except Exception as e:
        return {"ticker": ticker, "error": f"Failed to fetch filing index: {e}"}

    # Fetch the actual 10-K document
    try:
        resp = requests.get(doc_url, headers=headers, timeout=30)
        text = re.sub(r"<[^>]+>", " ", resp.text)  # strip HTML tags
        text = re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        return {"ticker": ticker, "error": f"Failed to fetch 10-K document: {e}"}

    return {
        "ticker": ticker,
        "filing_date": filing_date,
        "accession_number": accessions[ten_k_idx],
        "business_description": _extract_section(text, "Item 1", "Item 1A", max_chars=3000),
        "risk_factors": _extract_section(text, "Item 1A", "Item 1B", max_chars=2000),
        "mda_highlights": _extract_section(text, "Item 7", "Item 7A", max_chars=3000),
        "source": doc_url,
    }


def _extract_section(text: str, start_marker: str, end_marker: str, max_chars: int = 2000) -> str:
    """Extracts text between two section markers."""
    pattern = rf"{re.escape(start_marker)}[.\s](.+?){re.escape(end_marker)}"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()[:max_chars]
    # fallback: just find the start marker
    idx = text.lower().find(start_marker.lower())
    if idx != -1:
        return text[idx:idx + max_chars]
    return ""
