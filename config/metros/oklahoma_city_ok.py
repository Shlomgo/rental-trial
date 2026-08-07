"""
Metro configuration: Oklahoma City, OK.

To add a new metro, copy this file (e.g. config/metros/dallas_fort_worth_tx.py),
change the values below to match that metro's builder-site URLs, and add the
new module to METRO_REGISTRY in config/metros/__init__.py. Nothing in src/
needs to change.
"""

METRO_AREA = "Oklahoma City, OK"
METRO_SLUG = "oklahoma-city-ok"

# Cities/towns considered part of this metro. Used only as a human-readable
# sanity check on discovered results, not for filtering... except here it
# doubles as the actual city filter for builder discovery, since D.R. Horton
# and Lennar file the whole OKC region (core city + close-in suburbs) under
# one region path.
CITIES = [
    "Oklahoma City", "Edmond", "Norman", "Moore", "Mustang", "Yukon",
    "Piedmont", "Newcastle", "Blanchard", "Choctaw", "Midwest City",
    "Del City", "Bethany", "Warr Acres", "Jones", "Harrah", "Guthrie",
    "Tuttle", "Noble",
]

# Which builder modules (in src/builders/) to run for this metro.
BUILDERS = ["dr_horton", "lennar"]

# The URL path segment each builder site uses for this metro's region.
#   D.R. Horton:  https://www.drhorton.com/oklahoma/oklahoma-city/<city>/<community>
#   Lennar:       https://www.lennar.com/new-homes/oklahoma/oklahoma-city/<city>/<community>
DR_HORTON_REGION_PATH = "oklahoma/oklahoma-city"
LENNAR_REGION_PATH = "new-homes/oklahoma/oklahoma-city"

# Lennar's sitemap groups some non-city sections (promos, events) under the
# same URL depth as real cities. List slugs to skip here.
LENNAR_EXCLUDE_CITY_SLUGS = {"promo", "event"}

# Rental sources to check in Step 2, in priority order.
RENTAL_SOURCES = ["zillow", "realtor", "apartments_com", "rent_com"]

# Published Claude Artifact URL for this metro's dashboard (generate_dashboard.py
# output). Set once you've published it; generate_index.py links out to this.
DASHBOARD_ARTIFACT_URL = "https://claude.ai/code/artifact/a5e67897-d8ae-4c71-ac88-0059c722b6bc"
