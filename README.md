# AI Brand Visibility Tracker — ChatGPT, Perplexity, Gemini & Claude

**Find out if AI recommends you — or your competitor.**

Run real buyer-intent queries across ChatGPT, Perplexity, Gemini, and Claude. Get mention rates, position scores, share of voice vs. competitors, cited sources, and automatic **week-over-week trend deltas** in a single run. No API keys needed.

---

## What it does

For each combination of brand × query × engine, the actor:

1. Sends the query to the AI engine (using its real web-search mode)
2. Detects whether your brand is mentioned, how early, and how often
3. Measures your share of voice vs. every competitor you list
4. Collects the URLs the AI cited as sources
5. Compares results to your previous run and reports the delta

All checks run in one batch — track a whole client roster or your brand + every competitor in a single run.

---

## Why this tracker

| Feature | This actor | Most trackers |
|---|---|---|
| Multi-brand batches | ✅ unlimited | ❌ one brand per run |
| Built-in trend deltas | ✅ automatic | ❌ manual export |
| 4 engines (incl. web-search) | ✅ | ❌ 1–2 engines |
| No API keys needed | ✅ | ❌ requires your keys |
| Pay only for what you run | ✅ per-check pricing | ❌ flat subscription |

---

## Who uses it

- **SEO / GEO agencies** building AI visibility reports for clients
- **Brand & comms teams** monitoring how LLMs describe them vs. the competition
- **Founders** checking whether AI search recommends them or their rival
- **Product marketers** tracking share of voice across AI channels

---

## Input

The default input works out of the box — just swap in your brand name:

```json
{
  "brands": [
    {
      "name": "Asana",
      "aliases": [],
      "competitors": ["Trello", "Monday.com", "ClickUp"]
    }
  ],
  "queries": [
    "best project management tool for small teams",
    "what project management software should a startup use"
  ],
  "engines": ["chatgpt", "perplexity", "gemini"],
  "trackTrends": true
}
```

**Input fields:**

| Field | Required | Description |
|---|---|---|
| `brands` | ✅ | List of brands. Each has `name`, optional `aliases`, optional `competitors`. |
| `queries` | ✅ | Buyer-intent questions your customers ask AI assistants. |
| `engines` | — | `chatgpt`, `perplexity`, `gemini`, `claude`. Default: first three (search-backed). |
| `trackTrends` | — | Save this run's summary and report deltas vs. the previous run. Default: `true`. |
| `trendKey` | — | Label to keep separate trend series (e.g. one per client). |

---

## Output

### Dataset — one row per (brand × query × engine) check

```json
{
  "brand": "Asana",
  "engine": "chatgpt",
  "query": "best project management tool for small teams",
  "brand_mentioned": true,
  "mention_count": 2,
  "position_score": 9,
  "share_of_voice": 0.4,
  "competitor_mentions": { "Trello": 2, "Monday.com": 1, "ClickUp": 0 },
  "cited_domains": ["g2.com", "blog.asana.com"],
  "response_snippet": "For small teams, Asana offers a generous free tier...",
  "response_truncated": false
}
```

**Key fields:**

- `position_score` — 1–10; 10 = brand named first, 1 = named last, 0 = not mentioned
- `share_of_voice` — brand mentions ÷ (brand + all competitor mentions)
- `cited_domains` — domains the AI cited as sources for its answer
- `response_truncated` — `true` if the AI hit its token limit (treat that row as inconclusive)

### SUMMARY key-value — per-brand rollup + trend deltas

```json
{
  "summary": {
    "Asana": {
      "mention_rate": 0.67,
      "avg_position_score": 7.5,
      "avg_share_of_voice": 0.42,
      "engines": {
        "chatgpt":    { "mention_rate": 1.0, "responses": 2 },
        "perplexity": { "mention_rate": 0.5, "responses": 2 }
      }
    }
  },
  "trends": {
    "Asana": {
      "mention_rate":       { "current": 0.67, "previous": 0.5,  "delta":  0.17 },
      "avg_position_score": { "current": 7.5,  "previous": 6.0,  "delta":  1.5  },
      "avg_share_of_voice": { "current": 0.42, "previous": 0.38, "delta":  0.04 }
    }
  }
}
```

---

## Pricing

Pay per event — a small flat fee per visibility check (brand × query × engine). All upstream AI API costs are included; you don't need your own keys.

**Example:** 1 brand × 3 queries × 3 engines = 9 checks.

---

## Scheduling for weekly trend reports

1. Set up a **Schedule** in Apify (Actors → Schedules → New schedule)
2. Point it at this actor with your saved input
3. Keep `trackTrends: true` (the default)
4. Every run automatically compares to the previous one and writes deltas to `SUMMARY`

Use `trendKey` to maintain separate trend series per client — e.g. `"trendKey": "client-acme"`.

---

## Use as an MCP tool

Add this actor to Claude Desktop, Cursor, or any MCP-compatible client via [Apify's MCP server](https://apify.com/apify/actors-mcp-server) and let your agent check AI brand visibility on demand.

---

## FAQ

**Do I need OpenAI / Anthropic / Google API keys?**
No. All API calls are made server-side and the cost is bundled into the per-check price.

**Which engine uses real web search?**
All four: `chatgpt` uses `gpt-4o-search-preview`, `perplexity` uses `sonar` (always web-backed), `gemini` uses `gemini-2.5-flash`, and `claude` uses `claude-sonnet-5` via OpenRouter.

**What if a response is truncated?**
The actor flags `response_truncated: true` on that row. A brand absent from a truncated response may simply not have been reached yet — treat it as inconclusive rather than a true "not mentioned."

**Can I track multiple clients without their data mixing?**
Yes — set a unique `trendKey` per client (e.g. `"client-acme"`, `"client-beta"`). Each series is stored separately.

**What's the difference between `mention_count` and `position_score`?**
`mention_count` is how many times the brand appeared in the response. `position_score` (1–10) measures *where* it first appeared — being named first scores 10, being buried at the end scores 1.

---

## More from dbott23

| Actor | What it does |
|---|---|
| [AI Citation Auditor](https://apify.com/dbott23/ai-citation-auditor) | Check if your website is cited by ChatGPT, Perplexity, and Gemini |
| [App Store & Google Play Reviews Scraper](https://apify.com/dbott23/appstore-reviews-scraper) | Export iOS and Android app reviews by keyword or app ID |
| [Trustpilot Reviews Scraper](https://apify.com/dbott23/trustpilot-reviews-scraper) | Export Trustpilot reviews to CSV or JSON — no API key needed |
| [B2B Reviews Scraper](https://apify.com/dbott23/b2b-reviews-scraper) | Pull reviews from G2, Capterra, and Trustpilot in one run |
| [Bluesky Posts Scraper](https://apify.com/dbott23/bluesky-posts-scraper) | Search and export Bluesky posts by keyword or user profile |
