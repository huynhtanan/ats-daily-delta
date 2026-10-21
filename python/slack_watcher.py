"""Post newly-opened Greenhouse + Ashby jobs to a Slack webhook.

Schedule with `cron 0 */6 * * *`, GitHub Actions, or Apify's built-in Scheduler.

    pip install "apify-client>=3" requests
    export APIFY_TOKEN=...
    export SLACK_WEBHOOK=https://hooks.slack.com/services/...
    python slack_watcher.py
"""
import os

import requests
from apify_client import ApifyClient

STATE_KEY = "daily-prod"
GREENHOUSE_BOARDS = ["anthropic", "airbnb", "stripe", "figma"]
ASHBY_BOARDS = ["openai", "ramp", "notion", "linear"]


def _attr(obj, snake, camel):
    if isinstance(obj, dict):
        return obj.get(camel) or obj.get(snake)
    return getattr(obj, snake, None) or getattr(obj, camel, None)


def new_jobs(client, actor_id, boards):
    run = client.actor(actor_id).call(run_input={
        "boardSlugs": boards,
        "mode": "jobs",
        "onlyNewSinceLastRun": True,
        "stateKey": STATE_KEY,
        "maxJobsPerBoard": 500,
    })
    dataset_id = _attr(run, "default_dataset_id", "defaultDatasetId")
    return list(client.dataset(dataset_id).iterate_items())


def main():
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    webhook = os.environ["SLACK_WEBHOOK"]

    rows = new_jobs(client, "zet46/greenhouse-jobs-scraper", GREENHOUSE_BOARDS)
    rows += new_jobs(client, "zet46/ashby-jobs-scraper", ASHBY_BOARDS)

    for j in rows:
        url = j.get("absoluteUrl") or j.get("jobUrl") or ""
        loc = j.get("locationName") or j.get("location") or "—"
        pay = ""
        if j.get("salaryMin"):
            pay = f' · {int(j["salaryMin"]):,}–{int(j["salaryMax"]):,} {j.get("salaryCurrency","")}'
        requests.post(webhook, json={
            "text": f'*{j["boardSlug"]}* — <{url}|{j["title"]}>\n{loc}{pay}'
        }, timeout=10)

    print(f"Posted {len(rows)} new job(s).")


if __name__ == "__main__":
    main()
