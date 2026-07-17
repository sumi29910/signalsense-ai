"""
Congestion Agent
Estimates traffic density from the frame and recommends a signal timing
adjustment. Starts as simple threshold logic — swap in a Vertex AI model
later once you have real labeled data.
"""
import os
import json
import base64
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

CONGESTION_PROMPT = """You are a traffic congestion analysis system.

Look at this junction frame and estimate congestion level.

Respond with ONLY valid JSON in this schema:
{
  "density_level": "<low|medium|high|severe>",
  "estimated_vehicles": <int>,
  "recommended_green_time_seconds": <int>,
  "reasoning": "<one short sentence>"
}

Baseline signal timing is 30 seconds green. Recommend higher (up to 90s) for
high/severe density, lower (down to 15s) for low density.
"""


def analyze_congestion(image_bytes: bytes, history: dict | None = None) -> dict:
    image_part = {
        "mime_type": "image/jpeg",
        "data": base64.b64encode(image_bytes).decode("utf-8"),
    }

    model = genai.GenerativeModel(MODEL_NAME)

    try:
        response = model.generate_content([CONGESTION_PROMPT, image_part])
        text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        parsed = json.loads(text)
    except Exception as e:
        parsed = {
            "density_level": "unknown",
            "estimated_vehicles": 0,
            "recommended_green_time_seconds": 30,
            "reasoning": "parse_error",
            "api_error": str(e),
        }

    return parsed
