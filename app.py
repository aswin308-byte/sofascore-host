from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Smart API-Tennis Proxy - GOD MODE Auto")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

@app.get("/health")
async def health():
    return {"status": "ok", "source": "smart-api-tennis", "god_mode": "ready"}

@app.get("/godmode")
async def godmode(player1: str = "Honda", player2: str = "Magadan", tournament: str = "Tokyo"):
    # Smart search for match
    params = {
        "method": "get_fixtures",
        "APIkey": API_KEY,
        "date_start": "2026-06-12",
        "date_stop": "2026-06-14"
    }
    data = await call_api(params)
    # In response, find the match by player names
    return JSONResponse(content={
        "god_mode_ready": True,
        "tip": "Look for " + player1 + " vs " + player2 + " in the matches list and copy event_key",
        "matches": data,
        "pbp": "See pointbypoint in the matching match",
        "current_score": "See scores in the matching match"
    })

async def call_api(params):
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}

@app.get("/event/{match_key}")
async def event(match_key: str):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key}
    return await call_api(params)

@app.get("/")
async def root():
    return {"message": "Smart Proxy Ready. Use /godmode?player1=Honda&player2=Magadan&tournament=Tokyo"}
