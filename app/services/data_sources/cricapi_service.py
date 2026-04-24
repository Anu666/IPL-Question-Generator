# CricAPI service
# Fetches IPL match data from cricapi.com (https://cricapi.com).
# Free tier: ~100 calls/day. Each question-generate request uses 2 calls max.

import httpx

from app.core.config import settings

BASE_URL = "https://api.cricapi.com/v1"
TIMEOUT = 10.0


def _parse_winner(status: str, team_name_lower: str) -> str:
    """Return 'W', 'L', or 'NR' for a match status string."""
    s = status.lower()
    if "won" in s:
        return "W" if team_name_lower[:6] in s else "L"
    if "no result" in s or "abandon" in s or "cancelled" in s:
        return "NR"
    return "NR"


async def _get(endpoint: str, params: dict) -> dict:
    """Internal helper: makes a GET request to cricapi.com."""
    params["apikey"] = settings.CRICAPI_KEY
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()


async def fetch_current_ipl_series_id() -> str | None:
    """Find the ID of the current or most recent IPL series."""
    try:
        data = await _get("series", {"offset": 0, "search": "Indian Premier League"})
        series_list = data.get("data", [])
        ipl_series = [
            s for s in series_list
            if "Indian Premier League" in s.get("name", "") or "IPL" in s.get("name", "")
        ]
        if ipl_series:
            ipl_series.sort(key=lambda x: x.get("startDate", ""), reverse=True)
            return ipl_series[0]["id"]
    except Exception:
        pass
    return None


async def fetch_series_context(team1: str, team2: str) -> dict:
    """
    Fetch H2H match history and individual team form from the current IPL series.
    Returns a structured dict ready to pass into the Gemini prompt.
    """
    result: dict = {
        "source": "cricapi.com",
        "series": None,
        "head_to_head": {},
        "team1_form": {},
        "team2_form": {},
    }

    try:
        series_id = await fetch_current_ipl_series_id()
        if not series_id:
            return result

        data = await _get("series_info", {"id": series_id})
        series_info = data.get("data", {})
        result["series"] = series_info.get("info", {}).get("name")

        match_list: list[dict] = series_info.get("matchList", [])
        t1 = team1.lower()
        t2 = team2.lower()

        h2h_matches = []
        t1_matches = []
        t2_matches = []

        for match in match_list:
            name = match.get("name", "").lower()
            status = match.get("status", "")
            date = match.get("date", "")
            venue = match.get("venue", "")

            involves_t1 = t1 in name
            involves_t2 = t2 in name

            entry = {"name": match.get("name"), "date": date, "venue": venue, "status": status}

            if involves_t1 and involves_t2:
                h2h_matches.append(entry)
            if involves_t1:
                t1_matches.append(entry)
            if involves_t2:
                t2_matches.append(entry)

        result["head_to_head"] = {
            "total_matches_this_season": len(h2h_matches),
            "recent": h2h_matches[-5:],
            "wins_this_season": {
                team1: sum(1 for m in h2h_matches if _parse_winner(m["status"], t1) == "W"),
                team2: sum(1 for m in h2h_matches if _parse_winner(m["status"], t2) == "W"),
            },
        }

        def build_form(matches: list[dict], team_lower: str) -> list[str]:
            return [_parse_winner(m["status"], team_lower) for m in matches if m["status"]]

        result["team1_form"] = {
            "team": team1,
            "matches_played_this_season": len(t1_matches),
            "recent_form": build_form(t1_matches[-8:], t1),
            "recent": t1_matches[-5:],
        }
        result["team2_form"] = {
            "team": team2,
            "matches_played_this_season": len(t2_matches),
            "recent_form": build_form(t2_matches[-8:], t2),
            "recent": t2_matches[-5:],
        }

    except Exception:
        # Return whatever we collected so far — Gemini handles missing data gracefully
        pass

    return result
