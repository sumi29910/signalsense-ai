"""
Safety / false-positive guardrail.

For the hackathon, wire this up to Enkrypt AI's guardrail API
(https://docs.enkryptai.com) — sign up for their free tier key and set
ENKRYPT_API_KEY in .env. Until you have that key wired in, this module
runs a local rule-based check so the pipeline still works end-to-end.

IMPORTANT for your pitch: this step exists because falsely flagging a
vehicle/driver has real consequences (wrongful fines) — this is exactly
the kind of place judges want to see genuine guardrail usage, not a
checkbox integration.
"""
import os

CONFIDENCE_THRESHOLD = 0.6


def _local_rule_check(result: dict) -> dict:
    """Drop any violation below confidence threshold instead of flagging it."""
    violations = result.get("violations", {}).get("violations_found", [])
    filtered = [v for v in violations if v.get("confidence", 0) >= CONFIDENCE_THRESHOLD]

    if "violations" in result:
        result["violations"]["violations_found"] = filtered
        result["violations"]["filtered_low_confidence_count"] = len(violations) - len(filtered)

    return result


def safety_check(result: dict) -> dict:
    enkrypt_key = os.getenv("ENKRYPT_API_KEY")

    if not enkrypt_key:
        # Fallback: local confidence-threshold guardrail
        return _local_rule_check(result)

    # --- Enkrypt AI integration ---
    # Once you have a key, replace this block with an actual call, e.g.:
    #
    # import requests
    # resp = requests.post(
    #     "https://api.enkryptai.com/guardrails/check",
    #     headers={"Authorization": f"Bearer {enkrypt_key}"},
    #     json={"content": result},
    # )
    # if resp.json().get("flagged"):
    #     result["safety_flagged"] = True
    #
    # Check their docs for the exact endpoint/schema before demo day.
    return _local_rule_check(result)
