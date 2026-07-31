#!/usr/bin/env python3
"""
Generates a self-contained HTML dashboard from a metro's communities.csv
and rentals.csv: communities grouped by builder, each showing its rental
count at a glance, expandable to the full rental detail table. Re-run this
any time either CSV changes so the dashboard reflects the latest data.

Usage:
    python3 generate_dashboard.py little-rock-ar
"""
import argparse
import csv
import datetime
import json
import os

from config.metros import get_metro


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


TEMPLATE = r"""<title>Little Rock New-Construction Rental Tracker</title>
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
  --status-active: #2B6E4E;
  --status-active-soft: #E1EEE6;
  --status-past: #5B6B62;
  --status-past-soft: #E6E9E3;
  --status-unknown: #9C6B18;
  --status-unknown-soft: #F3E9D4;
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
    --status-active: #59BC8C;
    --status-active-soft: #16281F;
    --status-past: #9AA79E;
    --status-past-soft: #1B231D;
    --status-unknown: #D9A94B;
    --status-unknown-soft: #2A2214;
    --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 1px 1px rgba(0,0,0,0.3);
  }
}
:root[data-theme="dark"] {
  --paper: #10160F; --paper-raised: #16201A; --ink: #E6ECE4; --ink-soft: #93A398;
  --ink-faint: #5E6D64; --line: #263028; --line-strong: #34413A; --accent: #59BC8C;
  --accent-ink: #0C1710; --accent-soft: #16281F; --clay: #E2895A; --clay-soft: #2C1F17;
  --slate: #86ADCE; --slate-soft: #182530; --status-active: #59BC8C; --status-active-soft: #16281F;
  --status-past: #9AA79E; --status-past-soft: #1B231D; --status-unknown: #D9A94B; --status-unknown-soft: #2A2214;
  --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 1px 1px rgba(0,0,0,0.3);
  color-scheme: dark;
}
:root[data-theme="light"] {
  --paper: #E7ECE2; --paper-raised: #FBFCF8; --ink: #16211C; --ink-soft: #56655C;
  --ink-faint: #8B978D; --line: #DAE0D6; --line-strong: #C2CBBC; --accent: #2B6E4E;
  --accent-ink: #FFFFFF; --accent-soft: #E1EEE6; --clay: #A85434; --clay-soft: #F3E4DB;
  --slate: #3E5C74; --slate-soft: #E1E8ED; --status-active: #2B6E4E; --status-active-soft: #E1EEE6;
  --status-past: #5B6B62; --status-past-soft: #E6E9E3; --status-unknown: #9C6B18; --status-unknown-soft: #F3E9D4;
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

.wrap { max-width: 1100px; margin: 0 auto; padding: 40px 24px 80px; }

header.page {
  display: flex; flex-direction: column; gap: 6px;
  margin-bottom: 28px; padding-bottom: 24px;
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
.meta-row {
  display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 14px;
  font-family: var(--mono); font-size: 12px; color: var(--ink-faint);
}
.meta-row span b { color: var(--ink-soft); font-weight: 600; }

/* ---- Toolbar ---- */
.toolbar {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 22px;
}
.search { flex: 1 1 260px; max-width: 380px; position: relative; }
.search input {
  width: 100%; font-family: var(--sans); font-size: 13.5px;
  padding: 8px 12px 8px 30px; border: 1px solid var(--line-strong);
  border-radius: 3px; background: var(--paper-raised); color: var(--ink);
}
.search input:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.search::before {
  content: ""; position: absolute; left: 10px; top: 50%; width: 11px; height: 11px;
  transform: translateY(-50%); border: 1.5px solid var(--ink-faint); border-radius: 50%;
}
.search::after {
  content: ""; position: absolute; left: 18px; top: 62%; width: 5px; height: 1.5px;
  background: var(--ink-faint); transform: rotate(45deg);
}
.toolbar-btn {
  font-family: var(--mono); font-size: 12px; padding: 7px 12px;
  border-radius: 3px; border: 1px solid var(--line-strong);
  background: var(--paper-raised); color: var(--ink-soft); cursor: pointer;
}
.toolbar-btn:hover { border-color: var(--accent); color: var(--ink); }

/* ---- Builder groups ---- */
.builder-group { margin-bottom: 30px; }
.builder-head {
  display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px;
}
.builder-head h2 {
  font-family: var(--serif); font-weight: 400; font-size: 20px; margin: 0; color: var(--ink);
}
.builder-head .totals {
  font-family: var(--mono); font-size: 12px; color: var(--ink-faint);
}
.builder-head .rule { flex: 1; height: 1px; background: var(--line); }

.community-list {
  display: flex; flex-direction: column; gap: 8px;
}

/* ---- Community row (accordion) ---- */
.community {
  background: var(--paper-raised);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: var(--shadow);
  overflow: hidden;
}
.community-head {
  display: flex; align-items: center; gap: 14px;
  padding: 13px 16px;
  cursor: pointer;
  user-select: none;
}
.community-head:hover { background: var(--accent-soft); }
.chevron {
  flex: none; width: 9px; height: 9px;
  border-right: 1.5px solid var(--ink-faint);
  border-bottom: 1.5px solid var(--ink-faint);
  transform: rotate(-45deg);
  transition: transform 0.15s ease;
}
.community.expanded .chevron { transform: rotate(45deg); }
.community-name-block { flex: 1; min-width: 0; }
.community-name {
  font-weight: 600; font-size: 14.5px; color: var(--ink);
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.community-streets {
  font-family: var(--mono); font-size: 12px; color: var(--ink-faint);
  margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.phase-tag {
  font-family: var(--mono); font-size: 10.5px; color: var(--ink-faint);
  border: 1px solid var(--line-strong); border-radius: 3px; padding: 1px 6px;
}
.rental-summary {
  flex: none; display: flex; align-items: center; gap: 10px;
}
.rental-total {
  font-family: var(--serif); font-size: 20px; color: var(--ink);
  min-width: 1.6em; text-align: right;
}
.rental-total.zero { color: var(--ink-faint); }
.mini-pills { display: flex; gap: 4px; }
.mini-pill {
  font-family: var(--mono); font-size: 10.5px; font-weight: 600;
  padding: 2px 6px; border-radius: 100px; white-space: nowrap;
}
.mini-pill.active { background: var(--status-active-soft); color: var(--status-active); }
.mini-pill.past { background: var(--status-past-soft); color: var(--status-past); }
.mini-pill.unknown { background: var(--status-unknown-soft); color: var(--status-unknown); }

.community-body {
  display: none;
  border-top: 1px solid var(--line);
  padding: 14px 16px 16px;
}
.community.expanded .community-body { display: block; }
.no-rentals { color: var(--ink-faint); font-size: 13px; padding: 4px 0 2px; }

/* ---- Rental detail table ---- */
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 640px; }
thead th {
  text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--ink-faint); padding: 8px 10px; border-bottom: 1px solid var(--line-strong);
  white-space: nowrap;
}
tbody tr { border-bottom: 1px solid var(--line); }
tbody tr:last-child { border-bottom: none; }
tbody td { padding: 9px 10px; vertical-align: top; font-size: 13px; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.mono, .mono { font-family: var(--mono); font-size: 12px; }

.pill {
  display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 600;
  padding: 3px 9px 3px 7px; border-radius: 100px; white-space: nowrap;
}
.pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%; }
.pill.active { background: var(--status-active-soft); color: var(--status-active); }
.pill.active::before { background: var(--status-active); }
.pill.past { background: var(--status-past-soft); color: var(--status-past); }
.pill.past::before { background: var(--status-past); }
.pill.unknown { background: var(--status-unknown-soft); color: var(--status-unknown); }
.pill.unknown::before { background: var(--status-unknown); }

.src a, .src span { color: var(--ink-faint); font-size: 11.5px; text-decoration: none; border-bottom: 1px dotted var(--ink-faint); }
.src a:hover { color: var(--accent); border-bottom-color: var(--accent); }
.blank { color: var(--ink-faint); }

.empty-state { text-align: center; color: var(--ink-faint); padding: 40px 14px; font-size: 13.5px; }

.foot-note { margin-top: 22px; font-size: 12px; color: var(--ink-faint); font-family: var(--mono); }

a:focus-visible, button:focus-visible, input:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 1px;
}

@media (max-width: 640px) {
  h1 { font-size: 27px; }
  .wrap { padding: 28px 16px 60px; }
  .rental-summary { flex-direction: column; align-items: flex-end; gap: 4px; }
  .community-streets { white-space: normal; }
}
</style>

<div class="wrap">
  <header class="page">
    <span class="eyebrow">New-Construction Rental Tracker</span>
    <h1>Little Rock, AR Metro</h1>
    <p class="subhead">Rental activity on streets built by D.R. Horton and Lennar, cross-referenced from builder sitemaps, MLS lease records, and manually verified listings.</p>
    <div class="meta-row">
      <span>Data as of <b id="generated-date"></b></span>
    </div>
  </header>

  <div class="toolbar">
    <div class="search"><input type="text" id="search" placeholder="Search community, street, or address&hellip;"></div>
    <button class="toolbar-btn" id="expand-all">Expand all</button>
    <button class="toolbar-btn" id="collapse-all">Collapse all</button>
  </div>

  <div id="builder-groups"></div>
  <p class="foot-note">Rent shown is the most recently known listed price. "Days" is days on market for that listing. Blank fields mean the source didn't report that value — not guessed.</p>
</div>

<script>
const COMMUNITIES = __COMMUNITIES_JSON__;
const RENTALS = __RENTALS_JSON__;
const GENERATED = __GENERATED_DATE__;
const BUILDER_ORDER = ["D.R. Horton", "Lennar"];

document.getElementById('generated-date').textContent = GENERATED;

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}
function fmtMoney(v) {
  if (!v) return '';
  const n = parseFloat(v);
  if (isNaN(n)) return v;
  return '$' + n.toLocaleString('en-US');
}
function statusClass(s) {
  if (s === 'currently for rent') return 'active';
  if (s === 'previously rented') return 'past';
  return 'unknown';
}
function statusLabel(s) {
  if (s === 'currently for rent') return 'For rent';
  if (s === 'previously rented') return 'Previously rented';
  return 'Unknown';
}
function blankOr(v) {
  return v ? esc(v) : '<span class="blank">—</span>';
}
function sourceCell(src) {
  if (!src) return '<span class="blank">—</span>';
  return src.split(' | ').map(p => {
    if (p.startsWith('http')) {
      let label = 'Zillow';
      try { label = new URL(p).hostname.replace('www.', '').split('.')[0]; label = label.charAt(0).toUpperCase() + label.slice(1); } catch (e) {}
      return `<span class="src"><a href="${esc(p)}" target="_blank" rel="noopener">${label}</a></span>`;
    }
    return `<span class="src"><span title="${esc(p)}">${esc(p)}</span></span>`;
  }).join(' ');
}

/* ---- Group communities by builder, then by community name+phase ---- */
function buildModel() {
  const byBuilder = {};
  for (const b of BUILDER_ORDER) byBuilder[b] = new Map();

  for (const c of COMMUNITIES) {
    const builderMap = byBuilder[c.builder] || (byBuilder[c.builder] = new Map());
    const key = c.community_name + '|' + (c.phase || '');
    if (!builderMap.has(key)) {
      builderMap.set(key, { name: c.community_name, phase: c.phase || '', streets: [], rentals: [] });
    }
    if (c.street_name) builderMap.get(key).streets.push(c.street_name);
  }
  for (const r of RENTALS) {
    const builderMap = byBuilder[r.builder];
    if (!builderMap) continue;
    // A rental's phase may differ in formatting from the community row's
    // phase in rare cases - fall back to matching by name only if the
    // exact name+phase key isn't found.
    let key = r.community_name + '|' + (r.phase || '');
    if (!builderMap.has(key)) {
      key = [...builderMap.keys()].find(k => k.startsWith(r.community_name + '|')) || key;
    }
    if (!builderMap.has(key)) {
      builderMap.set(key, { name: r.community_name, phase: r.phase || '', streets: [], rentals: [] });
    }
    builderMap.get(key).rentals.push(r);
  }
  return byBuilder;
}

function communityMatches(entry, q) {
  if (!q) return true;
  q = q.toLowerCase();
  if (entry.name.toLowerCase().includes(q)) return true;
  if (entry.streets.some(s => s.toLowerCase().includes(q))) return true;
  if (entry.rentals.some(r => r.full_address.toLowerCase().includes(q))) return true;
  return false;
}

function rentalRowHtml(r) {
  return `
    <tr>
      <td class="mono">${esc(r.full_address)}</td>
      <td class="num mono">${blankOr(fmtMoney(r.rent_price))}</td>
      <td>
        <span class="pill ${statusClass(r.status)}">${statusLabel(r.status)}</span>
        ${r.status_changed ? `<div class="mono" style="font-size:10px;color:var(--ink-faint);margin-top:4px">${esc(r.status_changed)}</div>` : ''}
      </td>
      <td class="mono">${blankOr(r.list_date)}</td>
      <td class="mono">${blankOr(r.rent_date)}</td>
      <td class="num mono">${blankOr(r.days_on_market)}</td>
      <td>${sourceCell(r.source_url)}</td>
    </tr>`;
}

function communityHtml(entry, idx) {
  const total = entry.rentals.length;
  const counts = { active: 0, past: 0, unknown: 0 };
  for (const r of entry.rentals) counts[statusClass(r.status)]++;

  const pills = [
    counts.active ? `<span class="mini-pill active">${counts.active} for rent</span>` : '',
    counts.past ? `<span class="mini-pill past">${counts.past} past</span>` : '',
    counts.unknown ? `<span class="mini-pill unknown">${counts.unknown} unknown</span>` : '',
  ].join('');

  const streetsLine = entry.streets.length
    ? entry.streets.join(', ')
    : 'No confirmed streets yet';

  const body = total
    ? `<div class="table-scroll"><table>
        <thead><tr>
          <th>Address</th><th class="num">Rent</th><th>Status</th>
          <th>Listed</th><th>Rented/removed</th><th class="num">Days</th><th>Source</th>
        </tr></thead>
        <tbody>${entry.rentals.map(rentalRowHtml).join('')}</tbody>
      </table></div>`
    : `<div class="no-rentals">No rental activity recorded yet.</div>`;

  return `
    <div class="community" data-idx="${idx}">
      <div class="community-head">
        <span class="chevron"></span>
        <div class="community-name-block">
          <div class="community-name">${esc(entry.name)}${entry.phase ? `<span class="phase-tag">${esc(entry.phase)}</span>` : ''}</div>
          <div class="community-streets">${esc(streetsLine)}</div>
        </div>
        <div class="rental-summary">
          <div class="mini-pills">${pills}</div>
          <div class="rental-total ${total ? '' : 'zero'}">${total}</div>
        </div>
      </div>
      <div class="community-body">${body}</div>
    </div>`;
}

function render() {
  const q = document.getElementById('search').value.trim();
  const model = buildModel();
  const groupsEl = document.getElementById('builder-groups');
  let html = '';
  let globalIdx = 0;
  let anyResults = false;

  for (const builder of BUILDER_ORDER) {
    const entries = [...(model[builder] || new Map()).values()]
      .filter(e => communityMatches(e, q))
      .sort((a, b) => a.name.localeCompare(b.name));
    if (!entries.length) continue;
    anyResults = true;
    const totalRentals = entries.reduce((s, e) => s + e.rentals.length, 0);
    html += `
      <section class="builder-group">
        <div class="builder-head">
          <h2>${esc(builder)}</h2>
          <span class="totals">${entries.length} ${entries.length === 1 ? 'community' : 'communities'} &middot; ${totalRentals} ${totalRentals === 1 ? 'rental' : 'rentals'}</span>
          <span class="rule"></span>
        </div>
        <div class="community-list">
          ${entries.map(e => communityHtml(e, globalIdx++)).join('')}
        </div>
      </section>`;
  }

  groupsEl.innerHTML = anyResults ? html : '<div class="empty-state">No communities match your search.</div>';

  groupsEl.querySelectorAll('.community-head').forEach(head => {
    head.addEventListener('click', () => {
      head.parentElement.classList.toggle('expanded');
    });
  });
}

document.getElementById('search').addEventListener('input', render);
document.getElementById('expand-all').addEventListener('click', () => {
  document.querySelectorAll('.community').forEach(c => c.classList.add('expanded'));
});
document.getElementById('collapse-all').addEventListener('click', () => {
  document.querySelectorAll('.community').forEach(c => c.classList.remove('expanded'));
});

render();
</script>
"""


def generate(metro_slug, output_dir="output"):
    metro_config = get_metro(metro_slug)
    communities_path = os.path.join(output_dir, f"{metro_config.METRO_SLUG}-communities.csv")
    rentals_path = os.path.join(output_dir, f"{metro_config.METRO_SLUG}-rentals.csv")
    if not os.path.exists(communities_path) or not os.path.exists(rentals_path):
        raise SystemExit(f"Run run_discovery.py / import scripts for {metro_slug} first.")

    communities = read_csv(communities_path)
    rentals = read_csv(rentals_path)
    generated = datetime.date.today().isoformat()

    communities_json = json.dumps(communities, ensure_ascii=False).replace("</script", "<\\/script")
    rentals_json = json.dumps(rentals, ensure_ascii=False).replace("</script", "<\\/script")

    out = TEMPLATE.replace("__COMMUNITIES_JSON__", communities_json)
    out = out.replace("__RENTALS_JSON__", rentals_json)
    out = out.replace("__GENERATED_DATE__", json.dumps(generated))

    dashboard_path = os.path.join(output_dir, f"{metro_config.METRO_SLUG}-dashboard.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(out)
    return dashboard_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metro_slug", help="e.g. little-rock-ar")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    path = generate(args.metro_slug, args.output_dir)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
