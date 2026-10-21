# ATS daily-delta — Greenhouse + Ashby (Python)

Track **only the new jobs** at Greenhouse and Ashby career boards (AI labs, scale-ups, Series B+), without re-processing the 600+ open roles on every run. Each run pushes a flat row per newly-opened job (`title`, `url`, `location`, `workplaceType`, `department`, `seniority`, salary band when posted, …) and remembers what it already sent across runs via a persistent `stateKey`.

Scrapers:
- **[apify.com/zet46/greenhouse-jobs-scraper](https://apify.com/zet46/greenhouse-jobs-scraper)** — Greenhouse public boards (`boards.greenhouse.io/<slug>`), 1 API call per board, 24 fields per job including classified `seniority` / `remoteType` / `aiEmploymentType`.
- **[apify.com/zet46/ashby-jobs-scraper](https://apify.com/zet46/ashby-jobs-scraper)** — Ashby public boards (`jobs.ashbyhq.com/<slug>`), 30 fields including structured compensation (`salaryMin`, `salaryMax`, `salaryCurrency`, `salaryInterval`).

Both actors are pay-per-event at **$0.50 per 1,000 jobs**. A new Apify account gets $5/month free credit — covers a 10-board baseline plus months of daily deltas.

## Setup

```bash
pip install "apify-client>=3" requests
export APIFY_TOKEN=...   # https://console.apify.com/settings/integrations
```

## 1. Baseline + delta on Greenhouse ([python/greenhouse_delta.py](python/greenhouse_delta.py))

```bash
python python/greenhouse_delta.py
```

First run (baseline for 4 boards, 240 jobs):
```
[board:anthropic] total 676, pushed 60 new (prev 0, now 676)
[board:airbnb]    total 186, pushed 60 new (prev 0, now 186)
[board:stripe]    total 730, pushed 60 new (prev 0, now 730)
[board:figma]     total 142, pushed 60 new (prev 0, now 142)
Done: 240 job(s) across 4 board(s)

[anthropic] mid    | AI Operations Engineer, Partnerships — San Francisco, CA
[anthropic] senior | Senior Research Engineer, Alignment — San Francisco, CA
[airbnb]    senior | Staff Software Engineer, Payments — San Francisco, CA
...
```

Second run (same input, 30 seconds later) — no new jobs opened in between:
```
onlyNewSinceLastRun ON; using KVS 'greenhouse-diff-daily-prod' (persists across runs)
Done: 0 job(s) across 4 board(s)
```

Zero rows pushed. Zero rows billed. The actor stores a `set` of `(boardSlug, jobId)` under the `stateKey` in Apify's Key-Value Store between runs; on each run it fetches the current list, filters out IDs it has already seen, pushes the new ones to the dataset, and updates the stored set.

## 2. Ashby, with salary ranges pre-extracted ([python/ashby_delta.py](python/ashby_delta.py))

```bash
python python/ashby_delta.py
```

```
[board:openai] total 60,  pushed 60 new   — 53/60 with salary ranges (88%)
[board:ramp]   total 60,  pushed 60 new   — 60/60 with salary ranges (100%)
[board:notion] total 60,  pushed 60 new   —  0/60 with salary ranges
[board:linear] total 29,  pushed 29 new   —  0/29 with salary ranges
Done: 209 job(s) across 4 board(s)

[openai] 257000-335000 USD/YEAR  | Technical Program Manager, Compute Infrastructure
[openai] 250000-445000 USD/YEAR  | Research Engineer
[openai] 293000-585000 USD/YEAR  | Research Engineer, Retrieval & Search, Applied Engineering
[openai] 380000-500000 USD/YEAR  | Researcher, Safety Training
[ramp]   180000-220000 USD/YEAR  | Senior Software Engineer, Payments
```

Compensation ranges show up where the employer opted in (CA, CO, NY, WA, and a growing list of pay-transparency jurisdictions). No HTML scraping on your side.

## 3. Send new jobs to Slack on a 6-hour cron ([python/slack_watcher.py](python/slack_watcher.py))

```bash
export SLACK_WEBHOOK=https://hooks.slack.com/services/...
python python/slack_watcher.py
```

The watcher calls both actors, posts each row to the given webhook, and prints `Posted N new jobs`. Schedule it with `cron 0 */6 * * *`, GitHub Actions, or Apify's built-in Scheduler.

## Cost

| Scenario                                           | Rows billed   | Cost    |
| -------------------------------------------------- | ------------- | ------- |
| First run on 8 boards covering ~450 jobs           | ~450          | $0.22   |
| Zero-delta run (same input, nothing new)           | 0             | $0.00   |
| 6-hour cron, average 3–8 new jobs / run / 8 boards | ~80 / month   | ~$0.04  |

Pay-per-event; `onlyNewSinceLastRun` filtering happens before dataset push, so you don't pay for rows the actor already sent in a previous run under the same `stateKey`.

## Fields you get back

### Greenhouse (24 fields)

`boardSlug`, `jobId`, `internalJobId`, `title`, `absoluteUrl`, `locationName`, `workplaceType` (`Remote`/`Hybrid`/`Onsite`), `metadata[]`, `departments`, `offices`, `requisitionId`, `firstPublished`, `updatedAt`, `applicationDeadline`, `language`, `companyName`, `contentHtml` (opt-in), `aiDisclaimer`, `aiOptOutUrl`, `seniority` (`intern`/`junior`/`mid`/`senior`/`staff`/`principal`/`director`/`vp`/`exec`), `remoteType` (`remote`/`hybrid`/`on_site`), `aiEmploymentType`, `parseConfidence` (0–1), `warnings[]`, `scrapedAt`.

### Ashby (30 fields)

`boardSlug`, `jobId`, `title`, `jobUrl`, `applyUrl`, `location`, `secondaryLocations[]`, `country`, `region`, `locality`, `workplaceType`, `workplaceTypeRaw`, `isRemote`, `employmentType`, `department`, `team`, `isListed`, `publishedAt`, `salaryMin`, `salaryMax`, `salaryCurrency`, `salaryInterval`, `equitySummary`, `bonusSummary`, `commissionSummary`, `compensationSummary`, `shouldDisplayCompensation`, `compensation` (full struct), `descriptionPlain`, `descriptionHtml`.

Both actors also expose a **`mode=report`** that collapses one company into a single row with `hiringScore` 0–100, `priorityRoles[]`, `departmentSignals[]`, `expansionSignals[]`, etc. — see the Apify Store page for the full schema.

## 4. Cross-company compensation pivot ([python/salary_pivot.py](python/salary_pivot.py))

```bash
python python/salary_pivot.py openai ramp notion linear
```

Keeps USD/year engineering roles only, prints per-company p25/median/p75 for both the `salaryMin` and `salaryMax` columns, plus the top 10 highest-paying individual roles. On 2026-10-21 (14 OpenAI + Ramp eng rows with disclosed USD bands):

```
company        roles   min p25   min med   min p75   max p25   max med   max p75
--------------------------------------------------------------------------------
openai             4   258,250   266,000   275,250   343,750   390,000   452,500
ramp              14   147,000   185,630   220,000   220,000   294,150   330,000

Top 10 highest max-pay engineering roles:
  openai     $ 266K-$ 445K  Software Engineer, Scaled Abuse
  openai     $ 266K-$ 445K  Software Engineer, Observability
  ramp       $ 275K-$ 400K  Tech Lead, Ramp Travel
  ramp       $ 280K-$ 385K  Design Systems Lead
  openai     $ 257K-$ 335K  Technical Program Manager, Compute Infrastructure
  ...
```

Non-USD and non-yearly rows are skipped so the aggregate stays comparable; roughly 15 % of rows fall out of the pivot in practice.

## Multi-pipeline

Change the `stateKey` ("daily-prod" / "weekly-recruiting" / "friend-x-watchlist") to run multiple independent diffs against the same boards without their state clobbering each other.

## Sample output

Check [`samples/`](samples/) for:

- `greenhouse_sample.json` + `ashby_sample.json` — real snapshots of the actor output so you can see the schema without running anything.
- `jobs_merged_449.csv` — 449 jobs across 8 companies in the unified 12-column schema, including 113 rows with salary bands.
- `verified_slugs.csv` / `verified_slugs.json` — **100 verified Greenhouse + Ashby slugs (12,221 open roles as of 2026-10-21)**. Drop-in input list for the delta scripts: AI labs (OpenAI, Cursor, Perplexity, Cohere, ElevenLabs, Harvey, Sierra, LangChain, Writer, Suno, Pika, Deepgram, OpenRouter, Pinecone...), big public tech (Databricks, Stripe, Anthropic, Robinhood, MongoDB, GitLab, Pinterest, Lyft, Intercom, Coinbase, Elastic...), and dev-tool/fintech SaaS.


## 5. Merge Greenhouse + Ashby into one CSV ([python/merge_ats_csv.py](python/merge_ats_csv.py))

Both actors return a superset of fields specific to their ATS. When you want to pivot across companies in a spreadsheet or hand the data to a BI tool, flatten both exports into a 12-column unified schema:

```bash
python python/merge_ats_csv.py     --greenhouse gh_dataset.json     --ashby ashby_dataset.json     --out jobs.csv
```

Columns: `ats, company, title, url, location, workplaceType, seniority, aiEmploymentType, salaryMin, salaryMax, salaryCurrency, publishedAt`.

The sample [`samples/jobs_merged_449.csv`](samples/jobs_merged_449.csv) is a real export from 2026-10-21: 240 Greenhouse rows (Anthropic / Airbnb / Stripe / Figma, 60 each) + 209 Ashby rows (OpenAI 60 / Ramp 60 / Notion 60 / Linear 29). 113 of those 449 rows carry a disclosed salary band — ready for `pandas.read_csv("samples/jobs_merged_449.csv").dropna(subset=["salaryMin"])`.

## Use it from AI agents (MCP)

```json
{"mcpServers": {"apify": {"url": "https://mcp.apify.com?tools=zet46/greenhouse-jobs-scraper,zet46/ashby-jobs-scraper"}}}
```

Then ask Claude / Cursor *"what new senior engineering roles opened at Anthropic, Stripe and OpenAI since my last check?"*.

## Related reading

- [huynhtanan/jobs-ats-tracker](https://github.com/huynhtanan/jobs-ats-tracker) — companion repo with a broader SQLite-based tracker (50 orgs covering 9,618 open roles), plus a `compare_salaries.py` tool that ranks Ashby companies by yearly compensation band.
- [dev.to/huynhtanan](https://dev.to/huynhtanan) — background write-ups on the Greenhouse and Ashby JSON endpoints and how pay-per-event scraping compares with Playwright-based ATS crawlers.

---

Output above is from real runs on 2026-10-21. Open-role counts and salary ranges change daily. MIT licensed.
