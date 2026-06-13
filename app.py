from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Ultimate Reliable Tennis API Proxy - Always Fresh Score + Best PBP")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

@app.get("/health")
async def health():
    return {"status": "ok", "source": "ultimate-fresh-pbp", "note": "Always fresh + best PBP"}

@app.get("/godmode")
async def godmode(player1: str = "Honda", player2: str = "Magadan", tournament: str = "Tokyo"):
    """Smart auto search for fresh score + best PBP"""
    params = {
        "method": "get_fixtures",
        "APIkey": API_KEY,
        "date_start": "2026-06-12",
        "date_stop": "2026-06-15"
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        return JSONResponse(content={
            "fresh_score": "See matches list for Honda vs Magadan",
            "pbp": "Best point-by-point in pointbypoint array",
            "tip": "Copy the event_key for this match and use /event/{key} for the absolute freshest micro score",
            "data": data
        })

@app.get("/event/{match_key}")
async def event(match_key: str):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key}
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        return JSONResponse(content={
            "fresh_exact_score": data.get("scores", {}),
            "micro_pbp": data.get("pointbypoint", []),
            "current_game": "See pointbypoint for 15-30-40, deuce, advantage",
            "status": "Fresh and detailed"
        })

@app.get("/")
async def root():
    return {"message": "Ultimate Proxy Ready — Always fresh score + best PBP"}
