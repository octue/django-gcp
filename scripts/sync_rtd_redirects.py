"""Sync the redirect map in rtd_redirects.toml to the Read the Docs project.

Read the Docs stores user-defined redirects in the project configuration (not in the
repository), so after changing rtd_redirects.toml somebody must push the map to RTD.
This script does that idempotently: it creates missing redirects, updates any whose
target or type differs, and leaves everything else untouched. It never deletes
redirects that are absent from the map, so manually-added redirects survive.

Usage:

    READTHEDOCS_TOKEN=<token> python scripts/sync_rtd_redirects.py [--dry-run]

The token is a Read the Docs API token (https://app.readthedocs.org/accounts/tokens/)
belonging to a maintainer of the django-gcp project. Uses only the standard library.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import tomllib
import urllib.request

API_BASE = "https://readthedocs.org/api/v3/projects/django-gcp/redirects/"
REDIRECTS_FILE = Path(__file__).parent / "rtd_redirects.toml"


def request(url, token, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        body = response.read()
        return json.loads(body) if body else None


def fetch_existing(token):
    """Return existing page redirects keyed by from_url, following pagination."""
    existing = {}
    url = API_BASE
    while url:
        page = request(url, token)
        for redirect in page["results"]:
            if redirect["type"] == "page":
                existing[redirect["from_url"]] = redirect
        url = page.get("next")
    return existing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report actions without applying them")
    args = parser.parse_args()

    token = os.environ.get("READTHEDOCS_TOKEN")
    if not token:
        sys.exit("Set the READTHEDOCS_TOKEN environment variable to a Read the Docs API token.")

    wanted = tomllib.loads(REDIRECTS_FILE.read_text())["redirects"]
    existing = fetch_existing(token)

    unchanged = 0
    for from_url, to_url in wanted.items():
        payload = {"from_url": from_url, "to_url": to_url, "type": "page", "http_status": 301}
        current = existing.get(from_url)
        if current is None:
            print(f"create {from_url} -> {to_url}")
            if not args.dry_run:
                request(API_BASE, token, method="POST", payload=payload)
        elif current["to_url"] != to_url or current.get("http_status") != 301:
            print(f"update {from_url} -> {to_url} (was -> {current['to_url']})")
            if not args.dry_run:
                request(f"{API_BASE}{current['pk']}/", token, method="PUT", payload=payload)
        else:
            unchanged += 1

    print(f"{unchanged} of {len(wanted)} redirects already in place.")


if __name__ == "__main__":
    main()
