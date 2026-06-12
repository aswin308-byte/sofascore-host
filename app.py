from fastapi import FastAPI
from sofascore_wrapper.api import SofascoreAPI
from fastapi.responses import JSONResponse
import asyncio

app = FastAPI(title="Sofascore JSON Proxy - PBP Enabled")

@app.get("/")
async def root():
    return {
        "status": "Sofascore wrapper running",
        "endpoints": {
            "/event/{event_id}": "Returns full event JSON + 'incidents' (raw PBP)",
            "/event/{event_id}?clean_pbp=true": "Also adds cleaned 'pbp' list"
        }
    }

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        api = SofascoreAPI()
        # 45 second timeout to prevent hanging
        data = await asyncio.wait_for(api.get_event(event_id), timeout=45.0)
        
        response = {"data": data}
        
        # Always expose raw incidents (this is the PBP)
        if "incidents" in data:
            response["incidents"] = data["incidents"]
            response["incidents_count"] = len(data["incidents"])
        
        # Optional clean PBP list (tennis-friendly)
        if clean_pbp and "incidents" in data:
            pbp = []
            for inc in data.get("incidents", []):
                if inc.get("incidentType") in ["point", "game", "set", "match"]:
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
        
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"error": "Timeout - Playwright too slow (try again or increase resources)"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Wrapper is alive"}
