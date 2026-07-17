"""
Corridor Coordination Agent (Pillar 4 — network-scale intelligence).

A "corridor" is a set of connected junctions along one road. Instead of
each signal deciding independently, this agent looks at congestion across
the whole corridor and sequences green lights so traffic flows smoothly
from one junction to the next — a "green wave". This is the piece that
makes the project a genuine SMART CITY / network agent, not just a
single-camera detector.
"""
import os
import json
import google.generativeai as genai
from memory.qdrant_store import get_junction_history

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

CORRIDOR_PROMPT = """You are a traffic corridor coordination system.

You manage a sequence of connected junctions on the same road, in order:
{junction_order}

Current congestion data for each junction:
{junction_data}

Decide a signal timing sequence that creates a "green wave" — a car
travelling down this corridor should hit mostly green lights. Junctions
with higher congestion need a longer green window and should get priority
in the sequence.

Respond with ONLY valid JSON:
{{
  "corridor_plan": [
    {{"junction_id": "<id>", "green_offset_seconds": <int>, "green_duration_seconds": <int>}}
  ],
  "reasoning": "<one short sentence explaining the sequencing logic>"
}}

green_offset_seconds is how many seconds after the first junction turns
green this junction should turn green (0 for the first one).
"""


def coordinate_corridor(junction_ids: list[str]) -> dict:
    junction_data_lines = []
    for jid in junction_ids:
        history = get_junction_history(jid, limit=1)
        recent = history["recent_events"][0] if history["recent_events"] else {}
        density = recent.get("congestion", {}).get("density_level", "unknown")
        junction_data_lines.append(f"- {jid}: congestion={density}")

    prompt = CORRIDOR_PROMPT.format(
        junction_order=" -> ".join(junction_ids),
        junction_data="\n".join(junction_data_lines),
    )

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)

    try:
        text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        # Safe fallback: equal spacing, default duration, no AI reasoning available
        parsed = {
            "corridor_plan": [
                {"junction_id": jid, "green_offset_seconds": i * 15, "green_duration_seconds": 30}
                for i, jid in enumerate(junction_ids)
            ],
            "reasoning": "fallback_equal_spacing_used",
        }

    return parsed
