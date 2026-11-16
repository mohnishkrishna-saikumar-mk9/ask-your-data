"""Answer cache (FR-14): identical (dataset, question, model, variant) returns instantly.

Small JSON-on-disk cache - survives app restarts, easy to inspect, no extra dependency.
Only the SQL is cached (not the rows), so results are always fresh from the database.
"""
import hashlib
import json
from pathlib import Path

from src.config import ROOT

CACHE_DIR = ROOT / ".cache" / "answers"


def cache_key(*parts: str) -> str:
    """Stable hash of the normalised inputs (case/whitespace-insensitive question)."""
    normalised = "|".join(" ".join(p.lower().split()) for p in parts)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:32]


def get(key: str, cache_dir: Path = CACHE_DIR) -> dict | None:
    """Return the cached entry or None."""
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def put(key: str, value: dict, cache_dir: Path = CACHE_DIR) -> None:
    """Store an entry (errors are ignored - caching must never break answering)."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{key}.json").write_text(json.dumps(value), encoding="utf-8")
    except OSError:
        pass
