"""
Violation Detection Agent
Uses Gemini's multimodal vision to inspect a traffic frame and return
structured violation data. This is the agent judges will look at closely —
keep the prompt tight and the output schema strict (valid JSON only).
"""
import os
import json
import base64
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"  # fast + cheap, good for hackathon iteration

VIOLATION_PROMPT = """You are a traffic violation detection system analyzing one CCTV frame.

Look carefully and identify any of these violations if present:
- red_light_jump
- wrong_lane
- no_helmet
- illegal_parking
- wrong_side_driving

Respond with ONLY valid JSON, no markdown, no extra text, in this exact schema:
{
  "violations_found": [
    {"type": "<violation_type>", "confidence": <0-1 float>, "description": "<short reason>"}
  ],
  "vehicle_count_estimate": <int>
}

If nothing is clearly visible, return an empty violations_found list. Do not guess if unsure —
under-reporting is safer than false-flagging someone.
"""


def detect_violations(image_bytes: bytes, history: dict | None = None) -> dict:
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    model = genai.GenerativeModel(MODEL_NAME)

    try:
        response = model.generate_content([VIOLATION_PROMPT, image_part])
        text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
    except Exception as e:
        # Covers quota errors, network errors, and bad JSON — never let a
        # Gemini API failure take down the whole analyze-junction request.
        parsed = {"violations_found": [], "vehicle_count_estimate": 0, "api_error": str(e)}

    return parsed
