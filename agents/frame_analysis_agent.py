"""
Consolidated Frame Analysis Agent.

Previously this pipeline made 3 separate Gemini calls per frame (one each
for violations, congestion, emergency vehicles) — that's 3x the quota
usage of a single call, which was causing repeated 429 "quota exceeded"
errors on the free tier during testing.

This combines all three into ONE Gemini vision call, cutting API usage
by two-thirds. The coordinator then splits the single response into the
same violations/congestion/emergency shape the rest of the app expects,
so nothing downstream (safety guardrail, dashboard rendering, Qdrant
logging) needs to change.
"""
import os
import time
import base64
import google.generativeai as genai
from agents.json_utils import extract_json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

ANALYSIS_PROMPT = """You are a traffic analysis system inspecting one CCTV frame.
Analyze it for THREE things at once:

1. VIOLATIONS — look for: red_light_jump, wrong_lane, no_helmet, illegal_parking, wrong_side_driving
2. CONGESTION — estimate density and recommend a signal green time (baseline 30s, up to 90s for severe, down to 15s for low)
3. EMERGENCY VEHICLES — ambulance, fire truck, or police with visible markings

Respond with ONLY valid JSON, no markdown, no extra text, in this exact schema:
{
  "violations_found": [
    {"type": "<violation_type>", "confidence": <0-1 float>, "description": "<short reason>"}
  ],
  "density_level": "<low|medium|high|severe>",
  "estimated_vehicles": <int>,
  "recommended_green_time_seconds": <int>,
  "congestion_reasoning": "<one short sentence>",
  "emergency_vehicle_detected": <true|false>,
  "emergency_vehicle_type": "<ambulance|fire_truck|police|none>",
  "emergency_confidence": <0-1 float>
}

If nothing is clearly visible for a category, use empty/false/none defaults for it.
Do not guess if unsure — under-reporting is safer than false-flagging someone.
"""


def analyze_frame(image_bytes: bytes) -> dict:
    """Returns a single dict with violations, congestion, and emergency data combined."""
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    model = genai.GenerativeModel(MODEL_NAME)

    parsed = None
    last_error = None
    for attempt in range(3):
        try:
            response = model.generate_content([ANALYSIS_PROMPT, image_part])
            parsed = extract_json(response.text)
            if parsed is None:
                return _fallback(parse_error=True, raw=response.text[:200])
            break
        except Exception as e:
            last_error = e
            if "429" in str(e) and attempt < 2:
                time.sleep(8 * (attempt + 1))  # 8s, then 16s
                continue
            return _fallback(api_error=str(e))

    # Split into the shape the rest of the app already expects
    violations = {
        "violations_found": parsed.get("violations_found", []),
        "vehicle_count_estimate": parsed.get("estimated_vehicles", 0),
    }
    congestion = {
        "density_level": parsed.get("density_level", "unknown"),
        "estimated_vehicles": parsed.get("estimated_vehicles", 0),
        "recommended_green_time_seconds": parsed.get("recommended_green_time_seconds", 30),
        "reasoning": parsed.get("congestion_reasoning", ""),
    }
    emergency = {
        "emergency_vehicle_detected": parsed.get("emergency_vehicle_detected", False),
        "vehicle_type": parsed.get("emergency_vehicle_type", "none"),
        "confidence": parsed.get("emergency_confidence", 0.0),
        "recommended_action": "grant_green_corridor" if parsed.get("emergency_vehicle_detected") else "none",
    }

    return {"violations": violations, "congestion": congestion, "emergency": emergency}


def _fallback(parse_error=False, api_error=None, raw=None) -> dict:
    note = {"parse_error": True, "raw_response": raw} if parse_error else {"api_error": api_error}
    return {
        "violations": {"violations_found": [], "vehicle_count_estimate": 0, **note},
        "congestion": {"density_level": "unknown", "estimated_vehicles": 0,
                       "recommended_green_time_seconds": 30, "reasoning": "Analysis failed.", **note},
        "emergency": {"emergency_vehicle_detected": False, "vehicle_type": "none",
                      "confidence": 0.0, "recommended_action": "none", **note},
    }
