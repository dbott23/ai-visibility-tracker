"""Pure analysis functions for the AI Brand Visibility Tracker.

Everything here is deterministic and offline-testable: mention detection,
position scoring, share of voice, citation extraction, aggregation, and
run-over-run trend deltas. No network calls.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse


def _brand_pattern(name: str) -> re.Pattern:
    # Word-boundary match, case-insensitive; tolerate possessives ("Acme's").
    return re.compile(r"\b" + re.escape(name.strip()) + r"(?:'s)?\b", re.IGNORECASE)


def find_mentions(text: str, brand: str, aliases: list[str] | None = None) -> list[dict]:
    """All prose mentions of brand (or aliases), as {offset, matched, term}.

    URLs are masked first: a brand inside a cited link is a citation
    (extract_citations), not a prose mention.
    """
    text = _URL_RE.sub(lambda m: " " * len(m.group(0)), text)
    mentions = []
    for term in [brand] + list(aliases or []):
        if not term.strip():
            continue
        for m in _brand_pattern(term).finditer(text):
            mentions.append({"offset": m.start(), "matched": m.group(0), "term": term})
    mentions.sort(key=lambda x: x["offset"])
    return mentions


def position_score(text: str, first_offset: int | None) -> int:
    """1-10: 10 = mentioned at the very top of the response, 1 = at the tail.

    0 = not mentioned at all.
    """
    if first_offset is None or not text:
        return 0
    frac = first_offset / max(len(text), 1)
    return max(1, 10 - int(frac * 10))


def share_of_voice(brand_count: int, competitor_counts: dict[str, int]) -> float:
    """brand mentions / (brand + all competitor mentions); 0.0 if nobody mentioned."""
    total = brand_count + sum(competitor_counts.values())
    if total == 0:
        return 0.0
    return round(brand_count / total, 4)


_URL_RE = re.compile(r"https?://[^\s\)\]\}>\"']+")


def _as_citation(url: str) -> dict:
    return {"url": url, "domain": urlparse(url).netloc.lower().removeprefix("www.")}


def extract_citations(text: str, source_urls: list[str] | None = None) -> list[dict]:
    """Unique URLs for a response, in order, as {url, domain}.

    Inline URLs found in the prose come first, followed by any `source_urls` the
    provider returned out-of-band (search-backed models list sources in a
    structured field instead of in the text).
    """
    seen, out = set(), []
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;:!?")
        if url in seen:
            continue
        seen.add(url)
        out.append(_as_citation(url))
    for url in source_urls or []:
        url = url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(_as_citation(url))
    return out


def analyze_response(text: str, brand: str, aliases: list[str] | None,
                     competitors: list[str],
                     source_urls: list[str] | None = None) -> dict:
    """Full per-response analysis record (engine/query metadata added by caller)."""
    mentions = find_mentions(text, brand, aliases)
    comp_counts = {c: len(find_mentions(text, c)) for c in competitors}
    first = mentions[0]["offset"] if mentions else None
    citations = extract_citations(text, source_urls)
    return {
        "brand_mentioned": bool(mentions),
        "mention_count": len(mentions),
        "position_score": position_score(text, first),
        "share_of_voice": share_of_voice(len(mentions), comp_counts),
        "competitor_mentions": comp_counts,
        "citations": citations,
        "cited_domains": sorted({c["domain"] for c in citations}),
    }


def aggregate(records: list[dict]) -> dict:
    """Roll per-response records (each carrying `brand` + analysis fields) into a
    per-brand summary: mention rate, mean position, mean share of voice, and
    per-engine breakdown."""
    brands: dict[str, dict] = {}
    for r in records:
        b = brands.setdefault(r["brand"], {"responses": 0, "mentioned": 0,
                                           "position_sum": 0, "sov_sum": 0.0,
                                           "engines": {}})
        b["responses"] += 1
        b["mentioned"] += 1 if r["brand_mentioned"] else 0
        b["position_sum"] += r["position_score"]
        b["sov_sum"] += r["share_of_voice"]
        e = b["engines"].setdefault(r["engine"], {"responses": 0, "mentioned": 0})
        e["responses"] += 1
        e["mentioned"] += 1 if r["brand_mentioned"] else 0

    out = {}
    for brand, b in brands.items():
        n = b["responses"]
        out[brand] = {
            "responses": n,
            "mention_rate": round(b["mentioned"] / n, 4) if n else 0.0,
            "avg_position_score": round(b["position_sum"] / n, 2) if n else 0.0,
            "avg_share_of_voice": round(b["sov_sum"] / n, 4) if n else 0.0,
            "engines": {
                eng: {"mention_rate": round(e["mentioned"] / e["responses"], 4),
                      "responses": e["responses"]}
                for eng, e in b["engines"].items()
            },
        }
    return out


def compute_deltas(current: dict, previous: dict | None) -> dict:
    """Week-over-week (run-over-run) per-brand deltas — the wedge feature.

    Returns {brand: {metric: {current, previous, delta}}} for the three headline
    metrics; brands new this run get previous=None.
    """
    deltas: dict[str, dict] = {}
    metrics = ("mention_rate", "avg_position_score", "avg_share_of_voice")
    for brand, cur in current.items():
        prev = (previous or {}).get(brand)
        deltas[brand] = {}
        for m in metrics:
            pv = prev.get(m) if prev else None
            deltas[brand][m] = {
                "current": cur[m],
                "previous": pv,
                "delta": round(cur[m] - pv, 4) if pv is not None else None,
            }
    return deltas
