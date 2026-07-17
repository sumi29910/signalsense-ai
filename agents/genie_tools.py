"""
Genie's tools. Each function here is a capability Genie can decide to
call on its own, based on what the operator asks. Docstrings matter —
Gemini reads them to decide which tool fits the question.
"""
from memory.qdrant_store import get_junction_history, get_all_junctions_summary
from agents.predictive_agent import forecast_junction
from agents.corridor_agent import coordinate_corridor
from agents.maps_traffic_agent import get_route_traffic


def check_junction_status(junction_id: str) -> dict:
    """Get logged history (violations, congestion, emergency events) for one
    monitored junction, e.g. 'junction_01'. Only works for junctions that
    have been analyzed through this system, not arbitrary real-world places."""
    return get_junction_history(junction_id)


def check_network_summary() -> dict:
    """Get a summary of recent events across ALL monitored junctions in the
    network. Use for questions like 'is everything okay' or 'what's happening
    across the network right now'."""
    return {"summary": get_all_junctions_summary()}


def check_forecast(junction_id: str) -> dict:
    """Forecast whether congestion at a monitored junction is trending up,
    down, or stable, e.g. 'junction_01'."""
    return forecast_junction(junction_id)


def plan_green_wave(junction_ids_csv: str) -> dict:
    """Plan a green-wave signal timing sequence across a corridor of
    connected monitored junctions, e.g. 'junction_01,junction_02'."""
    ids = [j.strip() for j in junction_ids_csv.split(",") if j.strip()]
    return coordinate_corridor(ids)


def check_real_world_traffic(origin: str, destination: str) -> dict:
    """Get REAL, current live traffic conditions between two real-world
    places using Google Maps — use this for ANY question about a specific
    road, chowk, landmark, or area that is NOT one of the monitored
    junctions (e.g. 'Sunaliya Chowk', 'MG Road'). If the operator only
    names one place, use the city or a well-known central point in that
    city as the origin, and the named place as the destination."""
    return get_route_traffic(origin, destination)
