"""
Memory layer using Qdrant.
Two logical collections are simulated inside one Qdrant collection using
a 'kind' field: junction_violation_history and congestion_pattern_by_time.

Uses Qdrant Cloud free tier — sign up at https://cloud.qdrant.io
Set QDRANT_URL and QDRANT_API_KEY in your .env file.
"""
import os
import time
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PayloadSchemaType

COLLECTION_NAME = "signalsense_memory"
VECTOR_SIZE = 8  # small fixed-size feature vector, see _vectorize() below

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
    return _client


def init_qdrant():
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    # BUG FIX: Qdrant requires an explicit payload index before you can
    # filter by a field (this is what caused "Index required but not
    # found for junction_id" — scroll_filter below needs this to exist).
    # create_payload_index is safe to call even if the index already
    # exists on a later restart.
    try:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="junction_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass  # index already exists — fine, ignore


def _vectorize(event: dict) -> list[float]:
    """
    Tiny hand-built feature vector so we don't need a full embedding model
    for the hackathon MVP: [num_violations, congestion_level_numeric,
    emergency_flag, hour_of_day, 0,0,0,0]. Swap for real embeddings later
    if you want semantic search over descriptions.
    """
    density_map = {"low": 0.25, "medium": 0.5, "high": 0.75, "severe": 1.0, "unknown": 0.0}
    num_violations = len(event.get("violations", {}).get("violations_found", []))
    density = density_map.get(event.get("congestion", {}).get("density_level", "unknown"), 0.0)
    emergency = 1.0 if event.get("emergency", {}).get("emergency_vehicle_detected") else 0.0
    hour = time.localtime().tm_hour / 24.0

    vec = [num_violations, density, emergency, hour, 0, 0, 0, 0]
    return vec


def log_event(junction_id: str, event: dict):
    client = _get_client()
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=_vectorize(event),
        payload={
            "junction_id": junction_id,
            "timestamp": time.time(),
            "event": event,
        },
    )
    client.upsert(collection_name=COLLECTION_NAME, points=[point])


def get_junction_history(junction_id: str, limit: int = 20) -> dict:
    client = _get_client()
    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter={"must": [{"key": "junction_id", "match": {"value": junction_id}}]},
        limit=limit,
    )
    events = [r.payload["event"] for r in results]
    return {
        "junction_id": junction_id,
        "past_event_count": len(events),
        "recent_events": events,
    }


def get_all_junctions_summary(limit: int = 200) -> str:
    """
    Pulls recent events across ALL junctions and formats them as plain text
    for the chat agent to read as grounding context. Kept as text (not raw
    JSON) because that's what the LLM reasons over most reliably.
    """
    client = _get_client()
    results, _ = client.scroll(collection_name=COLLECTION_NAME, limit=limit)

    if not results:
        return "No events logged yet."

    lines = []
    for r in results:
        payload = r.payload
        event = payload.get("event", {})
        violations = event.get("violations", {}).get("violations_found", [])
        density = event.get("congestion", {}).get("density_level", "unknown")
        emergency = event.get("emergency", {}).get("emergency_vehicle_detected", False)

        v_types = ", ".join(v.get("type", "?") for v in violations) or "none"
        lines.append(
            f"- Junction {payload.get('junction_id')}: violations=[{v_types}], "
            f"congestion={density}, emergency_vehicle={emergency}"
        )

    return "\n".join(lines)
