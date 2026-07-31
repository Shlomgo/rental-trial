"""
Registry of configured metros. Add a new metro by creating
config/metros/<slug>.py (copy an existing one as a template) and adding it
to METRO_REGISTRY below.
"""
from . import little_rock_ar

METRO_REGISTRY = {
    little_rock_ar.METRO_SLUG: little_rock_ar,
}


def get_metro(slug):
    try:
        return METRO_REGISTRY[slug]
    except KeyError:
        raise SystemExit(
            f"Unknown metro '{slug}'. Available: {', '.join(METRO_REGISTRY)}"
        )
