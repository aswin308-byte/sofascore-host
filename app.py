from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup
import re
import asyncio

app = FastAPI(title="Sofascore Hybrid Proxy v2 - Upgraded Fallback")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
}

SOFASCORE_API = "https://www.sofascore.com/api/v1/event"
SOFASCORE_PAGE = "https://www.sofascore.com/tennis/match"


async def fetch_from_api(client: httpx.AsyncClient, event_id: int, retries: int = 2):
    """Try Sofascore API with simple retry"""
    for attempt in range(retries):
        try:
            api_url = f"{SOFASCORE_API}/{event_id}"
            resp = await client.get(api_url)
            event_data = resp.json() if resp.status_code == 200 else {}

            inc_resp = await client.get(f"{api_url}/incidents")
            incidents = inc_resp.json().get("incidents", []) if inc_resp.status_code == 200 else []

            if incidents or event_data:
                return event_data, incidents
        except Exception:
            if attempt == retries - 1:
                return {}, []
            await asyncio.sleep(1)
    return {}, []


async def fetch_from_page(client: httpx.AsyncClient, event_id: int):
    """Improved page scraping fallback"""
    try:
        page_url = f"{SOFASCORE_PAGE}/placeholder/{event_id}"
        resp = await client.get(page_url)
        if resp.status_code != 200:
            return {}, []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try multiple ways to find current score
        current_score = "N/A"
        score_text = soup.find(string=re.compile(r"\d+\s*[-–]\s*\d+"))
        if score_text:
            current_score = score_text.strip()

        # Look for set scores (e.g. "Set 3: 3-2")
        set_scores = []
        for tag in soup.find_all(string=re.compile(r"set\s*\d", re.I)):
            set_scores.append(tag.strip())

        # Try to extract recent PBP / incidents text
        pbp_snippets = []
        for tag in soup.find_all(string=re.compile(r"(break|ace|point|game|set|match)", re.I)):
            text = tag.strip()
            if len(text) > 5 and len(text) < 120:
                pbp_snippets.append(text)
        pbp_snippets = pbp_snippets[:8]  # limit

        event_data = {
            "live_score_text": current_score,
            "set_scores_from_page": set_scores,
            "recent_pbp_snippets": pbp_snippets,
            "note": "Data extracted via page fallback"
        }

        return event_data, []
    except Exception:
        return {}, []


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "hybrid-v2-upgraded"}


@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=HEADERS, follow_redirects=True) as client:
            # Step 1: Try API
            event_data, incidents = await fetch_from_api(client, event_id)

            # Step 2: Fallback to page if needed
            if not incidents and not event_data.get("live_score_text"):
                page_data, _ = await fetch_from_page(client, event_id)
                event_data.update(page_data)
                incidents = []

            response = {
                "event": event_data,
                "incidents": incidents,
                "incidents_count": len(incidents),
                "source": "sofascore-hybrid-v2"
            }

            # Optional clean PBP
            if clean_pbp and incidents:
                pbp = []
                for inc in incidents:
                    pbp.append({
                        "time": inc.get("time"),
                        "type": inc.get("incidentType"),
                        "player": inc.get("player", {}).get("name") if inc.get("player") else None,
                        "homeScore": inc.get("homeScore"),
                        "awayScore": inc.get("awayScore"),
                        "description": inc.get("description")
                    })
                response["pbp"] = pbp
                response["pbp_count"] = len(pbp)

            return JSONResponse(content=response)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
