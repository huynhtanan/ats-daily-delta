#!/usr/bin/env python3
"""Merge Greenhouse + Ashby job records into a single flat CSV.

Reads two dataset exports (as JSON arrays or JSON Lines) and writes a
unified schema with 12 columns that work for both ATSes. Use this when
you want to pivot across companies in a spreadsheet without caring which
backend the data came from.

Example:
    # Greenhouse Apify dataset (JSON array)
    curl "https://api.apify.com/v2/datasets/<DS>/items?format=json" > gh.json

    # Ashby Apify dataset
    curl "https://api.apify.com/v2/datasets/<DS>/items?format=json" > ashby.json

    python merge_ats_csv.py --greenhouse gh.json --ashby ashby.json --out jobs.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

UNIFIED_FIELDS = [
    "ats",
    "company",
    "title",
    "url",
    "location",
    "workplaceType",
    "seniority",
    "aiEmploymentType",
    "salaryMin",
    "salaryMax",
    "salaryCurrency",
    "publishedAt",
]


def _load(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        return json.loads(text)
    # JSON Lines
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _row_greenhouse(it: dict) -> dict:
    return {
        "ats": "greenhouse",
        "company": it.get("companyName") or it.get("boardSlug") or "",
        "title": it.get("title") or "",
        "url": it.get("absoluteUrl") or "",
        "location": it.get("locationName") or "",
        "workplaceType": it.get("workplaceType") or "",
        "seniority": it.get("seniority") or "",
        "aiEmploymentType": it.get("aiEmploymentType") or "",
        "salaryMin": "",
        "salaryMax": "",
        "salaryCurrency": "",
        "publishedAt": it.get("firstPublished") or it.get("updatedAt") or "",
    }


def _row_ashby(it: dict) -> dict:
    return {
        "ats": "ashby",
        "company": it.get("boardSlug") or "",
        "title": it.get("title") or "",
        "url": it.get("jobUrl") or it.get("applyUrl") or "",
        "location": it.get("location") or "",
        "workplaceType": it.get("workplaceType") or "",
        "seniority": it.get("seniority") or "",
        "aiEmploymentType": it.get("aiEmploymentType") or "",
        "salaryMin": it.get("salaryMin") or "",
        "salaryMax": it.get("salaryMax") or "",
        "salaryCurrency": it.get("salaryCurrency") or "",
        "publishedAt": it.get("publishedAt") or "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--greenhouse", type=Path, help="Greenhouse JSON export")
    ap.add_argument("--ashby", type=Path, help="Ashby JSON export")
    ap.add_argument("--out", type=Path, required=True, help="Output CSV path")
    args = ap.parse_args()

    rows: list[dict] = []
    if args.greenhouse:
        rows.extend(_row_greenhouse(it) for it in _load(args.greenhouse))
    if args.ashby:
        rows.extend(_row_ashby(it) for it in _load(args.ashby))

    if not rows:
        print("No input files given; pass --greenhouse and/or --ashby.", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=UNIFIED_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
