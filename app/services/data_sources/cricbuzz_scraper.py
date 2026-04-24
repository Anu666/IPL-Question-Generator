# Cricbuzz scraper
# Best-effort scraper for supplementary IPL context from Cricbuzz.
# Every function is wrapped in try/except and returns empty data on failure.
# Cricbuzz may block bots or change HTML — graceful degradation is intentional.

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 8.0

# Map of common IPL team name keywords to Cricbuzz team slugs
# Used to build H2H URLs like /cricket-team/{slug}/vs/{slug}/head-to-head
_TEAM_SLUG_MAP: dict[str, str] = {
    "mumbai indians": "mumbai-indians-5",
    "chennai super kings": "chennai-super-kings-8",
    "royal challengers": "royal-challengers-bangalore-9",
    "delhi capitals": "delhi-capitals-61",
    "kolkata knight riders": "kolkata-knight-riders-10",
    "sunrisers hyderabad": "sunrisers-hyderabad-62",
    "punjab kings": "punjab-kings-64",
    "rajasthan royals": "rajasthan-royals-7",
    "gujarat titans": "gujarat-titans-4343",
    "lucknow super giants": "lucknow-super-giants-6904",
}


def _resolve_slug(team_name: str) -> str | None:
    name_lower = team_name.lower()
    for keyword, slug in _TEAM_SLUG_MAP.items():
        if keyword in name_lower or name_lower in keyword:
            return slug
    return None


async def fetch_head_to_head(team1: str, team2: str) -> dict:
    """
    Attempt to scrape H2H stats between two IPL teams from Cricbuzz.
    Returns {} on any failure.
    """
    try:
        slug1 = _resolve_slug(team1)
        slug2 = _resolve_slug(team2)
        if not slug1 or not slug2:
            return {}

        url = f"https://www.cricbuzz.com/cricket-team/{slug1}/vs/{slug2}/head-to-head"

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                return {}

            soup = BeautifulSoup(resp.content, "lxml")

            # Extract overall H2H summary text if present
            summary_blocks = soup.select("div.cb-col.cb-col-100")
            stats: dict = {}

            for block in summary_blocks[:10]:
                text = block.get_text(separator=" ", strip=True)
                if team1.lower()[:4] in text.lower() or team2.lower()[:4] in text.lower():
                    if any(kw in text.lower() for kw in ["won", "matches", "series"]):
                        stats["summary_snippet"] = text[:300]
                        break

            return stats

    except Exception:
        return {}


async def fetch_match_headlines(team1: str, team2: str) -> list[str]:
    """
    Scrape recent news headlines from Cricbuzz homepage mentioning either team.
    Returns [] on any failure.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get("https://www.cricbuzz.com/cricket-news/ipl", headers=HEADERS)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.content, "lxml")
            headlines = [a.get_text(strip=True) for a in soup.select("h2.cb-nws-hdln, a.cb-nws-hdln-ancr")]
            t1 = team1.lower()[:4]
            t2 = team2.lower()[:4]
            relevant = [h for h in headlines if t1 in h.lower() or t2 in h.lower()]
            return relevant[:6]

    except Exception:
        return []
