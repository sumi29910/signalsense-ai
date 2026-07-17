"""
Google Cloud Storage — stores uploaded traffic frames permanently.

Without this, frames only exist in memory during a request and are
discarded after analysis — nothing to audit or review later. This module
saves each analyzed frame to a GCS bucket and returns its URL, which gets
attached to the event logged in Qdrant (see memory/qdrant_store.py).

Setup:
1. Create a bucket: https://console.cloud.google.com/storage
2. Set GCS_BUCKET_NAME in .env
3. Authenticate locally: `gcloud auth application-default login`
   (same login used for Vertex AI — see agents/adk_agent.py)

If GCS isn't configured, upload_frame() returns None and the pipeline
keeps working normally (frame just won't be permanently stored) — this
matters because a hackathon demo shouldn't break if a bucket isn't set
up yet.
"""
import os
import time
import uuid

_bucket = None
_gcs_available = True


def _get_bucket():
    global _bucket, _gcs_available
    if not _gcs_available:
        return None
    if _bucket is not None:
        return _bucket

    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        _gcs_available = False
        return None

    try:
        from google.cloud import storage
        client = storage.Client()
        _bucket = client.bucket(bucket_name)
        return _bucket
    except Exception:
        # google-cloud-storage not installed, not authenticated, or bucket
        # doesn't exist — fail soft so the rest of the app keeps working.
        _gcs_available = False
        return None


def upload_frame(image_bytes: bytes, junction_id: str) -> str | None:
    """
    Uploads a frame to GCS under frames/<junction_id>/<timestamp>_<uuid>.jpg
    Returns the GCS URL (gs://bucket/path) or None if GCS isn't configured.
    """
    bucket = _get_bucket()
    if bucket is None:
        return None

    filename = f"frames/{junction_id}/{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    return f"gs://{bucket.name}/{filename}"
