"""
Metro configuration: Hickory, NC.

To add a new metro, copy this file (e.g. config/metros/dallas_fort_worth_tx.py),
change the values below to match that metro's builder-site URLs, and add the
new module to METRO_REGISTRY in config/metros/__init__.py. Nothing in src/
needs to change.
"""

METRO_AREA = "Hickory, NC"
METRO_SLUG = "hickory-nc"

# Cities considered part of this metro (Catawba County core). Used only as a
# human-readable sanity check on discovered results, not for filtering.
CITIES = [
    "Hickory", "Newton", "Conover", "Claremont", "Longview", "Catawba",
    "Maiden", "Startown", "Brookford",
]

# Which builder modules (in src/builders/) to run for this metro.
BUILDERS = ["dr_horton", "lennar"]

# The URL path segment each builder site uses for this metro's region.
# Both D.R. Horton and Lennar group Hickory under their "Charlotte" region:
#   D.R. Horton:  https://www.drhorton.com/north-carolina/charlotte/hickory/<community>
#   Lennar:       https://www.lennar.com/new-homes/north-carolina/charlotte/hickory/<community>
DR_HORTON_REGION_PATH = "north-carolina/charlotte"
LENNAR_REGION_PATH = "new-homes/north-carolina/charlotte"

# Lennar's sitemap groups some non-city sections (promos, events) under the
# same URL depth as real cities. List slugs to skip here.
LENNAR_EXCLUDE_CITY_SLUGS = {"promo", "event"}

# Rental sources to check in Step 2, in priority order.
RENTAL_SOURCES = ["zillow", "realtor", "apartments_com", "rent_com"]

# Published Claude Artifact URL for this metro's dashboard (generate_dashboard.py
# output). Set once you've published it; generate_index.py links out to this.
DASHBOARD_ARTIFACT_URL = ""
