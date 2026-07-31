#!/usr/bin/env python3
"""
Generates a self-contained HTML dashboard (sortable/filterable tables +
summary stats) from a metro's communities.csv and rentals.csv. Re-run this
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

    .wrap {
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }

    /* ---- Header ---- */
    header.page {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 32px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--line);
    }
    .eyebrow {
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--accent);
      font-weight: 600;
    }
    h1 {
      font-family: var(--serif);
      font-weight: 400;
      font-size: 34px;
      letter-spacing: -0.01em;
      margin: 2px 0 4px;
      color: var(--ink);
      text-wrap: balance;
    }
    .subhead {
      color: var(--ink-soft);
      font-size: 14.5px;
      max-width: 62ch;
    }
    .meta-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 18px;
      margin-top: 14px;
      font-family: var(--mono);
      font-size: 12px;
      color: var(--ink-faint);
    }
    .meta-row span b { color: var(--ink-soft); font-weight: 600; }

    /* ---- Stat cards ---- */
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 32px;
    }
    .stat {
      background: var(--paper-raised);
      border: 1px solid var(--line);
      border-radius: 3px;
      padding: 16px 18px;
      box-shadow: var(--shadow);
    }
    .stat .n {
      font-family: var(--serif);
      font-size: 28px;
      line-height: 1;
      color: var(--ink);
      font-variant-numeric: tabular-nums;
    }
    .stat .label {
      margin-top: 6px;
      font-size: 11.5px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--ink-faint);
    }

    /* ---- Tabs ---- */
    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }
    .tab-btn {
      font-family: var(--sans);
      font-size: 13.5px;
      font-weight: 600;
      color: var(--ink-faint);
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      padding: 10px 4px;
      margin-right: 22px;
      cursor: pointer;
      transition: color 0.15s ease;
    }
    .tab-btn:hover { color: var(--ink-soft); }
    .tab-btn.active { color: var(--ink); border-bottom-color: var(--accent); }
    .tab-btn .count {
      font-family: var(--mono);
      font-size: 11px;
      color: var(--ink-faint);
      margin-left: 4px;
    }

    .panel { display: none; }
    .panel.active { display: block; }

    /* ---- Filter bar ---- */
    .filters {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
    }
    .search {
      flex: 1 1 220px;
      min-width: 180px;
      position: relative;
    }
    .search input {
      width: 100%;
      font-family: var(--sans);
      font-size: 13.5px;
      padding: 8px 12px 8px 30px;
      border: 1px solid var(--line-strong);
      border-radius: 3px;
      background: var(--paper-raised);
      color: var(--ink);
    }
    .search input:focus {
      outline: 2px solid var(--accent);
      outline-offset: -1px;
    }
    .search::before {
      content: "";
      position: absolute;
      left: 10px; top: 50%;
      width: 11px; height: 11px;
      transform: translateY(-50%);
      border: 1.5px solid var(--ink-faint);
      border-radius: 50%;
    }
    .search::after {
      content: "";
      position: absolute;
      left: 18px; top: 62%;
      width: 5px; height: 1.5px;
      background: var(--ink-faint);
      transform: rotate(45deg);
    }
    .chipset { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip {
      font-family: var(--mono);
      font-size: 12px;
      padding: 6px 11px;
      border-radius: 100px;
      border: 1px solid var(--line-strong);
      background: var(--paper-raised);
      color: var(--ink-soft);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.12s ease;
    }
    .chip:hover { border-color: var(--accent); color: var(--ink); }
    .chip.active {
      background: var(--ink);
      border-color: var(--ink);
      color: var(--paper);
    }
    :root[data-theme="dark"] .chip.active, @media (prefers-color-scheme: dark) { }
    .chip.active { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }

    /* ---- Table ---- */
    .table-scroll {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 3px;
      background: var(--paper-raised);
      box-shadow: var(--shadow);
    }
    table { border-collapse: collapse; width: 100%; min-width: 760px; }
    thead th {
      position: sticky; top: 0;
      background: var(--paper-raised);
      text-align: left;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-faint);
      padding: 11px 14px;
      border-bottom: 1px solid var(--line-strong);
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    thead th:hover { color: var(--ink); }
    thead th .arrow { font-size: 9px; margin-left: 3px; opacity: 0.55; }
    thead th.sorted { color: var(--accent); }
    thead th.sorted .arrow { opacity: 1; }
    tbody tr { border-bottom: 1px solid var(--line); }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: var(--accent-soft); }
    tbody td {
      padding: 11px 14px;
      vertical-align: top;
      font-size: 13.5px;
    }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    td.mono, .mono { font-family: var(--mono); font-size: 12.5px; }
    td.addr { color: var(--ink); }
    td.addr .city { color: var(--ink-faint); font-size: 12px; }
    td.community { font-weight: 600; }
    td.community .street { display: block; font-weight: 400; color: var(--ink-faint); font-size: 12px; margin-top: 1px; font-family: var(--mono); }

    .badge {
      display: inline-block;
      font-family: var(--mono);
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 3px;
      font-weight: 600;
    }
    .badge.drh { background: var(--clay-soft); color: var(--clay); }
    .badge.lennar { background: var(--slate-soft); color: var(--slate); }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      font-weight: 600;
      padding: 3px 9px 3px 7px;
      border-radius: 100px;
      white-space: nowrap;
    }
    .pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%; }
    .pill.active { background: var(--status-active-soft); color: var(--status-active); }
    .pill.active::before { background: var(--status-active); }
    .pill.past { background: var(--status-past-soft); color: var(--status-past); }
    .pill.past::before { background: var(--status-past); }
    .pill.unknown { background: var(--status-unknown-soft); color: var(--status-unknown); }
    .pill.unknown::before { background: var(--status-unknown); }

    .src a, .src span { color: var(--ink-faint); font-size: 12px; text-decoration: none; border-bottom: 1px dotted var(--ink-faint); }
    .src a:hover { color: var(--accent); border-bottom-color: var(--accent); }
    .blank { color: var(--ink-faint); }

    .empty-row td { text-align: center; color: var(--ink-faint); padding: 40px 14px; font-size: 13.5px; }

    .foot-note {
      margin-top: 18px;
      font-size: 12px;
      color: var(--ink-faint);
      font-family: var(--mono);
    }
    .result-count { font-size: 12px; color: var(--ink-faint); font-family: var(--mono); margin-bottom: 10px; }

    a:focus-visible, button:focus-visible, input:focus-visible, th:focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 1px;
    }

    @media (max-width: 640px) {
      h1 { font-size: 27px; }
      .wrap { padding: 28px 16px 60px; }
    }
    </style>

    <div class="wrap">
      <header class="page">
        <span class="eyebrow">New-Construction Rental Tracker</span>
        <h1>Little Rock, AR Metro</h1>
        <p class="subhead">Rental activity on streets built by D.R. Horton and Lennar, cross-referenced from builder sitemaps, MLS lease records, and manually verified listings.</p>
        <div class="meta-row">
          <span>Data as of <b id="generated-date"></b></span>
          <span><span class="badge drh" style="margin-right:5px">D.R. Horton</span><span class="badge lennar">Lennar</span></span>
        </div>
      </header>

      <div class="stats" id="stats"></div>

      <div class="tabs">
        <button class="tab-btn active" data-panel="rentals">Rentals <span class="count" id="count-rentals"></span></button>
        <button class="tab-btn" data-panel="communities">Communities &amp; streets <span class="count" id="count-communities"></span></button>
      </div>

      <section class="panel active" id="panel-rentals">
        <div class="filters">
          <div class="search"><input type="text" id="rental-search" placeholder="Search address, community, or street&hellip;"></div>
          <div class="chipset" id="builder-chips"></div>
          <div class="chipset" id="status-chips"></div>
        </div>
        <div class="result-count" id="rental-result-count"></div>
        <div class="table-scroll">
          <table id="rental-table">
            <thead><tr>
              <th data-key="community_name">Community<span class="arrow">&#9662;</span></th>
              <th data-key="full_address">Address<span class="arrow">&#9662;</span></th>
              <th data-key="rent_price" class="num">Rent<span class="arrow">&#9662;</span></th>
              <th data-key="status">Status<span class="arrow">&#9662;</span></th>
              <th data-key="list_date">Listed<span class="arrow">&#9662;</span></th>
              <th data-key="rent_date">Rented/removed<span class="arrow">&#9662;</span></th>
              <th data-key="days_on_market" class="num">Days<span class="arrow">&#9662;</span></th>
              <th data-key="source_url">Source</th>
            </tr></thead>
            <tbody id="rental-tbody"></tbody>
          </table>
        </div>
        <p class="foot-note">Rent shown is the most recently known listed price. "Days" is days on market for that listing. Blank fields mean the source didn't report that value — not guessed.</p>
      </section>

      <section class="panel" id="panel-communities">
        <div class="filters">
          <div class="search"><input type="text" id="community-search" placeholder="Search community or street&hellip;"></div>
          <div class="chipset" id="community-builder-chips"></div>
        </div>
        <div class="result-count" id="community-result-count"></div>
        <div class="table-scroll">
          <table id="community-table">
            <thead><tr>
              <th data-key="community_name">Community<span class="arrow">&#9662;</span></th>
              <th data-key="builder">Builder<span class="arrow">&#9662;</span></th>
              <th data-key="phase">Phase<span class="arrow">&#9662;</span></th>
              <th data-key="street_name">Street<span class="arrow">&#9662;</span></th>
            </tr></thead>
            <tbody id="community-tbody"></tbody>
          </table>
        </div>
        <p class="foot-note">One row per street. A blank street means the community has no confirmed street yet (pre-construction or sold out with no MLS record found).</p>
      </section>
    </div>

    <script>
    const COMMUNITIES = __COMMUNITIES_JSON__;
    const RENTALS = __RENTALS_JSON__;
    const GENERATED = __GENERATED_DATE__;

    document.getElementById('generated-date').textContent = GENERATED;

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
    function builderClass(b) {
      return b === 'D.R. Horton' ? 'drh' : 'lennar';
    }
    function esc(s) {
      const d = document.createElement('div');
      d.textContent = s == null ? '' : s;
      return d.innerHTML;
    }
    function blankOr(v, cls) {
      return v ? `<span class="${cls||''}">${esc(v)}</span>` : `<span class="blank">—</span>`;
    }

    /* ---------- Stats ---------- */
    function renderStats() {
      const streets = new Set(COMMUNITIES.filter(c => c.street_name).map(c => c.community_name + '|' + c.street_name));
      const communityNames = new Set(COMMUNITIES.map(c => c.community_name));
      const active = RENTALS.filter(r => r.status === 'currently for rent');
      const rents = RENTALS.map(r => parseFloat(r.rent_price)).filter(n => !isNaN(n)).sort((a,b) => a-b);
      const median = rents.length ? (rents.length % 2 ? rents[(rents.length-1)/2] : (rents[rents.length/2-1]+rents[rents.length/2])/2) : null;

      const stats = [
        { n: communityNames.size, label: 'Communities tracked' },
        { n: streets.size, label: 'Streets on record' },
        { n: RENTALS.length, label: 'Rentals logged' },
        { n: active.length, label: 'Currently for rent' },
        { n: median ? fmtMoney(median) : '—', label: 'Median rent' },
      ];
      document.getElementById('stats').innerHTML = stats.map(s =>
        `<div class="stat"><div class="n">${s.n}</div><div class="label">${s.label}</div></div>`
      ).join('');
    }

    /* ---------- Rentals table ---------- */
    let rentalSort = { key: 'rent_date', dir: 'desc' };
    let rentalFilters = { builder: 'all', status: 'all', q: '' };

    function filteredRentals() {
      return RENTALS.filter(r => {
        if (rentalFilters.builder !== 'all' && r.builder !== rentalFilters.builder) return false;
        if (rentalFilters.status !== 'all' && r.status !== rentalFilters.status) return false;
        if (rentalFilters.q) {
          const hay = (r.full_address + ' ' + r.community_name + ' ' + r.street_name).toLowerCase();
          if (!hay.includes(rentalFilters.q.toLowerCase())) return false;
        }
        return true;
      });
    }

    function sortRows(rows, key, dir) {
      const numeric = key === 'rent_price' || key === 'days_on_market';
      const dateKey = key === 'list_date' || key === 'rent_date';
      return [...rows].sort((a, b) => {
        let av = a[key] || '', bv = b[key] || '';
        if (numeric) {
          av = parseFloat(av); bv = parseFloat(bv);
          if (isNaN(av)) av = dir === 'asc' ? Infinity : -Infinity;
          if (isNaN(bv)) bv = dir === 'asc' ? Infinity : -Infinity;
          return dir === 'asc' ? av - bv : bv - av;
        }
        if (dateKey) {
          if (!av) av = dir === 'asc' ? '9999' : '0000';
          if (!bv) bv = dir === 'asc' ? '9999' : '0000';
        }
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
      });
    }

    function sourceCell(src) {
      if (!src) return '<span class="blank">—</span>';
      const parts = src.split(' | ');
      return parts.map(p => {
        if (p.startsWith('http')) {
          let label = 'Zillow';
          try { label = new URL(p).hostname.replace('www.','').split('.')[0]; label = label.charAt(0).toUpperCase()+label.slice(1); } catch(e) {}
          return `<span class="src"><a href="${esc(p)}" target="_blank" rel="noopener">${label}</a></span>`;
        }
        return `<span class="src"><span title="${esc(p)}">${esc(p)}</span></span>`;
      }).join(' ');
    }

    function renderRentals() {
      const rows = sortRows(filteredRentals(), rentalSort.key, rentalSort.dir);
      document.getElementById('rental-result-count').textContent = `${rows.length} of ${RENTALS.length} rentals`;
      const tbody = document.getElementById('rental-tbody');
      if (!rows.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="8">No rentals match these filters.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td class="community">
            <span class="badge ${builderClass(r.builder)}" style="margin-right:6px">${r.builder === 'D.R. Horton' ? 'DRH' : 'LEN'}</span>${esc(r.community_name)}${r.phase ? ' <span class="mono" style="color:var(--ink-faint);font-size:11px">'+esc(r.phase)+'</span>' : ''}
            <span class="street">${esc(r.street_name)}</span>
          </td>
          <td class="addr mono">${esc(r.full_address)}</td>
          <td class="num mono">${blankOr(fmtMoney(r.rent_price))}</td>
          <td>
            <span class="pill ${statusClass(r.status)}">${statusLabel(r.status)}</span>
            ${r.status_changed ? `<div class="mono" style="font-size:10.5px;color:var(--ink-faint);margin-top:4px">${esc(r.status_changed)}</div>` : ''}
          </td>
          <td class="mono">${blankOr(r.list_date)}</td>
          <td class="mono">${blankOr(r.rent_date)}</td>
          <td class="num mono">${blankOr(r.days_on_market)}</td>
          <td>${sourceCell(r.source_url)}</td>
        </tr>
      `).join('');
    }

    function renderRentalHeaders() {
      document.querySelectorAll('#rental-table thead th').forEach(th => {
        th.classList.toggle('sorted', th.dataset.key === rentalSort.key);
        const arrow = th.querySelector('.arrow');
        if (th.dataset.key === rentalSort.key) arrow.innerHTML = rentalSort.dir === 'asc' ? '&#9652;' : '&#9662;';
      });
    }

    document.querySelectorAll('#rental-table thead th').forEach(th => {
      th.addEventListener('click', () => {
        const key = th.dataset.key;
        if (rentalSort.key === key) rentalSort.dir = rentalSort.dir === 'asc' ? 'desc' : 'asc';
        else { rentalSort.key = key; rentalSort.dir = key === 'rent_price' || key === 'days_on_market' ? 'desc' : 'asc'; }
        renderRentalHeaders();
        renderRentals();
      });
    });

    function renderChips() {
      const builders = ['all', ...new Set(RENTALS.map(r => r.builder))];
      document.getElementById('builder-chips').innerHTML = builders.map(b =>
        `<button class="chip ${rentalFilters.builder===b?'active':''}" data-builder="${esc(b)}">${b==='all'?'All builders':esc(b)}</button>`
      ).join('');
      const statuses = ['all', 'currently for rent', 'previously rented', 'unknown'];
      document.getElementById('status-chips').innerHTML = statuses.map(s =>
        `<button class="chip ${rentalFilters.status===s?'active':''}" data-status="${esc(s)}">${s==='all'?'All statuses':statusLabel(s)}</button>`
      ).join('');

      document.querySelectorAll('#builder-chips .chip').forEach(c => c.addEventListener('click', () => {
        rentalFilters.builder = c.dataset.builder;
        renderChips(); renderRentals();
      }));
      document.querySelectorAll('#status-chips .chip').forEach(c => c.addEventListener('click', () => {
        rentalFilters.status = c.dataset.status;
        renderChips(); renderRentals();
      }));
    }

    document.getElementById('rental-search').addEventListener('input', (e) => {
      rentalFilters.q = e.target.value;
      renderRentals();
    });

    /* ---------- Communities table ---------- */
    let communitySort = { key: 'community_name', dir: 'asc' };
    let communityFilters = { builder: 'all', q: '' };

    function filteredCommunities() {
      return COMMUNITIES.filter(c => {
        if (communityFilters.builder !== 'all' && c.builder !== communityFilters.builder) return false;
        if (communityFilters.q) {
          const hay = (c.community_name + ' ' + c.street_name).toLowerCase();
          if (!hay.includes(communityFilters.q.toLowerCase())) return false;
        }
        return true;
      });
    }

    function renderCommunities() {
      const rows = sortRows(filteredCommunities(), communitySort.key, communitySort.dir);
      document.getElementById('community-result-count').textContent = `${rows.length} of ${COMMUNITIES.length} streets`;
      const tbody = document.getElementById('community-tbody');
      if (!rows.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No communities match these filters.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map(c => `
        <tr>
          <td class="community">${esc(c.community_name)}</td>
          <td><span class="badge ${builderClass(c.builder)}">${esc(c.builder)}</span></td>
          <td class="mono">${blankOr(c.phase)}</td>
          <td class="mono">${blankOr(c.street_name)}</td>
        </tr>
      `).join('');
    }

    function renderCommunityHeaders() {
      document.querySelectorAll('#community-table thead th').forEach(th => {
        th.classList.toggle('sorted', th.dataset.key === communitySort.key);
        const arrow = th.querySelector('.arrow');
        if (th.dataset.key === communitySort.key) arrow.innerHTML = communitySort.dir === 'asc' ? '&#9652;' : '&#9662;';
      });
    }
    document.querySelectorAll('#community-table thead th').forEach(th => {
      th.addEventListener('click', () => {
        const key = th.dataset.key;
        if (communitySort.key === key) communitySort.dir = communitySort.dir === 'asc' ? 'desc' : 'asc';
        else { communitySort.key = key; communitySort.dir = 'asc'; }
        renderCommunityHeaders();
        renderCommunities();
      });
    });

    function renderCommunityChips() {
      const builders = ['all', ...new Set(COMMUNITIES.map(c => c.builder))];
      document.getElementById('community-builder-chips').innerHTML = builders.map(b =>
        `<button class="chip ${communityFilters.builder===b?'active':''}" data-builder="${esc(b)}">${b==='all'?'All builders':esc(b)}</button>`
      ).join('');
      document.querySelectorAll('#community-builder-chips .chip').forEach(c => c.addEventListener('click', () => {
        communityFilters.builder = c.dataset.builder;
        renderCommunityChips(); renderCommunities();
      }));
    }
    document.getElementById('community-search').addEventListener('input', (e) => {
      communityFilters.q = e.target.value;
      renderCommunities();
    });

    /* ---------- Tabs ---------- */
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('panel-' + btn.dataset.panel).classList.add('active');
      });
    });

    /* ---------- Init ---------- */
    document.getElementById('count-rentals').textContent = RENTALS.length;
    document.getElementById('count-communities').textContent = COMMUNITIES.length;
    renderStats();
    renderChips();
    renderRentalHeaders();
    renderRentals();
    renderCommunityChips();
    renderCommunityHeaders();
    renderCommunities();
    </script>
    """


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
