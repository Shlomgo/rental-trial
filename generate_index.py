#!/usr/bin/env python3
"""
Generates a landing page linking out to every configured metro's dashboard,
with an at-a-glance summary per metro (community count, active rentals,
aggregate % sold, last-updated date). Re-run any time a metro's data changes
so the summary numbers stay current - the per-metro dashboards it links to
are still generated separately by generate_dashboard.py.

Usage:
    python3 generate_index.py
"""
import csv
import datetime
import json
import os

from config.metros import METRO_REGISTRY


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def metro_summary(metro_config, output_dir="output"):
    slug = metro_config.METRO_SLUG
    communities = read_csv(os.path.join(output_dir, f"{slug}-communities.csv"))
    rentals = read_csv(os.path.join(output_dir, f"{slug}-rentals.csv"))
    totals = read_csv(os.path.join(output_dir, f"{slug}-community-totals.csv"))
    if not communities:
        return None

    community_count = len({(r["community_name"], r["builder"]) for r in communities})
    builders = sorted({r["builder"] for r in communities})
    active_rentals = sum(1 for r in rentals if r.get("status") == "currently for rent")

    # Only communities with a known total_homes_planned can contribute to
    # a meaningful % sold - mixing in sold_count from communities with no
    # planned total would inflate the numerator against a smaller denominator.
    with_planned = [t for t in totals if t.get("total_homes_planned")]
    sold = sum(int(t["sold_count"] or 0) for t in with_planned)
    planned = sum(int(t["total_homes_planned"]) for t in with_planned)
    pct_sold = round(sold / planned * 100, 1) if planned else None

    last_updated = max(
        (r.get("last_checked_date", "") for r in rentals),
        default="",
    )

    return {
        "metro_area": metro_config.METRO_AREA,
        "builders": builders,
        "community_count": community_count,
        "active_rentals": active_rentals,
        "sold": sold,
        "planned": planned,
        "pct_sold": pct_sold,
        "last_updated": last_updated,
        "dashboard_url": getattr(metro_config, "DASHBOARD_ARTIFACT_URL", ""),
    }


TEMPLATE = r"""<title>New-Construction Rental Tracker</title>
<style>
@media (prefers-color-scheme: light) {
  :root { color-scheme: light; }
}
:root {
  --paper: #E7ECE2;
  --paper-raised: #FBFCF8;
  --ink: #16211C;
  --ink-soft: #56655C;
  --ink-faint: #8B978D;
  --line: #DAE0D6;
  --line-strong: #C2CBBC;
  --accent: #2B6E4E;
  --accent-ink: #FFFFFF;
  --accent-soft: #E1EEE6;
  --clay: #A85434;
  --clay-soft: #F3E4DB;
  --slate: #3E5C74;
  --slate-soft: #E1E8ED;
  --shadow: 0 1px 2px rgba(22,33,28,0.06), 0 1px 1px rgba(22,33,28,0.04);
  --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "JetBrains Mono", Consolas, "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --paper: #10160F;
    --paper-raised: #16201A;
    --ink: #E6ECE4;
    --ink-soft: #93A398;
    --ink-faint: #5E6D64;
    --line: #263028;
    --line-strong: #34413A;
    --accent: #59BC8C;
    --accent-ink: #0C1710;
    --accent-soft: #16281F;
    --clay: #E2895A;
    --clay-soft: #2C1F17;
    --slate: #86ADCE;
    --slate-soft: #182530;
    --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 1px 1px rgba(0,0,0,0.3);
  }
}
:root[data-theme="dark"] {
  --paper: #10160F; --paper-raised: #16201A; --ink: #E6ECE4; --ink-soft: #93A398;
  --ink-faint: #5E6D64; --line: #263028; --line-strong: #34413A; --accent: #59BC8C;
  --accent-ink: #0C1710; --accent-soft: #16281F; --clay: #E2895A; --clay-soft: #2C1F17;
  --slate: #86ADCE; --slate-soft: #182530;
  --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 1px 1px rgba(0,0,0,0.3);
  color-scheme: dark;
}
:root[data-theme="light"] {
  --paper: #E7ECE2; --paper-raised: #FBFCF8; --ink: #16211C; --ink-soft: #56655C;
  --ink-faint: #8B978D; --line: #DAE0D6; --line-strong: #C2CBBC; --accent: #2B6E4E;
  --accent-ink: #FFFFFF; --accent-soft: #E1EEE6; --clay: #A85434; --clay-soft: #F3E4DB;
  --slate: #3E5C74; --slate-soft: #E1E8ED;
  --shadow: 0 1px 2px rgba(22,33,28,0.06), 0 1px 1px rgba(22,33,28,0.04);
  color-scheme: light;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--paper);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
}
::selection { background: var(--accent-soft); color: var(--ink); }

.wrap { max-width: 900px; margin: 0 auto; padding: 40px 24px 80px; }

header.page {
  display: flex; flex-direction: column; gap: 6px;
  margin-bottom: 32px; padding-bottom: 24px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em;
  text-transform: uppercase; color: var(--accent); font-weight: 600;
}
h1 {
  font-family: var(--serif); font-weight: 400; font-size: 34px;
  letter-spacing: -0.01em; margin: 2px 0 4px; color: var(--ink); text-wrap: balance;
}
.subhead { color: var(--ink-soft); font-size: 14.5px; max-width: 62ch; }

.metro-list { display: flex; flex-direction: column; gap: 10px; }

.metro-card {
  display: flex; align-items: center; gap: 20px;
  background: var(--paper-raised);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: var(--shadow);
  padding: 18px 20px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s ease;
}
.metro-card:hover { border-color: var(--accent); }
.metro-card.disabled { opacity: 0.55; pointer-events: none; }

.metro-main { flex: 1; min-width: 0; }
.metro-name {
  font-family: var(--serif); font-weight: 400; font-size: 19px; color: var(--ink);
}
.metro-builders {
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-faint);
  margin-top: 3px; letter-spacing: 0.02em;
}

.metro-stats {
  display: flex; gap: 26px; flex: none;
}
.stat { text-align: right; min-width: 64px; }
.stat .n {
  font-family: var(--serif); font-size: 20px; color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.stat .n.faint { color: var(--ink-faint); }
.stat .l {
  font-family: var(--mono); font-size: 10px; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ink-faint); margin-top: 2px;
}

.metro-arrow {
  flex: none; width: 9px; height: 9px;
  border-right: 1.5px solid var(--ink-faint);
  border-top: 1.5px solid var(--ink-faint);
  transform: rotate(45deg);
}

.metro-updated {
  font-family: var(--mono); font-size: 11px; color: var(--ink-faint);
  margin-top: 4px;
}

.empty-note {
  font-family: var(--mono); font-size: 12.5px; color: var(--ink-faint);
  padding: 14px 0;
}

footer.page {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--line);
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-faint);
}

@media (max-width: 560px) {
  .metro-card { flex-wrap: wrap; }
  .metro-stats { gap: 16px; }
}
</style>

<div class="wrap">
  <header class="page">
    <span class="eyebrow">New-construction rental tracker</span>
    <h1>Metros</h1>
    <div class="subhead">One dashboard per metro, tracking D.R. Horton and Lennar communities: rental activity and the new-construction sales pipeline.</div>
  </header>

  <div class="metro-list">
    __METRO_CARDS__
  </div>

  <footer class="page">Generated __GENERATED_DATE__</footer>
</div>
"""


def card_html(summary):
    pct = f"{summary['pct_sold']}%" if summary["pct_sold"] is not None else "&mdash;"
    href = summary["dashboard_url"] or "#"
    disabled_class = "" if summary["dashboard_url"] else " disabled"
    return f"""
    <a class="metro-card{disabled_class}" href="{href}" target="_blank" rel="noopener">
      <div class="metro-main">
        <div class="metro-name">{summary['metro_area']}</div>
        <div class="metro-builders">{' &middot; '.join(summary['builders'])}</div>
        <div class="metro-updated">Updated {summary['last_updated'] or '&mdash;'}</div>
      </div>
      <div class="metro-stats">
        <div class="stat"><div class="n">{summary['community_count']}</div><div class="l">Communities</div></div>
        <div class="stat"><div class="n">{summary['active_rentals']}</div><div class="l">For rent</div></div>
        <div class="stat"><div class="n{'' if summary['pct_sold'] is not None else ' faint'}">{pct}</div><div class="l">Sold</div></div>
      </div>
      <span class="metro-arrow"></span>
    </a>"""


def generate(output_dir="output"):
    summaries = []
    for metro_config in METRO_REGISTRY.values():
        summary = metro_summary(metro_config, output_dir)
        if summary:
            summaries.append(summary)
    summaries.sort(key=lambda s: s["metro_area"])

    if summaries:
        cards = "".join(card_html(s) for s in summaries)
    else:
        cards = '<div class="empty-note">No metros have data yet - run run_discovery.py for one first.</div>'

    generated = datetime.date.today().isoformat()
    out = TEMPLATE.replace("__METRO_CARDS__", cards)
    out = out.replace("__GENERATED_DATE__", generated)

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path


if __name__ == "__main__":
    path = generate()
    print(f"Wrote {path}")
