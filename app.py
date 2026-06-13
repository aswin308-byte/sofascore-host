from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Smart Tennis API Proxy - Fresh Score + Best PBP (GOD MODE Ready)")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

def find_match_by_players(matches, player1, player2):
    """Smart filter: find match by player names, prefer live ones"""
    player1_lower = player1.lower()
    player2_lower = player2.lower()
    live_matches = []
    other_matches = []
    
    for m in matches:
        first = m.get("event_first_player", "").lower()
        second = m.get("event_second_player", "").lower()
        if (player1_lower in first or player1_lower in second) and (player2_lower in first or player2_lower in second):
            if m.get("event_live") == "1":
                live_matches.append(m)
            else:
                other_matches.append(m)
    
    # Prefer live, then most recent
    if live_matches:
        return live_matches[0]
    if other_matches:
        return other_matches[0]
    return None

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "source": "smart-tennis-api",
        "features": "auto match discovery by name + live priority + full PBP + micro score"
    }

@app.get("/godmode")
async def godmode(player1: str = "Honda", player2: str = "Magadan", date_start: str = "2026-06-12", date_stop: str = "2026-06-15"):
    """Smart search: finds match_key + returns fresh score + best PBP"""
    params = {
        "method": "get_fixtures",
        "APIkey": API_KEY,
        "date_start": date_start,
        "date_stop": date_stop
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(API_BASE, params=params)
            if resp.status_code != 200:
                return JSONResponse(status_code=resp.status_code, content={"error": resp.text})
            
            data = resp.json()
            matches = data.get("result", []) if isinstance(data, dict) else []
            
            match = find_match_by_players(matches, player1, player2)
            
            if match:
                return JSONResponse(content={
                    "success": True,
                    "match_key": match.get("event_key"),
                    "is_live": match.get("event_live") == "1",
                    "current_score": match.get("event_final_result") or match.get("event_game_result"),
                    "micro_score": match.get("event_game_result"),
                    "status": match.get("event_status"),
                    "serve": match.get("event_serve"),
                    "pbp": match.get("pointbypoint", []),
                    "full_match": match,  # Full object for debugging
                    "tip": "Use /event/{match_key} for even fresher details if needed"
                })
            else:
                return JSONResponse(content={
                    "success": False,
                    "message": f"No match found for {player1} vs {player2} in date range. Try widening dates or check /fixtures directly.",
                    "matches_found": len(matches)
                })
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/event/{match_key}")
async def get_event(match_key: str):
    """Get full fresh details + best PBP for a specific match"""
    params = {
        "method": "get_fixtures",
        "APIkey": API_KEY,
        "match_key": match_key
    }
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            resp = await client.get(API_BASE, params=params)
            if resp.status_code != 200:
                return JSONResponse(status_code=resp.status_code, content={"error": resp.text})
            
            data = resp.json()
            matches = data.get("result", []) if isinstance(data, dict) else []
            match = matches[0] if matches else {}
            
            return JSONResponse(content={
                "success": True,
                "match_key": match_key,
                "is_live": match.get("event_live") == "1",
                "current_score": match.get("event_final_result") or match.get("event_game_result"),
                "micro_score": match.get("event_game_result"),
                "status": match.get("event_status"),
                "serve": match.get("event_serve"),
                "pbp": match.get("pointbypoint", []),
                "scores": match.get("scores", []),
                "full_match": match
            })
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
async def root():
    return {
        "message": "Smart Tennis API Proxy Ready",
        "usage": {
            "auto_find": "/godmode?player1=Honda&player2=Magadan",
            "specific": "/event/{match_key}"
        }
    }
