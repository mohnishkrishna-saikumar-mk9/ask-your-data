"""Registry of OpenAI-compatible LLM providers (SPEC 9.2).

Models are referenced everywhere as "provider:model_id", e.g. "groq:llama-3.3-70b-versatile".
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    """Connection details for one provider."""

    name: str
    base_url: str
    key_env: str | None  # None = no key needed (local Ollama)


PROVIDERS: dict[str, Provider] = {
    "groq": Provider("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "gemini": Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/",
                       "GEMINI_API_KEY"),
    "openrouter": Provider("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "ollama": Provider("ollama", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), None),
}


def parse_model(spec: str) -> tuple[Provider, str]:
    """'groq:llama-3.3-70b' -> (groq Provider, 'llama-3.3-70b'). Model ids may contain ':' or '/'."""
    provider_name, sep, model_id = spec.partition(":")
    if not sep or not model_id:
        raise ValueError(f"Model must look like 'provider:model_id', got {spec!r}")
    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider_name!r}. Choose from {sorted(PROVIDERS)}")
    return PROVIDERS[provider_name], model_id


def api_key(provider: Provider) -> str:
    """Read the provider's key from the environment ('ollama' gets a dummy key)."""
    if provider.key_env is None:
        return "ollama"
    key = os.getenv(provider.key_env, "")
    if not key:
        raise RuntimeError(f"{provider.key_env} is not set in .env")
    return key


def available_models(candidates: list[str]) -> list[str]:
    """Keep only models whose provider key is configured (so the UI never offers dead options)."""
    usable = []
    for spec in candidates:
        try:
            provider, _ = parse_model(spec)
            api_key(provider)
            usable.append(spec)
        except (ValueError, RuntimeError):
            continue
    return usable
