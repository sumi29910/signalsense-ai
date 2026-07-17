"""
Predictive Forecasting Agent (Pillar 4 — proactive, not just reactive).

Looks at a junction's logged history over time and estimates whether
congestion is trending up or down, so the city can act BEFORE a jam forms
instead of just reacting to camera frames as they come in.

This is intentionally simple (trend over logged density values) rather than
a full ML forecasting model — that's a reasonable v1 for a hackathon, and
the docstring below tells you exactly where to upgrade it later.
"""
from memory.qdrant_store import get_junction_history

DENSITY_SCORE = {"low": 1, "medium": 2, "high": 3, "severe": 4, "unknown": 0}


def forecast_junction(junction_id: str) -> dict:
    history = get_junction_history(junction_id, limit=10)
    events = history["recent_events"]

    if len(events) < 2:
        return {
            "junction_id": junction_id,
            "trend": "insufficient_data",
            "message": "Need at least 2 logged events to forecast a trend.",
        }

    scores = [
        DENSITY_SCORE.get(e.get("congestion", {}).get("density_level", "unknown"), 0)
        for e in events
    ]
    # events are most-recent-first from Qdrant scroll, so reverse for chronological order
    scores.reverse()

    recent_avg = sum(scores[-3:]) / len(scores[-3:])
    earlier_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]

    if recent_avg > earlier_avg + 0.5:
        trend = "rising"
        message = f"Congestion at {junction_id} is trending UP — consider preemptive signal adjustment."
    elif recent_avg < earlier_avg - 0.5:
        trend = "falling"
        message = f"Congestion at {junction_id} is easing."
    else:
        trend = "stable"
        message = f"Congestion at {junction_id} is steady, no action needed."

    return {
        "junction_id": junction_id,
        "trend": trend,
        "message": message,
        "sample_size": len(events),
    }


# --- Upgrade path (leave as a comment for when there's more time) ---
# Once there's more historical data, replace the average-comparison logic
# above with a proper time-series model (e.g. hosted on Vertex AI) that
# takes time-of-day and day-of-week into account — rush hour patterns
# repeat, and a same-time-yesterday comparison would be far more accurate
# than a simple recent-vs-earlier average.
