"""Pull only the NEW Ashby jobs since the previous run.

Each row includes a structured compensation range when the employer posted one
(CA, CO, NY, WA and other pay-transparency jurisdictions).

    pip install "apify-client>=3"
    export APIFY_TOKEN=...        # https://console.apify.com/settings/integrations
    python ashby_delta.py
"""
import os

from apify_client import ApifyClient

BOARDS = ["openai", "ramp", "notion", "linear"]
STATE_KEY = "daily-prod"
MAX_PER_BOARD = 500


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def main():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor("zet46/ashby-jobs-scraper").call(run_input={
        "boardSlugs": BOARDS,
        "mode": "jobs",
        "onlyNewSinceLastRun": True,
        "stateKey": STATE_KEY,
        "maxJobsPerBoard": MAX_PER_BOARD,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    rows = list(client.dataset(dataset_id).iterate_items())
    if not rows:
        print(f"No new Ashby jobs since the last run under stateKey={STATE_KEY!r}.")
        return
    print(f"{len(rows)} new Ashby job(s) since the last run under stateKey={STATE_KEY!r}:\n")
    for it in rows:
        pay = ""
        if it.get("salaryMin"):
            pay = f'{int(it["salaryMin"]):>7}-{int(it["salaryMax"]):<7} {it.get("salaryCurrency","")}/{(it.get("salaryInterval") or "").lower():5}'
        else:
            pay = " " * 24
        loc = it.get("location") or "—"
        print(f'  [{it["boardSlug"]:>7}] {pay} | {it["title"][:70]:70} — {loc}')


if __name__ == "__main__":
    main()
