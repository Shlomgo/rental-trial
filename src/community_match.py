"""
Matches free-text subdivision names (as they appear in MLS exports, e.g.
"COTTAGE WALK SUBDIVISION PHASE 1") against communities we already know
about from Step 1's builder-sitemap discovery.

Why this matters: builder sitemaps only list currently-for-sale inventory,
so a street that already sold out drops off the sitemap before Step 1 ever
sees it. MLS subdivision names are a permanent transaction record - they
don't disappear - so matching on them (instead of only matching on already-
known street names) is how a sold-out street gets captured at all.
"""
import re

_FILLER_WORDS = {"the", "at", "of", "in", "a"}


def _tokenize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return {w for w in s.split() if w and w not in _FILLER_WORDS}


def load_known_communities(communities_csv_path):
    """Returns a deduped list of {community_name, builder, phase} dicts,
    one per distinct community (collapsing its per-street rows)."""
    import csv
    seen = {}
    with open(communities_csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["community_name"], row["builder"])
            if key not in seen:
                seen[key] = {
                    "community_name": row["community_name"],
                    "builder": row["builder"],
                    "phase": row.get("phase", ""),
                }
    return list(seen.values())


def find_subdivision_matches(subdivision_text, communities):
    """Returns every known community whose name-tokens are a subset of the
    subdivision text's tokens. 0 matches = unrecognized subdivision;
    2+ matches = ambiguous (caller should not guess between them)."""
    sub_tokens = _tokenize(subdivision_text)
    if not sub_tokens:
        return []
    return [
        c for c in communities
        if _tokenize(c["community_name"]) and _tokenize(c["community_name"]).issubset(sub_tokens)
    ]


def match_subdivision(subdivision_text, communities):
    """Returns the single matching community dict, or None if the
    subdivision text matches zero or more than one known community (an
    ambiguous match is treated as no match - we don't guess)."""
    matches = find_subdivision_matches(subdivision_text, communities)
    return matches[0] if len(matches) == 1 else None


_PHASE_RE = re.compile(r"\b(?:phase|ph)\.?\s*([a-z0-9][a-z0-9-]*)\b", re.IGNORECASE)


def extract_phase(subdivision_text):
    m = _PHASE_RE.search(subdivision_text)
    return m.group(1).upper() if m else ""
