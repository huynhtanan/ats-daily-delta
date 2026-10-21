"""Pull only the NEW Greenhouse jobs since the previous run.

    pip install "apify-client>=3"
    export APIFY_TOKEN=...        # https://console.apify.com/settings/integrations
    python greenhouse_delta.py
"""
import os

from apify_client import ApifyClient

BOARDS = ["anthropic", "airbnb", "stripe", "figma"]
STATE_KEY = "daily-prod"      # change per independent pipeline
MAX_PER_BOARD = 500           # high enough to cover the full board


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def main():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/greenhouse-jobs-scraper").call(run_input={
        "boardSlugs": BOARDS,
        "mode": "jobs",
        "onlyNewSinceLastRun": True,
        "stateKey": STATE_KEY,
        "maxJobsPerBoard": MAX_PER_BOARD,
        "includeContent": False,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    rows = list(client.dataset(dataset_id).iterate_items())
    if not rows:
        print(f"No new Greenhouse jobs since the last run under stateKey={STATE_KEY!r}.")
        return
    print(f"{len(rows)} new Greenhouse job(s) since the last run under stateKey={STATE_KEY!r}:\n")
    for it in rows:
        seniority = (it.get("seniority") or "")[:7]
        remote = (it.get("workplaceType") or "")[:7]
        print(f'  [{it["boardSlug"]:>9}] {seniority:7} {remote:7} | '
              f'{it["title"][:70]:70}  — {it.get("locationName") or "—"}')


if __name__ == "__main__":
    main()
