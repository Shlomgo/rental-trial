#!/usr/bin/env python3
"""
Check a D.R. Horton community's QMI ("quick move-in" home) page and report
what changed in its for-sale roster since the last run: homes added,
removed, or with a price change.

Usage:
    python3 monitor_qmi_listing.py [<community-qmi-url>] [--output-dir output]

Defaults to the Brinkley Ridge (Kings Mountain, NC) community if no URL is
given.
"""
import argparse
import os
from datetime import date

from src.builders.dr_horton import fetch_qmi_page
from src.csv_io import upsert_qmi_listings
from src.http_client import new_session

DEFAULT_URL = (
    "https://www.drhorton.com/north-carolina/charlotte/kings-mountain/"
    "brinkley-ridge/qmis/444-brinkley-drive"
)


def _format_price(price):
    return f"${int(price):,}" if price not in (None, "") else "unknown price"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    session = new_session()
    page = fetch_qmi_page(args.url, session)
    if page is None:
        raise SystemExit(f"Could not fetch {args.url}")
    if not page["listings"]:
        raise SystemExit(
            f"Fetched {args.url} but found no home listings - "
            "the page structure may have changed."
        )

    today_str = date.today().isoformat()
    os.makedirs(args.output_dir, exist_ok=True)
    csv_slug = page["community_name"].lower().replace(" ", "-")
    csv_path = os.path.join(args.output_dir, f"{csv_slug}-qmi-listings.csv")

    changes = upsert_qmi_listings(
        csv_path, page["community_name"], page["city"], page["source_url"],
        page["listings"], today_str,
    )

    print(f"Checked {page['community_name']} ({page['city']}) - {args.url}")
    print(f"{len(page['listings'])} homes currently listed on the page.")
    print(f"Wrote {csv_path}")

    if not changes:
        print("No changes since the last check.")
        return

    added = [c for c in changes if c["type"] == "added"]
    removed = [c for c in changes if c["type"] == "removed"]
    price_changed = [c for c in changes if c["type"] == "price_changed"]

    if added:
        print(f"\nAdded ({len(added)}):")
        for c in added:
            print(f"  + {c['full_address']} - {_format_price(c['new_price'])}")
    if removed:
        print(f"\nRemoved ({len(removed)}):")
        for c in removed:
            print(f"  - {c['full_address']} (last seen at {_format_price(c['old_price'])})")
    if price_changed:
        print(f"\nPrice changes ({len(price_changed)}):")
        for c in price_changed:
            print(f"  ~ {c['full_address']}: {_format_price(c['old_price'])} -> {_format_price(c['new_price'])}")


if __name__ == "__main__":
    main()
