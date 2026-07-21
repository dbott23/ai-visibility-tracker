"""AI Brand Visibility Tracker — Apify actor entry point.

Multi-brand batch x queries x engines, with run-over-run trend deltas kept in a
named key-value store. Charges pay-per-event per (brand, query, engine) check.
"""
from __future__ import annotations

import asyncio

from apify import Actor

from analysis import aggregate, analyze_response, compute_deltas
from engines import ENGINE_MODELS, ask_engine

TREND_STORE = "ai-visibility-trends"


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        brands: list[dict] = inp.get("brands") or []
        queries: list[str] = inp.get("queries") or []
        engines: list[str] = inp.get("engines") or ["chatgpt", "perplexity", "gemini"]
        track_trends: bool = inp.get("trackTrends", True)

        if not brands or not queries:
            await Actor.fail(status_message="Provide at least one brand and one query.")
            return
        bad = [e for e in engines if e not in ENGINE_MODELS]
        if bad:
            await Actor.fail(status_message=f"Unknown engines: {bad}")
            return

        await Actor.charge("actor-start")

        records = []
        for brand in brands:
            name = brand["name"]
            aliases = brand.get("aliases") or []
            competitors = brand.get("competitors") or []
            for query in queries:
                for engine in engines:
                    text = await asyncio.to_thread(
                        ask_engine, engine, query, brand=name
                    )
                    rec = analyze_response(text, name, aliases, competitors)
                    rec.update({
                        "brand": name, "engine": engine, "query": query,
                        "response_snippet": text[:400],
                    })
                    records.append(rec)
                    await Actor.push_data(rec)
                    await Actor.charge("visibility-check")

        summary = aggregate(records)

        deltas = None
        if track_trends:
            store = await Actor.open_key_value_store(name=TREND_STORE)
            trend_key = inp.get("trendKey") or "default"
            previous = await store.get_value(trend_key)
            deltas = compute_deltas(summary, previous)
            await store.set_value(trend_key, summary)

        await Actor.set_value("SUMMARY", {"summary": summary, "trends": deltas})
        await Actor.set_status_message(
            f"Done: {len(records)} checks across {len(brands)} brand(s), "
            f"{len(engines)} engine(s)."
        )


if __name__ == "__main__":
    asyncio.run(main())
