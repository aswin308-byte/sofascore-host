from fastapi import FastAPI
from sofascore_wrapper.api import SofascoreAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Sofascore JSON Proxy")

@app.get("/")
async def root():
    return {"status": "Sofascore wrapper running - use /event/{id}"}

@app.get("/event/{event_id}")
async def get_event(event_id: int):
    try:
        api = SofascoreAPI()
        data = await api.get_event(event_id)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health():
    return {"status": "ok"}
