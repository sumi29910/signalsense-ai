"""
ADK Control-Room Agent (advanced version of Pillar 3).

This is a REAL Google ADK agent — not just a Gemini API call. It has
actual tools it can decide to call based on what the operator asks:
  - check junction history
  - check network-wide summary
  - forecast congestion trend
  - plan a corridor green-wave

Because it's a proper ADK Agent, you can also test it standalone with:
    adk web
from inside the agents/ folder (ADK auto-discovers root_agent).

VERTEX AI: if GOOGLE_GENAI_USE_VERTEXAI=True is set in .env (along with
GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION), ADK automatically routes
these Gemini calls through Vertex AI instead of the AI Studio API key.
That's what makes ticking "Vertex AI" in the submission form honest.
"""
import os
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from memory.qdrant_store import get_junction_history, get_all_junctions_summary
from agents.predictive_agent import forecast_junction
from agents.corridor_agent import coordinate_corridor


# ---- Tools: plain Python functions. ADK reads the docstring + type hints
# ---- to decide when to call each one. Keep docstrings clear — the model
# ---- uses them to choose the right tool. ----

def check_junction_history(junction_id: str) -> dict:
    """Get the logged violation/congestion/emergency history for one specific junction.

    Args:
        junction_id: the junction identifier, e.g. "junction_01"

    Returns:
        dict with past_event_count and recent_events for that junction.
    """
    return get_junction_history(junction_id)


def check_network_summary() -> dict:
    """Get a summary of recent events across ALL monitored junctions in the city network.
    Use this for questions like 'which junction has the most violations' or
    'what's happening across the network right now'.

    Returns:
        dict with a text summary of all logged events.
    """
    return {"summary": get_all_junctions_summary()}


def check_forecast(junction_id: str) -> dict:
    """Forecast whether congestion at a junction is trending up, down, or stable.

    Args:
        junction_id: the junction identifier, e.g. "junction_01"

    Returns:
        dict with trend ('rising'/'falling'/'stable') and a human-readable message.
    """
    return forecast_junction(junction_id)


def plan_corridor_green_wave(junction_ids_csv: str) -> dict:
    """Plan a green-wave signal timing sequence across a corridor of connected junctions.
    Use this when the operator asks to coordinate, sequence, or optimize signals
    across multiple junctions on the same road.

    Args:
        junction_ids_csv: comma-separated junction IDs in road order, e.g. "junction_01,junction_02,junction_03"

    Returns:
        dict with the corridor_plan (offsets and durations) and reasoning.
    """
    ids = [j.strip() for j in junction_ids_csv.split(",") if j.strip()]
    return coordinate_corridor(ids)


root_agent = Agent(
    model="gemini-flash-latest",
    name="genie_control_room_agent",
    instruction="""You are Genie, the SignalSense AI control-room assistant, helping a
traffic operator monitor and manage a network of smart traffic junctions.

You have tools to check individual junction history, get a network-wide
summary, forecast congestion trends, and plan corridor green-wave sequences.
Always call the relevant tool to get real data before answering — never
invent junction names, numbers, or events. If a tool returns no data, say
so honestly.

Keep answers short (2-4 sentences), plain language, no markdown headers.""",
    tools=[check_junction_history, check_network_summary, check_forecast, plan_corridor_green_wave],
)

_runner = InMemoryRunner(agent=root_agent)
_APP_NAME = _runner.app_name


async def ask_agent_adk(question: str, session_id: str = "control_room_session") -> str:
    """Send a question to the ADK agent and return its final text response."""
    user_id = "operator"

    # Session must exist before run_async — create it if this is a new session.
    try:
        await _runner.session_service.create_session(
            app_name=_APP_NAME, user_id=user_id, session_id=session_id
        )
    except Exception:
        pass  # session already exists, that's fine

    content = types.Content(parts=[types.Part(text=question)], role="user")
    final_text = "(no response)"

    async for event in _runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text = part.text

    return final_text
