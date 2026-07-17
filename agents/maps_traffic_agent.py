"""
Real-world traffic lookup — answers "how's traffic at X" using actual
live data from Google Maps, not general knowledge.

Uses the Distance Matrix API with traffic_model=best_guess: it compares
normal travel time vs current travel time on a route to estimate real
congestion. Needs GOOGLE_MAPS_API_KEY in .env, and the Distance Matrix
API enabled + billing set up on that Google Cloud project (Maps APIs
require billing even within the free monthly credit).

If the operator only names a destination (e.g. "Sunaliya Chowk, Korba")
without an origin, Genie (see agents/genie_agent.py) is instructed to
pick a sensible nearby reference point as the origin — e.g. the city
name itself — so this still works for single-place questions.
"""
import os
import requests

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def get_route_traffic(origin: str, destination: str) -> dict:
    """
    Returns real current traffic conditions between two places.

    Args:
        origin: starting point, e.g. "Korba bus stand" or just "Korba"
        destination: destination place, e.g. "Sunaliya Chowk, Korba"
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "error": "GOOGLE_MAPS_API_KEY not set in .env — real traffic lookup "
                     "is disabled until this is configured. Get a key at "
                     "https://console.cloud.google.com/google/maps-apis and "
                     "enable the Distance Matrix API + billing."
        }

    params = {
        "origins": origin,
        "destinations": destination,
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key,
    }

    try:
        resp = requests.get(DISTANCE_MATRIX_URL, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "OK":
            return {"error": f"Maps API error: {data.get('status')} — {data.get('error_message', '')}"}

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return {"error": f"Could not find a route between '{origin}' and '{destination}'."}

        duration_normal_sec = element["duration"]["value"]
        duration_traffic_sec = element.get("duration_in_traffic", {}).get("value", duration_normal_sec)
        ratio = (duration_traffic_sec / duration_normal_sec) if duration_normal_sec else 1.0

        if ratio > 1.4:
            level = "heavy"
        elif ratio > 1.15:
            level = "moderate"
        else:
            level = "light"

        return {
            "origin": origin,
            "destination": destination,
            "distance": element["distance"]["text"],
            "normal_duration": element["duration"]["text"],
            "current_duration": element.get("duration_in_traffic", {}).get("text", element["duration"]["text"]),
            "congestion_level": level,
        }
    except Exception as e:
        return {"error": f"Traffic lookup failed: {str(e)}"}
