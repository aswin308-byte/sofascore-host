from fastapi import FastAPI
from sofascore_wrapper.api import SofascoreAPI
from fastapi.responses import JSONResponse
import asyncio
import traceback

app = FastAPI(title="Sofascore JSON Proxy - Fixed")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/event/{event_id}")
async def get_event(event_id: int, clean_pbp: bool = False):
    try:
        api = SofascoreAPI()
        
        # Correct way to fetch match data (we'll adjust if needed)
        # Many wrappers use Match class or api.event(...)
        # For now we try to get full event data
        match_data = await asyncio.wait_for(
            api.event(event_id) if hasattr(api, 'event') else api.get_match(event_id),
            timeout=50.0
        )
        
        response = {"data": match_data}
        
        # Extract raw incidents (this is the PBP)
        if isinstance(match_data, dict) and "incidents" in match_data:
            response["incidents"] = match_data["incidents"]
            response["incidents_count"] = len(match_data["incidents"])
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print("=== FULL ERROR ===")
        print(traceback.format_exc())
        print("=== END ERROR ===")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
