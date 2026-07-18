"""
Genie — the control-room assistant, now with real tool-calling.

This deliberately uses google-generativeai's built-in automatic function
calling instead of Google ADK. ADK caused repeated server crashes during
testing (likely an async/event-loop issue on Windows); this approach is
simpler and more stable, while still giving Genie genuine tool use — it
decides on its own whether to check junction history, forecast, plan a
corridor, or look up real-world traffic via Google Maps.
"""
import os
import time
import google.generativeai as genai

from agents.genie_tools import (
    check_junction_status,
    check_network_summary,
    check_forecast,
    plan_green_wave,
    check_real_world_traffic,
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = """You are Genie, the SignalSense AI control-room assistant
for a traffic operator managing a smart city network.

You have tools to:
- check status/history of monitored junctions (junction_01, junction_02, etc.)
- get a network-wide summary
- forecast congestion trends
- plan green-wave corridor timing
- look up REAL live traffic for any real-world place using Google Maps

Always call the right tool to get real data before answering. If the
operator names a real place (a chowk, road, landmark) that isn't a
monitored junction, use check_real_world_traffic. Never invent numbers,
places, or events. If a tool returns an error, tell the operator plainly
what went wrong instead of making something up.

Keep answers short (2-4 sentences), plain language, no markdown headers.
"""

_model = genai.GenerativeModel(
    model_name="gemini-flash-latest",
    system_instruction=SYSTEM_INSTRUCTION,
    tools=[
        check_junction_status,
        check_network_summary,
        check_forecast,
        plan_green_wave,
        check_real_world_traffic,
    ],
)


def ask_genie(question: str) -> dict:
    last_error = None
    for attempt in range(2):  # one retry after a short wait, that's it
        try:
            chat = _model.start_chat(enable_automatic_function_calling=True)
            response = chat.send_message(question)
            return {"question": question, "answer": response.text}
        except Exception as e:
            last_error = e
            if "429" in str(e) and attempt == 0:
                time.sleep(4)  # brief pause, free-tier limits are per-minute
                continue
            break

    if "429" in str(last_error):
        answer = ("I'm temporarily rate-limited by the free Gemini API tier — "
                  "this resets after about a minute. Please wait a moment and ask again.")
    else:
        answer = f"I ran into an issue answering that ({str(last_error)[:150]}). Please try again."

    return {"question": question, "answer": answer}
