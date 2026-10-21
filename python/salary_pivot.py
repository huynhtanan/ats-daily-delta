"""Cross-company compensation pivot from Ashby salary data.

Fetches the current Ashby public boards for a list of companies via
`zet46/ashby-jobs-scraper`, then prints:

- per-company median / p25 / p75 salary-min and salary-max for engineering roles
- top 10 highest-paying individual roles across the input companies

Only USD/YEAR rows are included so the aggregate stays comparable (we skip
hourly, monthly and non-USD postings — ~15% of rows in practice).

Usage:
    export APIFY_TOKEN=...
    python python/salary_pivot.py                 # defaults: openai ramp notion linear
    python python/salary_pivot.py openai ramp notion linear perplexity figma

Needs: pip install "apify-client>=3"
"""

from __future__ import annotations

import os
import statistics
import sys

from apify_client import ApifyClient


def main() -> None:
    boards = sys.argv[1:] or ["openai", "ramp", "notion", "linear"]

    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/ashby-jobs-scraper").call(
        run_input={
            "boardSlugs": boards,
            "mode": "jobs",
            "onlyNewSinceLastRun": False,
            "maxJobsPerBoard": 500,
        }
    )

    rows = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    eng = [
        r
        for r in rows
        if r.get("salaryMin")
        and r.get("salaryCurrency") == "USD"
        and r.get("salaryInterval") == "1 YEAR"
        and _is_eng(r.get("title", ""), r.get("department", ""))
    ]

    print(f"Pulled {len(rows)} rows across {len(boards)} boards; "
          f"{len(eng)} are USD/year engineering roles.")
    if not eng:
        return

    print()
    print(f'{"company":10} {"roles":>6} {"min p25":>9} {"min med":>9} {"min p75":>9} '
          f'{"max p25":>9} {"max med":>9} {"max p75":>9}')
    print("-" * 80)

    for board in boards:
        subset = [r for r in eng if r["boardSlug"] == board]
        if not subset:
            print(f"{board:10} {0:>6}")
            continue
        mins = sorted(r["salaryMin"] for r in subset)
        maxs = sorted(r["salaryMax"] for r in subset)
        print(
            f"{board:10} {len(subset):>6} "
            f"{_q(mins, 0.25):>9,} {statistics.median(mins):>9,.0f} {_q(mins, 0.75):>9,} "
            f"{_q(maxs, 0.25):>9,} {statistics.median(maxs):>9,.0f} {_q(maxs, 0.75):>9,}"
        )

    print()
    print("Top 10 highest max-pay engineering roles:")
    for r in sorted(eng, key=lambda x: x["salaryMax"], reverse=True)[:10]:
        print(
            f'  {r["boardSlug"]:10} ${r["salaryMin"]/1000:>4.0f}K-${r["salaryMax"]/1000:>4.0f}K  '
            f'{r["title"][:70]}'
        )


_ENG_WORDS = (
    "engineer",
    "engineering",
    "developer",
    "architect",
    "sre",
    "devops",
    "infrastructure",
    "platform",
    "ml ",
    "ai ",
    "research",
    "scientist",
    "data",
    "backend",
    "frontend",
    "fullstack",
    "software",
)


def _is_eng(title: str, department: str) -> bool:
    s = f"{title} {department}".lower()
    return any(w in s for w in _ENG_WORDS)


def _q(xs, p: float) -> int:
    if not xs:
        return 0
    k = (len(xs) - 1) * p
    f, c = int(k), min(int(k) + 1, len(xs) - 1)
    return int(xs[f] + (xs[c] - xs[f]) * (k - f))


if __name__ == "__main__":
    main()
