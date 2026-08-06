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
import json
import re

from src.http_client import get_text

BASE = "https://www.drhorton.com"
SITEMAP_URL = f"{BASE}/sitemaps/website.xml"

_HOUSE_NUMBER_RE = re.compile(r"^\d+[a-zA-Z]?$")
_ZIP_RE = re.compile(r'"postalCode"\s*:\s*"(\d{5})"', re.IGNORECASE)
_CITY_RE = re.compile(r'"addressLocality"\s*:\s*"([^"]+)"', re.IGNORECASE)
_COMMUNITY_URL_RE = re.compile(r"^https?://www\.drhorton\.com/[^/]+/[^/]+/([^/]+)/([^/]+)/qmis/")
_STREET_ADDR_RE = re.compile(r'"streetaddress"\s*:\s*"([^"]+)"', re.IGNORECASE)
_HOME_PRICE_RE = re.compile(r'class="home-price">\s*<div>\s*\$([\d,]+)')
_PROPERTY_DETAILS_RE = re.compile(r'class="property-details">(.*?)</div>', re.S)
_SQF_NUMBER_RE = re.compile(r'class="sqf-number">(.*?)</div>', re.S)
_VAR_MODEL_RE = re.compile(r"var model = \{")


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


def _extract_number(text, label):
    m = re.search(r"([\d.]+)\s*" + re.escape(label), text)
    return m.group(1) if m else ""


def _extract_balanced_object(text, start):
    """text[start] must be '{'. Returns the substring from start through its
    matching closing brace (respecting quoted strings, so braces inside JSON
    string values don't throw off the count), or None if unbalanced."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _status_from_json(item):
    raw = (item.get("Status") or "").strip().lower()
    if raw == "available":
        return "for sale"
    if raw:
        return raw
    return "sold" if item.get("JdeIsSold") else "for sale"


def _fetch_other_homes(html):
    """A community page embeds its 'other available homes here' widget as a
    JS object literal (`var model = {"Items":[...]}`), one per home, with
    clean structured fields - far less fragile than scraping the rendered
    HTML cards. A page can embed more than one such widget (e.g. a
    'similar floor plans' block with no per-lot address); only the one whose
    items carry an Address field is the real home roster."""
    for m in _VAR_MODEL_RE.finditer(html):
        obj_text = _extract_balanced_object(html, m.end() - 1)
        if not obj_text:
            continue
        try:
            data = json.loads(obj_text)
        except json.JSONDecodeError:
            continue
        items = data.get("Items") or []
        if not items or "Address" not in items[0]:
            continue
        return [
            {
                "full_address": it.get("Address", ""),
                "lot_number": (it.get("LotNumber") or "").strip(),
                "price": it.get("Price") or None,
                "status": _status_from_json(it),
                "beds": it.get("NumberOfBedrooms", ""),
                "baths": it.get("NumberOfBathrooms", ""),
                "garage": it.get("NumberOfGarages", ""),
                "story": it.get("NumberOfStories", ""),
                "sqft": it.get("SquareFootage"),
                "detail_url": f"{BASE}{it['Url']}" if it.get("Url") else "",
            }
            for it in items
        ]
    return []


def _fetch_hero_home(html, url):
    """The QMI page's own home is shown as a one-off 'hero' block, not as a
    card in the community's 'other homes here' widget (D.R. Horton excludes
    a page's own home from its own related-homes list) - so it needs
    separate parsing. Returns None if the page isn't a home-detail page
    (e.g. it's a plain community hub page with no single featured home)."""
    addr_match = _STREET_ADDR_RE.search(html)
    if not addr_match:
        return None

    price_match = _HOME_PRICE_RE.search(html)
    price = int(price_match.group(1).replace(",", "")) if price_match else None

    p1_text = p2_text = ""
    pd_match = _PROPERTY_DETAILS_RE.search(html)
    if pd_match:
        p1_text = re.sub(r"<[^>]+>", " ", pd_match.group(1))
    sqf_match = _SQF_NUMBER_RE.search(html)
    if sqf_match:
        p2_text = re.sub(r"<[^>]+>", " ", sqf_match.group(1))

    sqft_match = re.search(r"([\d,]+)\s*Sq\.?\s*Ft\.?", p2_text)
    lot_match = re.search(r"Lot\s+(\d+)", p2_text)

    return {
        "full_address": addr_match.group(1),
        "lot_number": lot_match.group(1) if lot_match else "",
        "price": price,
        "status": "for sale" if price else "unknown",
        "beds": _extract_number(p1_text, "Bed"),
        "baths": _extract_number(p1_text, "Bath"),
        "garage": _extract_number(p1_text, "Garage"),
        "story": _extract_number(p1_text, "Story"),
        "sqft": int(sqft_match.group(1).replace(",", "")) if sqft_match else None,
        "detail_url": url,
    }


def fetch_qmi_page(url, session):
    """Fetch a D.R. Horton QMI ('quick move-in' home) detail page and return
    the whole community's current home roster embedded on it: the page's own
    featured home plus every other available/under-contract home in the
    community, since D.R. Horton renders the whole community's roster on
    each one of its own QMI pages, not just a dedicated listing page.

    Returns None if the page couldn't be fetched. Returns a dict with an
    empty 'listings' list if the page fetched but didn't contain any
    recognizable home data (e.g. site layout changed).
    """
    html = get_text(session, url)
    if not html:
        return None

    m = _COMMUNITY_URL_RE.match(url)
    city_slug, community_slug = (m.group(1), m.group(2)) if m else ("", "")

    listings = _fetch_other_homes(html)
    hero = _fetch_hero_home(html, url)
    if hero and hero["full_address"] not in {l["full_address"] for l in listings}:
        listings.insert(0, hero)

    city_name = _slug_to_title(city_slug)
    cm = _CITY_RE.search(html)
    if cm:
        city_name = cm.group(1).title()
    zip_code = ""
    zm = _ZIP_RE.search(html)
    if zm:
        zip_code = zm.group(1)

    return {
        "community_name": _slug_to_title(community_slug),
        "city": city_name,
        "zip": zip_code,
        "source_url": url,
        "listings": listings,
    }
