#!/usr/bin/env python3
"""
Add a street to a known community's entry in communities.csv.

Usage:
    python3 add_street.py little-rock-ar "Cottage Walk" "Example Lane"
    python3 add_street.py little-rock-ar "Cottage Walk" "Example Lane" --builder Lennar --phase "Phase 2" --city Benton

If the community already exists, --builder/--phase/--city are inferred from
its existing rows and don't need to be passed. If it doesn't exist yet,
--builder is required (a community's builder can't be guessed); --city is
optional but recommended since nothing else can infer it for a brand-new
community.
"""
import argparse
import csv
import os

from config.metros import get_metro
from src import csv_io


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("community_name")
    parser.add_argument("street_name")
    parser.add_argument("--builder", help="Required if the community is new")
    parser.add_argument("--phase", default="", help="Optional phase name/number")
    parser.add_argument("--city", default="", help="City/town the community is in")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    communities_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv")
    if not os.path.exists(communities_path):
        raise SystemExit(f"{communities_path} not found - run run_discovery.py first.")

    with open(communities_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    existing_for_community = [r for r in rows if r["community_name"].lower() == args.community_name.lower()]

    if existing_for_community:
        builder = args.builder or existing_for_community[0]["builder"]
        phase = args.phase or existing_for_community[0]["phase"]
        city = args.city or next((r.get("city", "") for r in existing_for_community if r.get("city")), "")
        community_name = existing_for_community[0]["community_name"]  # canonical casing
    else:
        if not args.builder:
            known = sorted({r["community_name"] for r in rows})
            raise SystemExit(
                f"'{args.community_name}' isn't a known community yet, so --builder is required "
                f"to add it as new. Known communities: {', '.join(known)}"
            )
        builder = args.builder
        phase = args.phase
        city = args.city
        community_name = args.community_name

    already_there = any(
        r["community_name"] == community_name and r["builder"] == builder
        and r["street_name"].lower() == args.street_name.lower()
        for r in rows
    )
    if already_there:
        print(f"'{args.street_name}' is already on record for {community_name}.")
        return

    csv_io.upsert_communities(communities_path, [{
        "metro_area": metro_config.METRO_AREA,
        "community_name": community_name,
        "city": city,
        "builder": builder,
        "phase": phase,
        "street_name": args.street_name,
    }])
    print(f"Added '{args.street_name}' to {community_name} ({builder}).")
    print("Run rerun_imports.py to check this street against everything you've uploaded so far.")


if __name__ == "__main__":
    main()
