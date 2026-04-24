# Match data service
# Aggregates data from all sources (cricapi + Cricbuzz) into a single
# context dict that gets sent to Gemini for question generation.

import asyncio

from app.services.data_sources.cricapi_service import fetch_series_context
from app.services.data_sources.cricbuzz_scraper import fetch_head_to_head, fetch_match_headlines


async def gather_match_context(team1: str, team2: str, date: str) -> dict:
    """
    Fetch and merge pre-match context from all data sources.
    Runs all network calls concurrently for speed.
    Returns a dict that is passed directly into the Gemini prompt.
    """
    # Run all sources concurrently — failures in one don't block others
    cricapi_data, h2h_scrape, headlines = await asyncio.gather(
        fetch_series_context(team1, team2),
        fetch_head_to_head(team1, team2),
        fetch_match_headlines(team1, team2),
        return_exceptions=True,
    )

    # Replace any exceptions with empty fallbacks
    if isinstance(cricapi_data, Exception):
        cricapi_data = {}
    if isinstance(h2h_scrape, Exception):
        h2h_scrape = {}
    if isinstance(headlines, Exception):
        headlines = []

    return {
        "match": {
            "team1": team1,
            "team2": team2,
            "date": date,
        },
        "cricapi": cricapi_data,
        "cricbuzz_h2h": h2h_scrape,
        "recent_headlines": headlines,
    }
