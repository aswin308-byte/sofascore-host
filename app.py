from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import asyncio

app = FastAPI(title="Sofascore JSON Proxy - Light & Fast")

SOFASCORE_BASE = "https://www.sofascore.com/api/v1/event"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get main event data (score, status, etc.)
            event_resp = await client.get(f"{SOFASCORE_BASE}/{event_id}")
            event_data = event_resp.json() if event_resp.status_code == 200 else {}

            # Get incidents / PBP
            inc_resp = await client.get(f"{SOFASCORE_BASE}/{event_id}/incidents")
            incidents = inc_resp.json().get("incidents", []) if inc_resp.status_code == 200 else []

        response = {
            "event": event_data,
            "incidents": incidents,
            "incidents_count": len(incidents),
            "source": "sofascore"
        }

        # Optional clean PBP list
        if clean_pbp:
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
