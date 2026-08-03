"""
Tracks every rental-data file a metro has been given (Apify export, MLS
export, ...) so rerun_imports.py can replay all of them at once - this is
what makes "add a street, then re-check everything" work: newly-known
streets get matched against data you already gave me, not just new
uploads.
"""
import csv
import os

MANIFEST_COLUMNS = ["filename", "source_type", "label", "added_date"]
# apify/mls/manual feed rentals.csv (rental activity); sales feeds
# community-totals.csv (the new-construction sales pipeline). "manual" is
# for listings entered by hand (e.g. pasted directly in chat, no export
# file to keep) - stored pre-matched in RENTALS_COLUMNS shape, so a
# rebuild-from-sources never silently drops them again.
VALID_SOURCE_TYPES = {"apify", "mls", "sales", "manual"}


def _sources_dir(metro_slug):
    return os.path.join("sources", metro_slug)


def _manifest_path(metro_slug):
    return os.path.join(_sources_dir(metro_slug), "manifest.csv")


def load_manifest(metro_slug):
    path = _manifest_path(metro_slug)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def add_source(metro_slug, filename, source_type, label, added_date):
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {VALID_SOURCE_TYPES}, got {source_type!r}")

    os.makedirs(_sources_dir(metro_slug), exist_ok=True)
    manifest = load_manifest(metro_slug)
    if any(m["filename"] == filename for m in manifest):
        return  # already registered
    manifest.append({
        "filename": filename, "source_type": source_type,
        "label": label, "added_date": added_date,
    })
    with open(_manifest_path(metro_slug), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(manifest)


def source_path(metro_slug, filename):
    return os.path.join(_sources_dir(metro_slug), filename)
