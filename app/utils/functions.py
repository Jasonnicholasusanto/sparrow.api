from datetime import datetime, timezone
import math
from typing import Any
from urllib.parse import urlparse


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def extract_storage_path(public_url: str, bucket_name: str) -> str:
    """
    Extracts the exact storage path from a Supabase public URL,
    removing bucket prefix and any query parameters.
    """
    # Parse URL (to remove ?query parts)
    parsed = urlparse(public_url)
    clean_path = (
        parsed.path
    )  # e.g. "/storage/v1/object/public/profile-pictures/<folder>/<file>.jpg"

    # Extract the part after "<bucket_name>/"
    return clean_path.split(f"/{bucket_name}/", 1)[-1]


def safe_json_float(value: Any) -> Any:
    try:
        if isinstance(value, float) and not math.isfinite(value):
            return None
    except Exception:
        return None
    return value
