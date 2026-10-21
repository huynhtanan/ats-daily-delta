"""Probe candidate ATS slugs via Greenhouse + Ashby public APIs.
Both are free + plain datacenter OK; just httpx.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
import httpx

# Greenhouse: boards-api.greenhouse.io/v1/boards/<slug>/jobs
# Ashby: api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true

GH_CANDIDATES = [
    # Dev tools / infra
    "cloudflare", "hashicorp", "fastly", "snowflake", "confluent",
    "fivetran", "airbyte", "retool", "postman", "benchling",
    "pagerduty", "atlassian", "mongodb-ventures", "okta", "auth0",
    "rippling", "deel", "remotecom", "carta", "pulley",
    # Fintech / commerce
    "doordash", "snap", "uber", "quora", "clickup", "notion-dot-so",
    "medium", "cash", "truework", "modernhealth", "oscarhealth",
    # AI
    "openai-careers", "scaleai", "huggingface", "replicateinc",
    "together", "mistral", "groq-inc", "pika-labs",
    # Vertical
    "shopify", "miro", "canva", "productboard", "atlassian-inc",
    "docusign", "zendesk", "zoomus",
    # Climate / health
    "lemonade", "nerdwallet", "coursera", "udemy",
]

ASHBY_CANDIDATES = [
    # Infra / dev
    "replicate", "together", "mistral", "groq", "fly", "railway",
    "vercel", "netlify", "render", "koyeb",
    # Auth / SaaS
    "clerk", "workos", "propelauth", "stytch", "resend", "loops",
    "pylon-inc", "frontapp", "pylon", "beam",
    # AI
    "scale", "scaleai", "humanloop", "mistralai", "duckbill",
    "stackblitz", "turso", "liquid-ai", "liquidai",
    # Media / dev
    "descript", "loom", "framer", "pitch", "arc", "arcbrowser",
    # New AI
    "neo4j", "redis", "redisinc", "chroma", "weaviate",
    # More
    "basedash", "whop", "mercury-labs", "mercor", "mercor-ai",
    "typeform", "mem0", "mem", "zepai", "flowise",
    # Mix
    "stytch-inc", "neon", "neondatabase", "planetscale", "turso-tech",
]

TIMEOUT = 10.0
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def probe_gh(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            if len(jobs) > 0:
                return ("Greenhouse", slug, len(jobs), "ok")
            return ("Greenhouse", slug, 0, "empty")
        return ("Greenhouse", slug, 0, f"http {r.status_code}")
    except Exception as e:
        return ("Greenhouse", slug, 0, f"err {type(e).__name__}")


def probe_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        r = httpx.get(url, timeout=TIMEOUT, headers={"User-Agent": UA})
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            if len(jobs) > 0:
                return ("Ashby", slug, len(jobs), "ok")
            return ("Ashby", slug, 0, "empty")
        return ("Ashby", slug, 0, f"http {r.status_code}")
    except Exception as e:
        return ("Ashby", slug, 0, f"err {type(e).__name__}")


def main():
    results = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        gh_futs = [ex.submit(probe_gh, s) for s in GH_CANDIDATES]
        ashby_futs = [ex.submit(probe_ashby, s) for s in ASHBY_CANDIDATES]
        for f in gh_futs + ashby_futs:
            results.append(f.result())

    verified = [r for r in results if r[3] == "ok"]
    verified.sort(key=lambda x: -x[2])

    print(f"Verified: {len(verified)}")
    for ats, slug, n, _ in verified:
        print(f"  {ats:12} {slug:30} {n:5}")

    rejects = [r for r in results if r[3] != "ok"]
    print(f"\nRejected: {len(rejects)}")
    reasons = {}
    for ats, slug, _, reason in rejects:
        reasons.setdefault(reason, []).append(f"{ats}/{slug}")
    for reason, items in reasons.items():
        print(f"  {reason}: {len(items)} ({items[:5]})")

    out = [{"slug": s, "ats": a, "count": n} for a, s, n, _ in verified]
    with open("workspace/content/jobs-ats-tracker/new_verified_slugs.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {len(out)} to new_verified_slugs.json")


if __name__ == "__main__":
    main()
