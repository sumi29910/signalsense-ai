"""
Chat Agent — the "conversational analyst" (Pillar 3).

This is what an operator talks to from the dashboard. It does NOT run at
the traffic signal — it runs on the server/control-room side. The operator
types a question in plain language, this agent pulls relevant data from
Qdrant memory, and asks Gemini to answer grounded in that real data
(so it doesn't hallucinate numbers).
"""
import os
import google.generativeai as genai
from memory.qdrant_store import get_all_junctions_summary

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-flash-latest"

CHAT_SYSTEM_PROMPT = """You are Genie, the SignalSense AI control-room assistant.
You help a traffic operator understand what is happening across monitored
junctions. You are ONLY given real logged data below — never invent
numbers, junction names, or events that aren't in this data.

If the data doesn't answer the question, say so honestly instead of guessing.

LOGGED DATA:
{context}

Operator question: {question}

Answer in 2-4 short sentences, plain language, no markdown headers.
"""


def ask_agent(question: str) -> dict:
    context = get_all_junctions_summary()
    prompt = CHAT_SYSTEM_PROMPT.format(context=context, question=question)

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        answer = response.text.strip()
    except Exception as e:
        # Never let a Gemini quota/network error crash the /chat request —
        # Genie should always reply with SOMETHING, even on failure.
        answer = f"I'm having trouble reaching my AI model right now ({str(e)[:120]}...). Please try again in a moment."

    return {"question": question, "answer": answer}
