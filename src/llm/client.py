"""One function to call any provider: complete(messages, model) -> (text, latency_ms)."""
import time
from collections.abc import Callable

from openai import OpenAI

from src.config import LLM_TIMEOUT_S
from src.llm.providers import api_key, parse_model

Messages = list[dict[str, str]]
# Signature of a completion function; tests pass a fake one instead of calling a real API.
CompleteFn = Callable[[Messages, str], tuple[str, float]]

_clients: dict[str, OpenAI] = {}


def _client_for(provider_name: str, base_url: str, key: str) -> OpenAI:
    """Reuse one SDK client per provider (keeps HTTP connections alive)."""
    if provider_name not in _clients:
        _clients[provider_name] = OpenAI(base_url=base_url, api_key=key,
                                         timeout=LLM_TIMEOUT_S, max_retries=1)
    return _clients[provider_name]


def reply_text(content: object) -> str:
    """The reply as one string. Most providers send a string; some (e.g. Gemini) can send a
    list of parts like [{"type": "text", "text": "..."}]."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") if isinstance(p, dict) else getattr(p, "text", str(p))
                 for p in content]
        return "".join(part for part in parts if part)
    return str(content)


def complete(messages: Messages, model: str) -> tuple[str, float]:
    """Send chat messages to `model` ("provider:model_id"); return (reply text, latency ms)."""
    provider, model_id = parse_model(model)
    client = _client_for(provider.name, provider.base_url, api_key(provider))
    start = time.perf_counter()
    response = client.chat.completions.create(model=model_id, messages=messages, temperature=0)
    latency_ms = (time.perf_counter() - start) * 1000
    return reply_text(response.choices[0].message.content), latency_ms
