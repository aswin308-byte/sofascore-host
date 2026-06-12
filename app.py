from fastapi import FastAPI
from sofascore_wrapper.api import SofascoreAPI
from fastapi.responses import JSONResponse
import asyncio
import traceback

app = FastAPI(title="Sofascore JSON Proxy - Debug Mode")

@app.get("/")
async def root():
    return {"status": "running", "note": "Debug mode - errors will be logged"}

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        api = SofascoreAPI()
        data = await asyncio.wait_for(api.get_event(event_id), timeout=50.0)
        
        response = {"data": data}
        
        if "incidents" in data:
            response["incidents"] = data["incidents"]
            response["incidents_count"] = len(data["incidents"])
        
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
                    })
            response["pbp"] = pbp
        
        return JSONResponse(content=response)
        
    except Exception as e:
        # This will print the FULL error in Railway logs
        print("=== ERROR START ===")
        print(traceback.format_exc())
        print("=== ERROR END ===")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.get("/health")
async def health():
    return {"status": "ok"}
