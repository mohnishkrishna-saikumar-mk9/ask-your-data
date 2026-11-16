"""Loads per-dataset knowledge files: metric glossary and few-shot examples."""
from functools import lru_cache

import yaml

from src.config import ROOT

KNOWLEDGE_DIR = ROOT / "knowledge"


@lru_cache(maxsize=8)
def load_glossary(dataset: str) -> dict:
    """Return {'metrics': {...}, 'notes': [...]} for a dataset (empty if file missing)."""
    path = KNOWLEDGE_DIR / dataset / "glossary.yaml"
    if not path.exists():
        return {"metrics": {}, "notes": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=8)
def load_few_shots(dataset: str) -> list[dict[str, str]]:
    """Return [{'question': ..., 'sql': ...}, ...] for a dataset."""
    path = KNOWLEDGE_DIR / dataset / "few_shots.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("examples", [])


@lru_cache(maxsize=8)
def load_example_questions(dataset: str) -> list[str]:
    """Five example questions shown as buttons on the Ask page (FR-16)."""
    path = KNOWLEDGE_DIR / dataset / "few_shots.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("ui_examples", [])


def render_glossary(dataset: str) -> str:
    """Glossary as plain text lines for the prompt."""
    g = load_glossary(dataset)
    lines = [f"- {name}: {definition}" for name, definition in g.get("metrics", {}).items()]
    lines += [f"- NOTE: {note}" for note in g.get("notes", [])]
    return "\n".join(lines)
