"""Engine callers. One key (OPENROUTER_API_KEY, actor-secret env var) covers all
chat engines; no keys ever required from the user.

MOCK_MODE=1 returns canned fixtures so the whole actor can run end-to-end with
zero API spend (used by tests and the free demo path).
"""
from __future__ import annotations

import os
from typing import NamedTuple

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


class Answer(NamedTuple):
    """An engine's reply: prose plus the URLs the provider cited out-of-band.

    Search-backed models (notably perplexity/sonar) return their sources in a
    structured field rather than inline in the prose, so extracting URLs from
    `text` alone misses them entirely.
    """
    text: str
    source_urls: list[str]


def _provider_citations(payload: dict) -> list[str]:
    """URLs from OpenRouter's structured citation fields, in order, deduped.

    Two shapes are in the wild: a top-level `citations` list of URL strings
    (Perplexity's passthrough), and per-message `annotations` entries of type
    `url_citation` (the OpenAI-style format). Accept both.
    """
    urls: list[str] = []
    for c in payload.get("citations") or []:
        if isinstance(c, str):
            urls.append(c)
        elif isinstance(c, dict) and c.get("url"):
            urls.append(c["url"])

    message = (payload.get("choices") or [{}])[0].get("message") or {}
    for ann in message.get("annotations") or []:
        if not isinstance(ann, dict):
            continue
        cite = ann.get("url_citation") or (ann if ann.get("type") == "url_citation" else {})
        if isinstance(cite, dict) and cite.get("url"):
            urls.append(cite["url"])

    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def ask_engine(engine: str, query: str, *, brand: str = "", timeout: float = 90.0) -> Answer:
    """Return the engine's answer text plus any provider-supplied source URLs."""
    if os.environ.get("MOCK_MODE") == "1":
        return Answer(MOCK_RESPONSE.format(brand=brand or "the brand"), [])

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
    payload = resp.json()
    text = payload["choices"][0]["message"]["content"] or ""
    return Answer(text, _provider_citations(payload))
