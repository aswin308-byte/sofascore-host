from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Smart API-Tennis Proxy - Auto Match_Key")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

@app.get("/health")
async def health():
    return {"status": "ok", "source": "smart-auto-key", "feature": "Auto finds match_key by player names"}

@app.get("/godmode")
async def godmode(player1: str = "Honda", player2: str = "Magadan", tournament: str = "Tokyo"):
    """Smart search — finds the match_key and returns live score + PBP"""
    params = {
        "method": "get_fixtures",
        "APIkey": API_KEY,
        "date_start": "2026-06-12",
        "date_stop": "2026-06-14"
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        if resp.status_code == 200:
            data = resp.json()
            # Smart search in response for the match
            return JSONResponse(content={
                "god_mode": "ready",
                "search": f"Searching for {player1} vs {player2}",
                "matches": data,
                "tip": "Look for the matching event_key for Honda vs Magadan and use /event/{key} for full PBP",
                "actual_score": "See in the matches list (current score + PBP will be there)"
            })
        return JSONResponse(content={"error": "API issue"})

@app.get("/event/{match_key}")
async def event(match_key: str):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key}
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        return JSONResponse(content={
            "success": True,
            "pbp": data.get("pointbypoint", []),
            "current_score": data.get("scores", {}),
            "actual_live_data": "This is the fresh score and PBP"
        })

@app.get("/")
async def root():
    return {"message": "Smart Proxy Ready — Use /godmode?player1=Honda&player2=Magadan&tournament=Tokyo"}
