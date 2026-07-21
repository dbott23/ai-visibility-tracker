# AI Brand Visibility Tracker — ChatGPT, Perplexity, Gemini & Claude

**See exactly how AI assistants talk about your brands — and how that changes week
over week.** Run buyer-intent queries across ChatGPT, Perplexity, Gemini, and
Claude, then get mention rates, position scores, share of voice vs competitors,
cited sources, and **automatic trend deltas vs your previous run**. No API keys
needed — everything is bundled.

## Why this one

- **Multi-brand batches** — track a whole client roster (or your brand + every
  competitor) in a single run. Most trackers do one brand per run.
- **Trend deltas built in** — schedule it weekly and every run reports
  `mention_rate`, `position`, and `share of voice` **change** since last run.
  That's the report agencies actually send to clients.
- **No keys, zero config** — the default input works as-is; pricing is per
  check, so you pay only for what you run.

## Who uses it

SEO / GEO agencies reporting AI visibility to clients · brand & comms teams
watching how LLMs describe them · founders checking whether AI search
recommends them or their competitor.

## Input (works out of the box)

```json
{
  "brands": [{"name": "Asana", "competitors": ["Trello", "Monday.com"]}],
  "queries": ["best project management tool for small teams"],
  "engines": ["chatgpt", "perplexity", "gemini"]
}
```

## Output

One record per (brand × query × engine) check:

```json
{
  "brand": "Asana", "engine": "chatgpt",
  "query": "best project management tool for small teams",
  "brand_mentioned": true, "mention_count": 2, "position_score": 9,
  "share_of_voice": 0.4,
  "competitor_mentions": {"Trello": 2, "Monday.com": 1},
  "cited_domains": ["example.com", "blog.asana.com"]
}
```

Plus a `SUMMARY` key-value record with per-brand rollups and trend deltas:

```json
{"Asana": {"mention_rate": {"current": 0.67, "previous": 0.5, "delta": 0.17}}}
```

## Pricing

Pay per event: a flat rate per visibility check (brand × query × engine) plus a
small run-start fee. All upstream AI API costs are included.

## Use as an MCP tool

Add this actor to Claude, Cursor, or any MCP client via Apify's MCP server and
let your agent check AI visibility on demand.

## FAQ

**Do I need OpenAI/Anthropic/Google keys?** No — calls are made server-side at
the actor's expense and bundled into the per-check price.

**How do I get weekly trend reports?** Schedule the actor weekly with
`trackTrends: true` (the default). Use `trendKey` to keep separate series per
client.
