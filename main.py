"""
SignalSense AI - Main entry point
Orchestrates: Violation Detection -> Congestion -> Emergency Priority -> Memory -> Safety -> Response
"""
import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from agents.coordinator import route_analysis
from agents.corridor_agent import coordinate_corridor
from agents.predictive_agent import forecast_junction
from memory.qdrant_store import init_qdrant, get_junction_history, get_all_junctions_summary

load_dotenv()

app = FastAPI(title="SignalSense AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the simple test UI at /
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup():
    init_qdrant()


@app.get("/")
def root():
    return {"status": "SignalSense AI running", "docs": "/docs"}


@app.post("/analyze-junction")
async def analyze_junction(
    junction_id: str = Form(...),
    frame: UploadFile = File(...),
):
    """
    Main pipeline entry point.
    Upload one traffic camera frame for a given junction_id.
    Returns violations found, congestion suggestion, emergency status.
    """
    image_bytes = await frame.read()
    result = route_analysis(junction_id=junction_id, image_bytes=image_bytes)
    return result


@app.get("/junction/{junction_id}/history")
def junction_history(junction_id: str):
    """Return past violation/congestion pattern for a junction from Qdrant memory."""
    return get_junction_history(junction_id)


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Pillar 3 — Genie, the conversational analyst. Uses Gemini's built-in
    function calling (agents/genie_agent.py) so Genie can genuinely decide
    to check junction history, forecast, plan corridors, or look up real
    Google Maps traffic for any named place. Falls back to a plain Gemini
    call if anything about the tool-calling path fails, so the dashboard
    never breaks.
    """
    try:
        from agents.genie_agent import ask_genie
        return ask_genie(req.question)
    except Exception:
        from agents.chat_agent import ask_agent
        return ask_agent(req.question)


@app.get("/overview")
def overview():
    """Summary data for the dashboard's overview cards."""
    summary_text = get_all_junctions_summary()
    return {"summary": summary_text}


class CorridorRequest(BaseModel):
    junction_ids: list[str]


@app.post("/corridor/optimize")
def corridor_optimize(req: CorridorRequest):
    """
    Network-scale agent: given an ordered list of connected junctions,
    returns a green-wave signal timing plan across all of them.
    """
    return coordinate_corridor(req.junction_ids)


@app.get("/junction/{junction_id}/forecast")
def junction_forecast(junction_id: str):
    """Predictive agent: is congestion trending up, down, or stable here."""
    return forecast_junction(junction_id)


class RouteTrafficQuery(BaseModel):
    origin: str
    destination: str


@app.post("/route-traffic")
def route_traffic(req: RouteTrafficQuery):
    """Real live traffic between two places via Google Maps — used directly
    by the Location Search page (bypasses the chat agent for a quick lookup)."""
    from agents.maps_traffic_agent import get_route_traffic
    return get_route_traffic(req.origin, req.destination)


class LocationQuery(BaseModel):
    query: str


@app.post("/location-query")
def location_query(req: LocationQuery):
    """General traffic Q&A about any city — not grounded in Qdrant, uses
    Gemini's general knowledge. Separate from the control-room chat which
    only talks about monitored junctions."""
    from agents.location_agent import answer_location_query
    return answer_location_query(req.query)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
