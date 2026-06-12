from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup
import re
import asyncio

app = FastAPI(title="Sofascore Hybrid Proxy - Best Version")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
}

SOFASCORE_API = "https://www.sofascore.com/api/v1/event"
SOFASCORE_PAGE = "https://www.sofascore.com/tennis/match"

async def fetch_from_api(client: httpx.AsyncClient, event_id: int):
    """Try Sofascore API first"""
    try:
        api_url = f"{SOFASCORE_API}/{event_id}"
        resp = await client.get(api_url)
        event_data = resp.json() if resp.status_code == 200 else {}

        inc_resp = await client.get(f"{api_url}/incidents")
        incidents = inc_resp.json().get("incidents", []) if inc_resp.status_code == 200 else []

        return event_data, incidents
    except Exception:
        return {}, []

async def fetch_from_page(client: httpx.AsyncClient, event_id: int):
    """Fallback: scrape Sofascore match page"""
    try:
        page_url = f"{SOFASCORE_PAGE}/placeholder/{event_id}"
        resp = await client.get(page_url)
        if resp.status_code != 200:
            return {}, []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find current score text
        score_elements = soup.find_all(string=re.compile(r"\d+\s*[-–]\s*\d+"))
        current_score = score_elements[0].strip() if score_elements else "N/A"

        # Try to extract some PBP-like text (basic)
        pbp_text = ""
        pbp_div = soup.find("div", string=re.compile(r"point|game|set", re.I))
        if pbp_div:
            pbp_text = pbp_div.get_text(strip=True)[:200]

        event_data = {
            "live_score_text": current_score,
            "pbp_text_from_page": pbp_text,
            "note": "Data from page fallback"
        }

        return event_data, []
    except Exception:
        return {}, []

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "hybrid-api-fallback"}

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        async with httpx.AsyncClient(timeout=25.0, headers=HEADERS, follow_redirects=True) as client:
            # Step 1: Try API first
            event_data, incidents = await fetch_from_api(client, event_id)

            # Step 2: If no incidents, fallback to page scraping
            if not incidents:
                page_data, _ = await fetch_from_page(client, event_id)
                event_data.update(page_data)
                incidents = []  # page fallback currently gives limited PBP

            response = {
                "event": event_data,
                "incidents": incidents,
                "incidents_count": len(incidents),
                "source": "sofascore-hybrid"
            }

            # Optional clean PBP list
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
