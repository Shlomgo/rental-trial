"""
Lennar community discovery.

Like drhorton.com, lennar.com is client-rendered, but its XML sitemap lists
plain server-rendered URLs for every city, community, and floor plan:

    /new-homes/<state>/<metro>/<city>
    /new-homes/<state>/<metro>/<city>/<community>
    /new-homes/<state>/<metro>/<city>/<community>/<plan-slug>
    /new-homes/<state>/<metro>/<city>/<community>/<plan-slug>/<lot-id>

Unlike D.R. Horton, Lennar's per-lot URL ends in an opaque numeric lot ID,
not a street slug, so the street name isn't visible in the sitemap URL
itself. Each community page embeds its zip code in a Next.js/Apollo GraphQL
state blob; each individual lot page embeds that lot's street address the
same way. So: one fetch per community for zip, plus one fetch per lot URL
to collect street names.
"""
import re

from src.http_client import get_text

BASE = "https://www.lennar.com"
SITEMAP_URL = f"{BASE}/api/images/sitemapfe.xml"

_ZIP_RE = re.compile(r'"zipCode"\s*:\s*"(\d{5})"')
_STREET_ADDRESS_RE = re.compile(r'"streetAddress"\s*:\s*"([^"]+)"')
_LEADING_HOUSE_NUMBER_RE = re.compile(r"^\d+\s+")


def _slug_to_title(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def _fetch_sitemap_urls(session):
    xml = get_text(session, SITEMAP_URL)
    if not xml:
        return []
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def discover(metro_config, session):
    """Returns a list of dicts, one per community:
    {community_name, builder, city, zip, phase, streets: [...], source_url}
    """
    region_path = metro_config.LENNAR_REGION_PATH
    exclude_city_slugs = getattr(metro_config, "LENNAR_EXCLUDE_CITY_SLUGS", set())
    prefix = f"{BASE}/{region_path}/"

    urls = _fetch_sitemap_urls(session)
    region_urls = [u for u in urls if u.startswith(prefix)]

    communities = set()  # (city_slug, community_slug)
    lot_urls = {}  # (city_slug, community_slug) -> [lot url, ...]
    for u in region_urls:
        tail = u[len(prefix):].strip("/")
        segs = tail.split("/")
        if len(segs) < 2:
            continue
        city_slug, community_slug = segs[0], segs[1]
        if city_slug in exclude_city_slugs:
            continue
        key = (city_slug, community_slug)
        communities.add(key)
        if len(segs) == 4 and segs[3].isdigit():
            lot_urls.setdefault(key, []).append(u)

    results = []
    for city_slug, community_slug in sorted(communities):
        community_url = f"{BASE}/{region_path}/{city_slug}/{community_slug}"
        html = get_text(session, community_url)
        zip_code = ""
        if html:
            zm = _ZIP_RE.search(html)
            if zm:
                zip_code = zm.group(1)

        streets = set()
        for lot_url in lot_urls.get((city_slug, community_slug), []):
            lot_html = get_text(session, lot_url)
            if not lot_html:
                continue
            sm = _STREET_ADDRESS_RE.search(lot_html)
            if sm:
                street = _LEADING_HOUSE_NUMBER_RE.sub("", sm.group(1)).strip()
                if street:
                    streets.add(street)

        results.append({
            "community_name": _slug_to_title(community_slug),
            "builder": "Lennar",
            "city": _slug_to_title(city_slug),
            "zip": zip_code,
            "phase": "",  # no phase-relisted communities found live for this metro yet
            "streets": sorted(streets),
            "source_url": community_url,
        })
    return results
