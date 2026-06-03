from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from api.streaming import start_analysis, stream_events, get_result, get_session_status

router = APIRouter()


class AnalyzeRequest(BaseModel):
    query: str = ""


@router.post("/analyze/{ticker}")
async def start(ticker: str, body: AnalyzeRequest = AnalyzeRequest()):
    session_id, from_cache = start_analysis(ticker.upper(), body.query)
    return {"session_id": session_id, "ticker": ticker.upper(), "cached": from_cache}


@router.get("/stream/{session_id}")
async def stream(session_id: str):
    status = get_session_status(session_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/result/{session_id}")
async def result(session_id: str):
    status = get_session_status(session_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Session not found")
    if status != "done":
        return {"status": status}
    data = get_result(session_id)
    return {"status": "done", "data": data}
