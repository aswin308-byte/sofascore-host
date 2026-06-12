from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
from bs4 import BeautifulSoup
import re
import asyncio

app = FastAPI(title="Sofascore Proxy - Best Version")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

SOFASCORE_API = "https://www.sofascore.com/api/v1/event"
SOFASCORE_PAGE = "https://www.sofascore.com/tennis/match"

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "best-hybrid"}

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        async with httpx.AsyncClient(timeout=25.0, headers=HEADERS) as client:
            # 1. Try Sofascore API first (fast)
            api_url = f"{SOFASCORE_API}/{event_id}"
            resp = await client.get(api_url)
            event_data = resp.json() if resp.status_code == 200 else {}

            inc_resp = await client.get(f"{api_url}/incidents")
            incidents = inc_resp.json().get("incidents", []) if inc_resp.status_code == 200 else []

            # 2. Fallback: If no incidents, scrape the page
            if not incidents:
                page_url = f"{SOFASCORE_PAGE}/placeholder/{event_id}"
                page_resp = await client.get(page_url)
                if page_resp.status_code == 200:
                    soup = BeautifulSoup(page_resp.text, "html.parser")
                    # Try to extract current score from page (basic)
                    score_text = soup.find(string=re.compile(r"\d+-\d+"))
                    if score_text:
                        event_data["live_score_text"] = score_text.strip()

            response = {
                "event": event_data,
                "incidents": incidents,
                "incidents_count": len(incidents),
                "source": "sofascore"
            }

            # Clean PBP list
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
