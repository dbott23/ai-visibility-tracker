"""AI Brand Visibility Tracker — Apify actor entry point.

Multi-brand batch x queries x engines, with run-over-run trend deltas kept in a
named key-value store. Charges pay-per-event per (brand, query, engine) check.
"""
from __future__ import annotations

import asyncio
import json

from apify import Actor, Event

from analysis import aggregate, analyze_response, compute_deltas
from engines import ENGINE_MODELS, ask_engine

TREND_STORE = "ai-visibility-trends"

# Progress lives in the run's default key-value store, which survives a
# migration. Without it, a migrated run restarts main() from scratch: every
# check is re-run (duplicate dataset rows, double API spend) and every
# pay-per-event charge fires a second time for work the customer already paid
# for. Apify migrates runs routinely, so this is a normal path, not an edge case.
CHECKPOINT_KEY = "CHECKPOINT"


def _check_id(brand: str, query: str, engine: str) -> str:
    """Stable identity for one (brand, query, engine) unit of work.

    JSON-encoded rather than delimiter-joined so that a brand or query
    containing the delimiter cannot collide with a different check.
    """
    return json.dumps([brand, query, engine], sort_keys=True)


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

        checkpoint = await Actor.get_value(CHECKPOINT_KEY) or {}
        records: list[dict] = checkpoint.get("records") or []
        done: set[str] = set(checkpoint.get("done") or [])
        resumed = bool(checkpoint)

        trend_store = await Actor.open_key_value_store(name=TREND_STORE)
        trend_key = inp.get("trendKey") or "default"
        # Read the comparison baseline before any work, and checkpoint it: this
        # run overwrites the stored series at the end, so a migration after that
        # write would otherwise leave the resumed run comparing against itself
        # and reporting every delta as zero.
        baseline = (checkpoint.get("baseline") if resumed
                    else await trend_store.get_value(trend_key))

        async def save_checkpoint() -> None:
            await Actor.set_value(CHECKPOINT_KEY, {
                "records": records,
                "done": sorted(done),
                "baseline": baseline,
            })

        # A migration can land between any two checks; flush progress on the
        # way out so the new host resumes instead of starting over.
        async def on_migrating(_event_data) -> None:
            await save_checkpoint()

        Actor.on(Event.MIGRATING, on_migrating)

        if resumed:
            Actor.log.info(
                f"Resuming after migration: {len(done)} of "
                f"{len(brands) * len(queries) * len(engines)} checks already done."
            )
        else:
            # Charged once per run; on resume the original run already paid.
            await Actor.charge("actor-start")

        for brand in brands:
            name = brand["name"]
            aliases = brand.get("aliases") or []
            competitors = brand.get("competitors") or []
            for query in queries:
                for engine in engines:
                    check_id = _check_id(name, query, engine)
                    if check_id in done:
                        continue
                    answer = await asyncio.to_thread(
                        ask_engine, engine, query, brand=name
                    )
                    rec = analyze_response(answer.text, name, aliases, competitors,
                                           answer.source_urls)
                    rec.update({
                        "brand": name, "engine": engine, "query": query,
                        "response_snippet": answer.text[:400],
                        # A truncated reply may simply not have reached the
                        # brand yet, so a False `brand_mentioned` on this row
                        # is inconclusive rather than a real absence.
                        "response_truncated": answer.truncated,
                    })
                    if answer.truncated and not rec["brand_mentioned"]:
                        Actor.log.warning(
                            f"{engine} reply hit the token limit before mentioning "
                            f"{name} ({query!r}) - treat this row as inconclusive."
                        )
                    records.append(rec)
                    await Actor.push_data(rec)
                    # Commit the check as done before charging for it. A
                    # migration in the gap then costs us one uncharged check
                    # rather than billing the customer twice for one result —
                    # the safe direction to fail on a monetized Actor.
                    done.add(check_id)
                    await save_checkpoint()
                    await Actor.charge("visibility-check")

        summary = aggregate(records)

        deltas = None
        if track_trends:
            deltas = compute_deltas(summary, baseline)
            await trend_store.set_value(trend_key, summary)

        await Actor.set_value("SUMMARY", {"summary": summary, "trends": deltas})
        await Actor.set_status_message(
            f"Done: {len(records)} checks across {len(brands)} brand(s), "
            f"{len(engines)} engine(s)."
        )


if __name__ == "__main__":
    asyncio.run(main())
