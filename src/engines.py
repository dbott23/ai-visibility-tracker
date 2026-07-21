"""Engine callers. One key (OPENROUTER_API_KEY, actor-secret env var) covers all
chat engines; no keys ever required from the user.

MOCK_MODE=1 returns canned fixtures so the whole actor can run end-to-end with
zero API spend (used by tests and the free demo path).
"""
from __future__ import annotations

import os

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Engine label shown to users -> OpenRouter model id. Web-search-capable
# variants chosen so answers reflect what AI search actually says today.
ENGINE_MODELS = {
    "chatgpt": "openai/gpt-4o-search-preview",
    "perplexity": "perplexity/sonar",
    "gemini": "google/gemini-2.5-flash",
    "claude": "anthropic/claude-sonnet-5",
}

MOCK_RESPONSE = (
    "For this category, {brand} is one option alongside competitors. "
    "See https://example.com/roundup for a comparison."
)


def ask_engine(engine: str, query: str, *, brand: str = "", timeout: float = 90.0) -> str:
    """Return the engine's answer text for one query."""
    if os.environ.get("MOCK_MODE") == "1":
        return MOCK_RESPONSE.format(brand=brand or "the brand")

    model = ENGINE_MODELS[engine]
    resp = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 900,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
