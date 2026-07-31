"""Orchestrates Step 1: run every configured builder module for a metro and
flatten the results into one row per (community, street)."""
import importlib

from src.http_client import new_session


def discover_communities(metro_config, session=None):
    session = session or new_session()
    all_communities = []
    for builder_name in metro_config.BUILDERS:
        module = importlib.import_module(f"src.builders.{builder_name}")
        found = module.discover(metro_config, session)
        print(f"  {builder_name}: {len(found)} communities")
        all_communities.extend(found)
    return all_communities


def communities_to_rows(metro_config, communities):
    rows = []
    for c in communities:
        streets = c["streets"] or [""]
        for street in streets:
            rows.append({
                "metro_area": metro_config.METRO_AREA,
                "community_name": c["community_name"],
                "builder": c["builder"],
                "phase": c["phase"],
                "street_name": street,
            })
    return rows
