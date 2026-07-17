"""
Coordinator agent — this is the orchestration layer used by main.py.
The dashboard's chat also has an alternative real ADK agent (see
agents/adk_agent.py) — this coordinator handles the frame-analysis
pipeline specifically (upload -> detect -> store -> log).
"""
from agents.violation_detection import detect_violations
from agents.congestion_agent import analyze_congestion
from agents.emergency_agent import check_emergency_vehicle
from memory.qdrant_store import log_event, get_junction_history
from safety.guardrail import safety_check
from storage.local_store import save_frame_locally
from storage.gcs_store import upload_frame


def route_analysis(junction_id: str, image_bytes: bytes) -> dict:
    # Step 1: pull past pattern for this junction from memory (safe — if
    # Qdrant is briefly unreachable, don't let that kill the whole request)
    try:
        history = get_junction_history(junction_id)
    except Exception as e:
        history = {"junction_id": junction_id, "past_event_count": 0, "recent_events": [], "memory_error": str(e)}

    # Step 2: run detection agents. Each of these already has its own
    # internal try/except (see agents/violation_detection.py etc.) so a
    # Gemini quota error returns a safe default instead of raising.
    violations = detect_violations(image_bytes, history=history)
    congestion = analyze_congestion(image_bytes, history=history)
    emergency = check_emergency_vehicle(image_bytes)

    raw_result = {
        "junction_id": junction_id,
        "violations": violations,
        "congestion": congestion,
        "emergency": emergency,
    }

    # Step 3: safety / false-positive guardrail before anything gets flagged
    checked_result = safety_check(raw_result)

    # Step 4: store the actual frame — local backup always, GCS if configured.
    try:
        checked_result["frame_local_path"] = save_frame_locally(image_bytes, junction_id)
    except Exception as e:
        checked_result["frame_local_path"] = None
        checked_result["local_storage_error"] = str(e)

    try:
        checked_result["frame_gcs_url"] = upload_frame(image_bytes, junction_id)
    except Exception:
        checked_result["frame_gcs_url"] = None  # GCS not configured — fine

    # Step 5: log this event (with frame reference) back into memory
    try:
        log_event(junction_id, checked_result)
    except Exception as e:
        checked_result["memory_log_error"] = str(e)

    return checked_result
