# Sample output

Snapshots of real data returned by the two actors on **2026-10-21**, so you can see the schema without running anything.

## greenhouse_sample.json

10 rows from `zet46/greenhouse-jobs-scraper` with input:

```json
{"boardSlugs": ["anthropic", "airbnb", "stripe", "figma"], "mode": "jobs", "maxJobsPerBoard": 60}
```

Includes `seniority` / `remoteType` / `aiEmploymentType` classification, `parseConfidence`, and `warnings[]`. Anthropic rows carry `requisitionId` (e.g. `REQ-26-1145-01`), Airbnb/Figma rows carry `departments[]` populated.

## ashby_sample.json

10 rows from `zet46/ashby-jobs-scraper` — 5 OpenAI roles + 5 Ramp roles — all with structured salary data (`salaryMin`, `salaryMax`, `salaryCurrency`, `salaryInterval`, plus the full `compensation.compensationTiers[]` struct for anything with equity/bonus/commission).

Description bodies (`descriptionPlain`, `descriptionHtml`) are stripped from the samples to keep the files small — they are present on every row in a real run.

## jobs_merged_449.csv

Full output of [`python/merge_ats_csv.py`](../python/merge_ats_csv.py) run on the two JSON exports above (extended from 10 rows each to 60 per Greenhouse board + full Ashby board, as of 2026-10-21). 449 rows total:

| ATS         | Companies                            | Rows | With salary band |
| ----------- | ------------------------------------ | ---- | ---------------- |
| Greenhouse  | anthropic, airbnb, stripe, figma     | 240  | 0 (no pay-transparency header on these boards) |
| Ashby       | openai, ramp, notion, linear         | 209  | 113 (54 %)       |

Columns: `ats, company, title, url, location, workplaceType, seniority, aiEmploymentType, salaryMin, salaryMax, salaryCurrency, publishedAt`.

Load it with:

```python
import pandas as pd
df = pd.read_csv("samples/jobs_merged_449.csv")
df[df["salaryMin"].notna()].groupby("company")["salaryMax"].median().sort_values()
```


## verified_slugs.csv / verified_slugs.json

Known-good Greenhouse and Ashby board slugs, verified live on **2026-10-21**: 75 companies covering **10,491 open roles** (36 Greenhouse / 7,182 roles + 39 Ashby / 3,309 roles).

- CSV columns: `slug, ats, open_roles, api_url`.
- JSON wraps the same rows plus a top-level `as_of` + `total_roles` + `orgs` summary.

Use these as a starting board list for the `python/greenhouse_delta.py` + `python/ashby_delta.py` scripts (and the Slack watcher), or as the input for a nightly multi-company tracker. The slugs cluster around three groups: **AI labs on Ashby** (OpenAI, Cohere, Cursor, Perplexity, ElevenLabs, Harvey, Sierra, Cognition, LangChain, Writer, Lambda, Fireworks, Pinecone, Deepgram, OpenRouter, Suno, Pika, Character, Runway, Exa, Browserbase, Dust, Granola, Lovable...), **big public tech on Greenhouse** (Databricks, Stripe, Anthropic, Elastic, MongoDB, Robinhood, Coinbase, GitLab, Pinterest, Lyft, Intercom, Asana, Mercury, Mixpanel, Everlaw, Faire, Chime, Twilio, Twitch...), and **dev-tool / fintech / SaaS** on both.

## Caveats

- Open-role counts and compensation bands change daily. These files are a **snapshot**, not a live feed.
- Compensation on Ashby only shows up where the employer opted in. US pay-transparency jurisdictions (CA / CO / NY / WA / IL / MD / ...) force disclosure, so you'll see ~80–100 % salary coverage on US-headquartered companies and 0–20 % on EU-only companies.
- Greenhouse `departments[]` and `offices[]` are often empty — the actor sets `warnings: ["no_department"]` so you can skip rows that don't meet your filter.
