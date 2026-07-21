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


# Verbose models answer a "best tool for X" query as a listicle with a long
# paragraph per entry. Left unguided they burn the token budget describing the
# first one or two products and get cut off, so brands further down the list
# look absent when they were simply never reached — a false "not mentioned"
# reading, which is the worst possible error for a visibility tracker. Ask for
# the full slate of names up front and keep the per-item prose short.
SYSTEM_PROMPT = (
    "Answer as you normally would for a user researching this question. "
    "Name every product or company you would actually recommend, listing them "
    "in your genuine order of preference, and keep each description to one or "
    "two sentences so the full list fits in your reply."
)

# Headroom for the whole list. Truncation is still detected and surfaced.
MAX_TOKENS = 1600


class Answer(NamedTuple):
    """An engine's reply: prose plus the URLs the provider cited out-of-band.

    Search-backed models (notably perplexity/sonar) return their sources in a
    structured field rather than inline in the prose, so extracting URLs from
    `text` alone misses them entirely.

    `truncated` flags a reply the model cut short at the token limit: any brand
    it had not reached yet is missing for mechanical reasons, so a "not
    mentioned" result on such a row is unreliable rather than meaningful.
    """
    text: str
    source_urls: list[str]
    truncated: bool = False


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
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "max_tokens": MAX_TOKENS,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    choice = (payload.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    return Answer(text, _provider_citations(payload),
                  choice.get("finish_reason") == "length")
