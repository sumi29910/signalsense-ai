"""
Location Query Agent — answers general traffic questions about ANY city,
not just the junctions monitored in Qdrant memory.

This is intentionally separate from the control-room chat agent: the
control-room agent only talks about YOUR monitored junctions (grounded,
no hallucination). This one answers general knowledge questions like
"how's traffic usually in Bengaluru during rush hour" using Gemini's
general knowledge — clearly labeled as general info, not live sensor data.
"""
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

LOCATION_PROMPT = """You are a traffic information assistant. The user is
asking a general question about traffic in a specific city or area:
"{query}"

Give a short, helpful, realistic answer (3-5 sentences) about typical
traffic patterns, congestion times, or general road conditions for that
place, based on general knowledge. Clearly note this is general
information, not a live sensor reading, if the question implies real-time
status.
"""


def answer_location_query(query: str) -> dict:
    prompt = LOCATION_PROMPT.format(query=query)
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    return {"query": query, "answer": response.text.strip()}
