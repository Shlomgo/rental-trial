"""
Metro configuration: Little Rock, AR.

To add a new metro, copy this file (e.g. config/metros/dallas_fort_worth_tx.py),
change the values below to match that metro's builder-site URLs, and add the
new module to METRO_REGISTRY in config/metros/__init__.py. Nothing in src/
needs to change.
"""

METRO_AREA = "Little Rock, AR"
METRO_SLUG = "little-rock-ar"

# Cities considered part of this metro. Used only as a human-readable sanity
# check on discovered results, not for filtering.
CITIES = [
    "Little Rock", "North Little Rock", "Maumelle", "Bryant", "Benton",
    "Cabot", "Ward", "Beebe", "Searcy", "Mayflower", "Conway", "Alexander",
    "Bauxite", "Hensley", "Sherwood", "Jacksonville", "Mabelvale",
    "Haskell", "East End",
]

# Which builder modules (in src/builders/) to run for this metro.
BUILDERS = ["dr_horton", "lennar"]

# The URL path segment each builder site uses for this metro's region.
# Found by browsing to the builder's "homes for sale in <metro>" landing page:
#   D.R. Horton:  https://www.drhorton.com/<DR_HORTON_REGION_PATH>
#   Lennar:       https://www.lennar.com/<LENNAR_REGION_PATH>
DR_HORTON_REGION_PATH = "arkansas/central-arkansas"
LENNAR_REGION_PATH = "new-homes/arkansas/little-rock"

# Lennar's sitemap groups some non-city sections (promos, events) under the
# same URL depth as real cities. List slugs to skip here.
LENNAR_EXCLUDE_CITY_SLUGS = {"promo", "event", "little-rock-singlefamily"}

# Rental sources to check in Step 2, in priority order.
RENTAL_SOURCES = ["zillow", "realtor", "apartments_com", "rent_com"]

# Published Claude Artifact URL for this metro's dashboard (generate_dashboard.py
# output). Set once you've published it; generate_index.py links out to this.
DASHBOARD_ARTIFACT_URL = "https://claude.ai/code/artifact/5170beda-e22d-451a-8104-a44e243cd0b6"
