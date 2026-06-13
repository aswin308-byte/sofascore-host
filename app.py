from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Ultimate Tennis Proxy - Smart Match_Key + Livescore Priority")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

def calculate_confidence(match, player1, player2):
    score = 0
    f = match.get("event_first_player", "").lower()
    s = match.get("event_second_player", "").lower()
    p1, p2 = player1.lower(), player2.lower()
    if p1 in f or p1 in s: score += 40
    if p2 in f or p2 in s: score += 40
    if "live" in match.get("event_status", "").lower() or match.get("event_live") == "1": score += 20
    return min(score, 100)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "ultimate-smart", "note": "Better name matching + confidence + livescore priority"}

@app.get("/godmode")
async def godmode(
    player1: str, 
    player2: str, 
    tournament: str = None,
    all_candidates: bool = False
):
    # Try livescore first (best for live data)
    params = {"method": "get_livescore", "APIkey": API_KEY}
    if tournament:
        params["tournament_key"] = tournament

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        matches = data.get("result", []) if isinstance(data, dict) else []

        p1 = player1.lower()
        p2 = player2.lower()

        candidates = []
        for m in matches:
            f = m.get("event_first_player", "").lower()
            s = m.get("event_second_player", "").lower()
            if (p1 in f or p1 in s) and (p2 in f or p2 in s):
                confidence = calculate_confidence(m, player1, player2)
                candidates.append({"match": m, "confidence": confidence})

        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        if candidates:
            best = candidates[0]["match"]
            return JSONResponse(content={
                "success": True,
                "match_key": best.get("event_key"),
                "is_live": best.get("event_live") == "1",
                "current_score": best.get("event_final_result") or best.get("event_game_result") or "-",
                "micro_score": best.get("event_game_result") or "-",
                "status": best.get("event_status"),
                "confidence": candidates[0]["confidence"],
                "pbp": best.get("pointbypoint", []),
                "candidates_found": len(candidates),
                "message": "Best match found with confidence score"
            })

        return JSONResponse(content={"success": False, "message": "Match not found. Try adding tournament parameter."})

@app.get("/live/{match_key}")
async def live(match_key: str):
    params = {"method": "get_livescore", "APIkey": API_KEY, "match_key": match_key}
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        matches = data.get("result", []) if isinstance(data, dict) else []
        m = matches[0] if matches else {}
        
        return JSONResponse(content={
            "success": True,
            "match_key": match_key,
            "is_live": m.get("event_live") == "1",
            "current_score": m.get("event_final_result") or m.get("event_game_result") or "-",
            "micro_score": m.get("event_game_result") or "-",
            "status": m.get("event_status"),
            "pbp": m.get("pointbypoint", []),
            "message": "Fresh live data from get_livescore endpoint (best for PBP)"
        })

@app.get("/")
async def root():
    return {"message": "Ultimate proxy ready. /godmode?player1=Krutykh&player2=Petak or /live/12136243"}
