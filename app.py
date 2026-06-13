from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="API-Tennis Full Proxy - GOD MODE Ready")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

@app.get("/health")
async def health():
    return {"status": "ok", "source": "api-tennis-full", "features": "livescore + fixtures + match + PBP"}

@app.get("/livescore")
async def livescore(tournament: str = None):
    params = {"method": "get_livescore", "APIkey": API_KEY}
    if tournament:
        params["tournament_key"] = tournament  # add if known
    return await call_api(params)

@app.get("/fixtures")
async def fixtures(date_start: str = "2026-06-12", date_stop: str = "2026-06-14"):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "date_start": date_start, "date_stop": date_stop}
    return await call_api(params)

@app.get("/event/{match_key}")
async def event(match_key: str):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key}
    return await call_api(params)

async def call_api(params):
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return JSONResponse(content={
                "success": True,
                "matches": data.get("results", data),
                "pbp_example": "See 'pointbypoint' in response",
                "source": "api-tennis-full"
            })
        return JSONResponse(status_code=resp.status_code, content={"error": resp.text})

@app.get("/")
async def root():
    return {
        "message": "Full API-Tennis Proxy ready",
        "usage": "/livescore | /fixtures | /event/{match_key}"
    }
