"""
Emergency Priority Agent
Detects ambulance / fire truck / police vehicle in frame and requests a
green-corridor signal override. This is the agent that maps directly to
the "emergency vehicle priority" line in the official problem statement —
make sure your demo video shows this triggering clearly.
"""
import os
import base64
import google.generativeai as genai
from agents.json_utils import extract_json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

EMERGENCY_PROMPT = """You are an emergency vehicle detection system.

Check this traffic frame for an ambulance, fire truck, or police vehicle with
visible emergency markings (lights, sirens, livery).

Respond with ONLY valid JSON:
{
  "emergency_vehicle_detected": <true|false>,
  "vehicle_type": "<ambulance|fire_truck|police|none>",
  "confidence": <0-1 float>,
  "recommended_action": "<grant_green_corridor|none>"
}
"""


def check_emergency_vehicle(image_bytes: bytes) -> dict:
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    model = genai.GenerativeModel(MODEL_NAME)

    try:
        response = model.generate_content([EMERGENCY_PROMPT, image_part])
        parsed = extract_json(response.text)
        if parsed is None:
            parsed = {
                "emergency_vehicle_detected": False,
                "vehicle_type": "none",
                "confidence": 0.0,
                "recommended_action": "none",
                "parse_error": True,
                "raw_response": response.text[:200],
            }
    except Exception as e:
        parsed = {
            "emergency_vehicle_detected": False,
            "vehicle_type": "none",
            "confidence": 0.0,
            "recommended_action": "none",
            "api_error": str(e),
        }

    return parsed
