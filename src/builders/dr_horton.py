"""
D.R. Horton community discovery.

Strategy: drhorton.com is a client-rendered site, so its search/finder pages
don't expose data to a plain HTTP GET. Its XML sitemap does, though, and
every active community's model-home and quick-move-in ("qmi") pages are
listed in it as plain server-rendered URLs of the form:

    /<state>/<region>/<city>/<community>
    /<state>/<region>/<city>/<community>/qmis/<house-number>-<street-slug>

We use the sitemap to enumerate communities and their qmi addresses (which
give us street names), then fetch each community's own page once to read
its zip code out of the embedded JSON-LD PostalAddress block.
"""
import re

from src.http_client import get_text

BASE = "https://www.drhorton.com"
SITEMAP_URL = f"{BASE}/sitemaps/website.xml"

_HOUSE_NUMBER_RE = re.compile(r"^\d+[a-zA-Z]?$")
_ZIP_RE = re.compile(r'"postalCode"\s*:\s*"(\d{5})"', re.IGNORECASE)
_CITY_RE = re.compile(r'"addressLocality"\s*:\s*"([^"]+)"', re.IGNORECASE)


def _slug_to_title(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def _qmi_slug_to_street(slug):
    """'6301-warwick-dr' -> 'Warwick Dr' (drops the leading house number)."""
    parts = slug.split("-")
    i = 0
    while i < len(parts) and _HOUSE_NUMBER_RE.match(parts[i]):
        i += 1
    return " ".join(w.capitalize() for w in parts[i:])


def _fetch_sitemap_urls(session):
    xml = get_text(session, SITEMAP_URL)
    if not xml:
        return []
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def discover(metro_config, session):
    """Returns a list of dicts, one per community:
    {community_name, builder, city, zip, phase, streets: [...], source_url}
    """
    region_path = metro_config.DR_HORTON_REGION_PATH
    prefix_https = f"{BASE}/{region_path}/"
    prefix_http = prefix_https.replace("https://", "http://")
    # A builder's "region" path can be much bigger than the actual metro
    # (e.g. Hickory, NC is filed under D.R. Horton's whole "Charlotte"
    # region alongside Charlotte, Gastonia, Monroe, ...), so region_path
    # alone isn't a safe filter - only keep cities in metro_config.CITIES.
    allowed_cities = {c.lower() for c in getattr(metro_config, "CITIES", [])}

    urls = _fetch_sitemap_urls(session)
    region_urls = [
        u for u in urls if u.startswith(prefix_https) or u.startswith(prefix_http)
    ]

    # (city_slug, community_slug) -> set of street names
    communities = {}
    for u in region_urls:
        tail = u.split(f"/{region_path}/", 1)[1].strip("/")
        segs = tail.split("/")
        if len(segs) < 2:
            continue  # city hub page, e.g. .../little-rock
        city_slug, community_slug = segs[0], segs[1]
        if community_slug in ("floor-plans", "qmis"):
            continue
        if allowed_cities and _slug_to_title(city_slug).lower() not in allowed_cities:
            continue
        streets = communities.setdefault((city_slug, community_slug), set())
        if len(segs) >= 4 and segs[2] == "qmis":
            streets.add(_qmi_slug_to_street(segs[3]))

    results = []
    for (city_slug, community_slug), streets in sorted(communities.items()):
        community_url = f"{BASE}/{region_path}/{city_slug}/{community_slug}"
        html = get_text(session, community_url)
        zip_code = ""
        city_name = _slug_to_title(city_slug)
        if html:
            zm = _ZIP_RE.search(html)
            if zm:
                zip_code = zm.group(1)
            cm = _CITY_RE.search(html)
            if cm:
                city_name = cm.group(1).title()
        results.append({
            "community_name": _slug_to_title(community_slug),
            "builder": "D.R. Horton",
            "city": city_name,
            "zip": zip_code,
            "phase": "",  # no phase-relisted communities found live for this metro yet
            "streets": sorted(streets),
            "source_url": community_url,
        })
    return results
