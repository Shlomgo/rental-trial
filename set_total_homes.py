#!/usr/bin/env python3
"""
Set (or update) the manually-tracked total planned home count for a
community - used to compute % sold once sales-export data is imported.

Usage:
    python3 set_total_homes.py little-rock-ar "Cottage Walk" 400
    python3 set_total_homes.py little-rock-ar "New Community" 250 --builder Lennar
"""
import argparse
import csv
import os

from config.metros import get_metro
from src.community_totals import TOTALS_COLUMNS, set_total_homes_planned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug")
    parser.add_argument("community_name")
    parser.add_argument("total_homes", type=int)
    parser.add_argument("--builder", help="Required if the community isn't known yet")
    parser.add_argument("--phase", default="")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    metro_config = get_metro(args.metro_slug)
    communities_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-communities.csv")
    totals_path = os.path.join(args.output_dir, f"{metro_config.METRO_SLUG}-community-totals.csv")

    builder, phase, community_name = args.builder, args.phase, args.community_name
    if os.path.exists(communities_path):
        with open(communities_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        existing = [r for r in rows if r["community_name"].lower() == args.community_name.lower()]
        if existing:
            builder = builder or existing[0]["builder"]
            phase = phase or existing[0]["phase"]
            community_name = existing[0]["community_name"]

    if not builder:
        raise SystemExit(
            f"'{args.community_name}' isn't in {communities_path} yet, so --builder is required."
        )

    set_total_homes_planned(totals_path, metro_config.METRO_AREA, community_name, builder, phase, args.total_homes)
    print(f"Set {community_name} ({builder}) total planned homes to {args.total_homes}.")


if __name__ == "__main__":
    main()
