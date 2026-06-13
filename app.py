from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Tennis API Proxy - Livescore-First + Self-Diagnosing")

API_BASE = "https://api.api-tennis.com/tennis"
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")


def find_best_match(matches, player1, player2):
    p1 = player1.lower()
    p2 = player2.lower()
    live_matches = []
    other_matches = []
    for m in matches:
        f = m.get("event_first_player", "").lower()
        s = m.get("event_second_player", "").lower()
        if (p1 in f or p1 in s) and (p2 in f or p2 in s):
            if m.get("event_live") == "1":
                live_matches.append(m)
            else:
                other_matches.append(m)
    return live_matches[0] if live_matches else (other_matches[0] if other_matches else None)


def shape_match(m, extra=None):
    out = {
        "is_live": m.get("event_live") == "1",
        "status": m.get("event_status"),
        "event_date": m.get("event_date"),
        "event_time": m.get("event_time"),
        "current_score": m.get("event_final_result") or m.get("event_game_result"),
        "micro_score": m.get("event_game_result"),
        "serve": m.get("event_serve"),
        "pbp_count": len(m.get("pointbypoint", []) or []),
        "pbp": m.get("pointbypoint", []),
        "scores": m.get("scores", []),
    }
    if extra:
        out.update(extra)
    return out


@app.get("/health")
async def health():
    return {"status": "ok", "source": "livescore-first", "note": "Smart search + livescore priority + self-diagnosing output"}


@app.get("/godmode")
async def godmode(player1: str = "Honda", player2: str = "Magadan", date_start: str = "2026-06-12", date_stop: str = "2026-06-15"):
    """
    Find a match by player names. Tries get_livescore first (for matches in progress),
    then falls back to get_fixtures across the date range.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Try livescore first — only returns matches the feed considers live.
        ls = await client.get(API_BASE, params={"method": "get_livescore", "APIkey": API_KEY})
        ls_data = ls.json() if ls.status_code == 200 else {}
        ls_matches = ls_data.get("result", []) if isinstance(ls_data, dict) else []
        match = find_best_match(ls_matches, player1, player2)
        source = "livescore"

        # 2. Fall back to fixtures across the date range.
        if not match:
            fx = await client.get(API_BASE, params={
                "method": "get_fixtures", "APIkey": API_KEY,
                "date_start": date_start, "date_stop": date_stop,
            })
            if fx.status_code != 200:
                return JSONResponse(status_code=fx.status_code, content={"error": fx.text})
            fx_data = fx.json() if fx.status_code == 200 else {}
            fx_matches = fx_data.get("result", []) if isinstance(fx_data, dict) else []
            match = find_best_match(fx_matches, player1, player2)
            source = "fixtures"

    if match:
        return JSONResponse(content={
            "success": True,
            "data_source": source,
            "match_key": match.get("event_key"),
            **shape_match(match, {"full_match": match}),
        })
    return JSONResponse(content={
        "success": False,
        "message": "Match not found in livescore or fixtures for this date range.",
    })


@app.get("/event/{match_key}")
async def event(match_key: str):
    params = {"method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key}
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(API_BASE, params=params)
        data = resp.json() if resp.status_code == 200 else {}
        matches = data.get("result", []) if isinstance(data, dict) else []
        m = matches[0] if matches else {}
        return JSONResponse(content={
            "success": bool(m),
            "match_key": match_key,
            **shape_match(m),
        })


@app.get("/live/{match_key}")
async def live_match(match_key: str):
    """
    Try get_livescore first; fall back to get_fixtures.
    Reports what each source returned so failures are self-diagnosing.
    """
    async with httpx.AsyncClient(timeout=25.0) as client:
        ls = await client.get(API_BASE, params={
            "method": "get_livescore", "APIkey": API_KEY, "match_key": match_key,
        })
        ls_data = ls.json() if ls.status_code == 200 else {}
        ls_matches = ls_data.get("result", []) if isinstance(ls_data, dict) else []

        fx = await client.get(API_BASE, params={
            "method": "get_fixtures", "APIkey": API_KEY, "match_key": match_key,
        })
        fx_data = fx.json() if fx.status_code == 200 else {}
        fx_matches = fx_data.get("result", []) if isinstance(fx_data, dict) else []

    m = ls_matches[0] if ls_matches else (fx_matches[0] if fx_matches else {})
    source = "livescore" if ls_matches else ("fixtures" if fx_matches else "none")

    return JSONResponse(content={
        "success": bool(m),
        "data_source": source,
        "livescore_returned": len(ls_matches),
        "fixtures_returned": len(fx_matches),
        "match_key": match_key,
        **shape_match(m),
    })


@app.get("/")
async def root():
    return {"message": "Livescore-first proxy ready. Use /godmode or /live/{match_key}"}
