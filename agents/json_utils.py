"""
Shared JSON extraction helper.

Gemini is asked to respond with pure JSON, but sometimes wraps it in
markdown fences, adds a stray sentence before/after, or uses slightly
different fence styles. A naive "strip the exact ```json prefix" approach
fails silently whenever the response doesn't match exactly — which is
what was causing every analysis to fall back to default/empty values
regardless of the actual image content.

This function tries multiple extraction strategies before giving up.
"""
import json
import re


def extract_json(text: str) -> dict | None:
    if not text:
        return None

    text = text.strip()

    # Strategy 1: direct parse (best case — model followed instructions exactly)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: pull content out of a ```json ... ``` or ``` ... ``` fence,
    # wherever it appears in the text (not just at the very start)
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find the first '{' and the last '}' and try that slice —
    # catches cases with a stray sentence before/after the JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None
