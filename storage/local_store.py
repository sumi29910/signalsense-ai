"""
Local backup storage — saves a copy of every analyzed frame to the
uploads/ folder on disk, regardless of whether GCS is configured.

This exists so you never lose a frame during development/demo — GCS
requires setup (bucket + auth), but this always works out of the box.
The uploads/ folder itself is gitignored so images never get pushed
to GitHub.
"""
import os
import time
import uuid

LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


def save_frame_locally(image_bytes: bytes, junction_id: str) -> str:
    """Saves the frame to uploads/<junction_id>/<timestamp>_<uuid>.jpg, returns the local path."""
    junction_dir = os.path.join(LOCAL_UPLOAD_DIR, junction_id)
    os.makedirs(junction_dir, exist_ok=True)

    filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(junction_dir, filename)

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    return filepath
