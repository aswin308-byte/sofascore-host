from fastapi import FastAPI
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="API-Tennis Proxy - GOD MODE Ready")

# === CONFIGURATION ===
API_BASE = os.getenv("API_TENNIS_BASE", "https://api.api-tennis.com/tennis")
API_KEY = os.getenv("API_TENNIS_KEY", "0fe87cdf50ab7e026c1d82c5d9818e8214c97f8fdf8437c38088fb2fedef28fb")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "source": "api-tennis",
        "note": "Using Railway environment variables"
    }

@app.get("/event/{event_id}")
async def get_event(event_id: str):
    """
    Returns full match data + point-by-point + current game score (15-30-40 etc.)
    """
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            params = {
                "APIkey": API_KEY,
                "match_key": event_id,
                "method": "get_match"   # ← change this if your docs use a different method name
            }

            resp = await client.get(API_BASE, params=params)

            if resp.status_code == 200:
                data = resp.json()
                return JSONResponse(content={
                    "success": True,
                    "pbp": data.get("pointbypoint", []),
                    "scores": data.get("scores", {}),
                    "current_game": data.get("current_game", {}),
                    "raw": data,
                    "source": "api-tennis"
                })
            else:
                return JSONResponse(
                    status_code=resp.status_code,
                    content={"error": resp.text}
                )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
async def root():
    return {"message": "API-Tennis Proxy ready. Use /event/{match_key}"}
