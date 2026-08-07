"""
Registry of configured metros. Add a new metro by creating
config/metros/<slug>.py (copy an existing one as a template) and adding it
to METRO_REGISTRY below.
"""
from . import baldwin_county_al, hickory_nc, little_rock_ar, oklahoma_city_ok

METRO_REGISTRY = {
    little_rock_ar.METRO_SLUG: little_rock_ar,
    hickory_nc.METRO_SLUG: hickory_nc,
    baldwin_county_al.METRO_SLUG: baldwin_county_al,
    oklahoma_city_ok.METRO_SLUG: oklahoma_city_ok,
}


def get_metro(slug):
    try:
        return METRO_REGISTRY[slug]
    except KeyError:
        raise SystemExit(
            f"Unknown metro '{slug}'. Available: {', '.join(METRO_REGISTRY)}"
        )
