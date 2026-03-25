"""
Mundane Astrology Dashboard — Gradio UI (v2)
Categorical Pulse · Risk/Reward Gauge · Side-by-Side Analysis Cards
"""

import os
import datetime
import pandas as pd
import gradio as gr

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from astrology_engine import (
    get_transit_data,
    get_house_positions,
    get_all_house_positions,
    get_lagna_sign,
    get_natal_chart,
    get_next_ingresses,
    get_retrograde_status,
    get_next_lunations,
    COUNTRY_LAGNAS,
    VEDIC_PLANETS,
)
from predictor import (
    categorize_transits,
    get_country_summary,
    generate_llm_analysis,
    generate_watch_summary,
    build_heatmap_data,
    build_categorical_pulse,
    _text_to_bullets,
    PLANET_ORDER,
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
COUNTRIES      = list(COUNTRY_LAGNAS.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS injected via gr.Blocks(css=...) — fixes Gradio chrome visibility
# ─────────────────────────────────────────────────────────────────────────────
_GRADIO_CSS = """
/* ── Dark app shell ──────────────────────────────────────────────────── */
body { background: #0b0f19 !important; }
.gradio-container { background-color: #0b0f19 !important; color: #f8fafc !important; }

/* ── Tab navigation ──────────────────────────────────────────────────── */
.tab-nav button { color: #94a3b8 !important; background: transparent !important; }
.tab-nav button.selected { color: #f8fafc !important; border-bottom: 2px solid #7c3aed !important; }

/* ── Form labels ─────────────────────────────────────────────────────── */
label > span, .label-wrap > span, .block > label,
.svelte-1gfkn6j, .section-header { color: #e2e8f0 !important; font-weight: 500; }

/* ── Markdown / prose ────────────────────────────────────────────────── */
.prose, .prose p, .prose li, .prose strong,
.prose h1, .prose h2, .prose h3 { color: #f8fafc !important; }

/* ── Gradio native accordion (NOT our .ma-accordion) ────────────────── */
.block:not(.ma-root) > details > summary { color: #f8fafc !important; background: #1e293b !important; }

/* ── Inputs / selects ────────────────────────────────────────────────── */
input, select, textarea {
  background: #1e293b !important;
  color: #f8fafc !important;
  border-color: #334155 !important;
}

/* ── Gradio native DataFrame tables ONLY (scoped — not our HTML tables) ─ */
.gradio-container .table-wrap thead th,
.gradio-container .dataframe thead th {
  background: #1e293b !important;
  color: #94a3b8 !important;
  text-transform: uppercase;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
  padding: 10px 12px !important;
  border-bottom: 2px solid #334155 !important;
}
.gradio-container .table-wrap tbody td,
.gradio-container .dataframe tbody td {
  background-color: #0f172a !important;
  color: #f8fafc !important;
  padding: 10px 12px !important;
  border-bottom: 1px solid #1e293b !important;
}

/* ── .status-badge pill utility ──────────────────────────────────────── */
.status-badge {
  padding: 4px 12px;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.85rem;
}
.status-badge-green  { background: #14532d; color: #86efac !important; }
.status-badge-red    { background: #7f1d1d; color: #fca5a5 !important; }
.status-badge-yellow { background: #713f12; color: #fde047 !important; }
.status-badge-grey   { background: #1e293b; color: #94a3b8 !important; }

/* ── ISOLATE our .ma-root HTML blocks from all overrides above ───────── */
div.ma-root {
  background: #ffffff !important;
  color: #1e293b !important;
  isolation: isolate;
}

/* ── iOS / Safari text-size fix ─────────────────────────────────────── */
html { -webkit-text-size-adjust: 100%; }

/* ── Mobile: tab nav scrollable row ─────────────────────────────────── */
@media (max-width: 768px) {
  .tab-nav {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    flex-wrap: nowrap !important;
    scrollbar-width: none;
  }
  .tab-nav::-webkit-scrollbar { display: none; }
  .tab-nav button {
    min-width: 70px !important;
    font-size: .72rem !important;
    white-space: nowrap;
    padding: 8px 10px !important;
  }

  /* Stack top date+button row vertically */
  .gr-row, .row-wrap {
    flex-direction: column !important;
    flex-wrap: wrap !important;
  }

  /* Touch-friendly tap targets */
  button { min-height: 44px; }
  select, input { min-height: 40px; font-size: 16px !important; /* prevents iOS zoom */ }

  /* Shrink the Calculate button */
  .primary { width: 100% !important; }

  /* DataFrame wrapper horizontal scroll */
  .gradio-container .table-wrap { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Shared CSS injected into every HTML block
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
  /* Root reset — overrides Gradio theme inheritance */
  .ma-root{color:#1e293b !important;background:#ffffff;font-family:'Segoe UI',system-ui,sans-serif;
           border-radius:10px;padding:10px;line-height:1.5}
  .ma-root *{box-sizing:border-box}
  /* Cards */
  .ma-card{border-radius:12px;padding:14px 18px;margin:6px 0;
           box-shadow:0 2px 8px rgba(0,0,0,.10);color:#1e293b !important}
  .ma-green {background:#f0fdf4;border-left:5px solid #22c55e}
  .ma-red   {background:#fff1f2;border-left:5px solid #ef4444}
  .ma-yellow{background:#fefce8;border-left:5px solid #eab308}
  .ma-grey  {background:#f8fafc;border-left:5px solid #94a3b8}
  /* Tags */
  .ma-tag{display:inline-block;border-radius:99px;padding:2px 10px;
          font-size:.75rem;font-weight:600;margin-right:4px;color:#1e293b}
  .ma-tag-green {background:#dcfce7 !important;color:#166534 !important}
  .ma-tag-red   {background:#fee2e2 !important;color:#991b1b !important}
  .ma-tag-yellow{background:#fef9c3 !important;color:#854d0e !important}
  /* Tip bar */
  .ma-tip{margin-top:8px;padding:8px 12px;background:#eff6ff;border-radius:8px;
          font-size:.82rem;color:#1e40af !important}
  /* Categorical Pulse table */
  .pulse-table{width:100%;border-collapse:collapse;font-size:.87rem;color:#1e293b}
  .pulse-table th{background:#1e293b;color:#f1f5f9 !important;padding:9px 12px;
                  text-align:left;font-weight:600}
  .pulse-table td{padding:9px 12px;border-bottom:1px solid #e2e8f0;
                  vertical-align:top;color:#1e293b !important;background:#ffffff}
  .pulse-table tr:nth-child(even) td{background:#f8fafc}
  /* Gauge */
  .gauge-wrap{margin:8px 0 16px;color:#1e293b !important}
  .gauge-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;color:#1e293b !important}
  .gauge-track{position:relative;height:24px;border-radius:12px;
               background:linear-gradient(to right,#ef4444 0%,#ef4444 33%,
               #eab308 33%,#eab308 66%,#22c55e 66%,#22c55e 100%);
               box-shadow:inset 0 1px 3px rgba(0,0,0,.25)}
  .gauge-needle{position:absolute;top:-3px;transform:translateX(-50%);
                font-size:1.2rem;line-height:1}
  .gauge-labels{display:flex;justify-content:space-between;
                font-size:.72rem;color:#475569 !important;margin-top:3px}
  /* Heatmap table */
  .heatmap-tbl{width:100%;border-collapse:collapse;font-size:.83rem;color:#1e293b}
  .heatmap-tbl th{background:#0f172a;color:#e2e8f0 !important;
                  padding:9px 12px;text-align:center;font-weight:600}
  .heatmap-tbl td{padding:8px 10px;text-align:center;
                  border:1px solid #e2e8f0;color:#1e293b !important}
  .hm-high-risk   td{background:#fff1f2}
  .hm-high-growth td{background:#f0fdf4}
  .hm-mixed       td{background:#fefce8}
  .hm-legend{font-size:.74rem;color:#64748b !important;margin-top:8px}
  /* Side-by-side analysis cards */
  .split-wrap{display:flex;gap:14px;flex-wrap:wrap;margin-top:6px}
  .split-card{flex:1;min-width:260px;border-radius:12px;padding:16px 18px;
              font-size:.87rem;color:#1e293b !important}
  .split-green{background:#f0fdf4;border:1px solid #86efac}
  .split-red  {background:#fff1f2;border:1px solid #fca5a5}
  .split-card h4{margin:0 0 10px;font-size:.95rem;font-weight:700;color:#1e293b !important}
  .split-card ul{margin:0;padding-left:18px;line-height:1.8;color:#1e293b !important}
  .split-card li{margin-bottom:3px;color:#1e293b !important}
  /* Retrograde banner */
  .retro-banner{background:#1e293b;color:#f1f5f9 !important;border-radius:10px;
                padding:10px 16px;font-size:.83rem;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
  .retro-banner span{color:#f1f5f9 !important}
  .retro-pill{background:#334155;border-radius:99px;padding:3px 10px;
              font-weight:600;font-size:.78rem;color:#fbbf24 !important}
  .station-pill{background:#334155;border-radius:99px;padding:3px 10px;
                font-size:.78rem;color:#a5f3fc !important}
  /* Ingress cards */
  .ingress-grid{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0}
  .ingress-card{flex:1;min-width:160px;background:#f8fafc;border:1px solid #e2e8f0;
                border-radius:10px;padding:10px 12px;color:#1e293b !important}
  .ingress-card .planet{font-weight:700;font-size:.88rem;color:#1e293b !important}
  .ingress-card .arrow{color:#64748b;font-size:.8rem}
  .ingress-card .days{font-size:1.1rem;font-weight:700;color:#7c3aed !important}
  .ingress-card .date{font-size:.73rem;color:#64748b !important}
  .ingress-card .houses{font-size:.72rem;color:#475569 !important;margin-top:3px}
  /* Lunation alerts */
  .luna-list{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0}
  .luna-card{flex:1;min-width:180px;border-radius:10px;padding:10px 14px;
             color:#1e293b !important}
  .luna-new{background:#fef9c3;border:1px solid #fde047}
  .luna-full{background:#ede9fe;border:1px solid #c4b5fd}
  .luna-eclipse{background:#fff1f2;border:2px solid #ef4444}
  .luna-card .ltype{font-weight:700;font-size:.88rem;color:#1e293b !important}
  .luna-card .lsign{font-size:.8rem;color:#475569 !important}
  .luna-card .ldays{font-size:1rem;font-weight:700;color:#7c3aed !important}
  .luna-card .lhouses{font-size:.72rem;color:#475569 !important;margin-top:3px}
  /* Watch summary */
  .watch-card{background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:14px;
              padding:18px 22px;color:#f1f5f9 !important}
  .watch-card h3{margin:0 0 12px;color:#fbbf24 !important;font-size:1rem}
  .watch-card ul{margin:0;padding-left:0;list-style:none;color:#e2e8f0 !important}
  .watch-card li{margin-bottom:8px;padding-left:20px;position:relative;
                 color:#e2e8f0 !important;font-size:.87rem;line-height:1.6}
  .watch-card li::before{content:"•";position:absolute;left:0;color:#fbbf24}
  /* Natal chart table */
  .natal-tbl{width:100%;border-collapse:collapse;font-size:.85rem;color:#1e293b}
  .natal-tbl th{background:#334155;color:#f1f5f9 !important;padding:8px 12px;
                text-align:left;font-weight:600}
  .natal-tbl td{padding:7px 12px;border-bottom:1px solid #e2e8f0;
                color:#1e293b !important;background:#ffffff}
  .natal-tbl tr:nth-child(even) td{background:#f8fafc}
  .natal-same{color:#22c55e !important;font-weight:600}
  .natal-diff{color:#64748b}
  /* South Indian chart — square responsive cells */
  .si-tbl{width:100%;table-layout:fixed;border-collapse:collapse}
  .si-cell{border:1px solid #cbd5e1;padding:5px 5px 4px;vertical-align:top;
           width:25%;aspect-ratio:1;min-height:72px;background:#f8fafc;position:relative}
  .si-cell-crisis{background:#fff1f2 !important}
  .si-cell-growth{background:#f0fdf4 !important}
  .si-cell-mixed {background:#fefce8 !important}
  .si-cell-lagna {background:#f8fafc}
  /* Diagonal slash overlay for Lagna */
  .si-lagna-slash::after{content:"";position:absolute;inset:0;pointer-events:none;
    background:linear-gradient(45deg,transparent 48%,#ff4b4b 49%,#ff4b4b 51%,transparent 52%)}
  /* Gold conjunction border */
  .si-conjunct{border:3px solid #f59e0b !important}
  /* Planet badge pills */
  .p-badge{display:inline-block;border-radius:99px;padding:1px 7px;font-size:.68rem;
           font-weight:700;margin:1px 1px;line-height:1.5;white-space:nowrap}
  .p-growth{background:#dcfce7;color:#166534}
  .p-crisis{background:#fee2e2;color:#991b1b}
  .p-sun   {background:#fef3c7;color:#92400e}
  .p-moon  {background:#dbeafe;color:#1e40af}
  .p-merc  {background:#ede9fe;color:#5b21b6}
  .p-neut  {background:#f1f5f9;color:#475569}
  /* Sign label */
  .si-sign{font-size:.56rem;color:#94a3b8;text-align:right;line-height:1;margin-bottom:2px}
  /* ASC badge */
  .si-asc{font-size:.56rem;font-weight:700;color:#1d4ed8;background:#dbeafe;
          border-radius:3px;padding:1px 4px;display:inline-block;margin-bottom:2px}
  /* Centre cell */
  .si-centre{background:linear-gradient(135deg,#0f172a,#1e3a5f);border:1px solid #334155;
             text-align:center;vertical-align:middle;padding:8px}
  /* Daily Pulse table */
  .dp-tbl{width:100%;border-collapse:collapse;font-size:.85rem;color:#1e293b}
  .dp-tbl th{background:#1e293b;color:#f1f5f9 !important;padding:9px 12px;
             text-align:left;font-weight:600}
  .dp-tbl td{padding:9px 12px;border-bottom:1px solid #e2e8f0;
             vertical-align:top;color:#1e293b !important;background:#ffffff}
  .dp-tbl tr:nth-child(even) td{background:#f8fafc}
  .dp-badge{display:inline-block;border-radius:6px;padding:2px 8px;font-size:.75rem;
            font-weight:700;margin-right:4px}
  .dp-ok  {background:#dcfce7;color:#166534}
  .dp-warn{background:#fee2e2;color:#991b1b}
  .dp-mid {background:#fef9c3;color:#854d0e}
  /* HTML details/accordion */
  details.ma-accordion{margin-top:8px;border-radius:10px;overflow:hidden;
                        border:1px solid #e2e8f0}
  details.ma-accordion summary{padding:10px 16px;font-weight:700;font-size:.88rem;
    cursor:pointer;background:#f8fafc !important;color:#1e293b !important;list-style:none;
    display:flex;align-items:center;gap:8px}
  details.ma-accordion summary::-webkit-details-marker{display:none}
  details.ma-accordion[open] summary{background:#1e293b !important;color:#f1f5f9 !important}
  details.ma-accordion .acc-body{padding:14px 16px;background:#ffffff !important;
    color:#1e293b !important}
  /* ── Mobile: 768px breakpoint ─────────────────────────────────────── */
  @media(max-width:768px){
    /* Scrollable table wrappers */
    .ma-root{padding:6px}
    /* Cards full-width on mobile */
    .split-card{min-width:unset !important;width:100% !important}
    .ingress-card{min-width:unset !important;width:100% !important}
    .luna-card{min-width:unset !important;width:100% !important}
    /* Stack flex grids to single column */
    .ingress-grid{flex-direction:column !important}
    .luna-list{flex-direction:column !important}
    .split-wrap{flex-direction:column !important}
    /* Smaller table font */
    .pulse-table,.heatmap-tbl,.natal-tbl,.dp-tbl{font-size:.76rem}
    .pulse-table th,.heatmap-tbl th,.natal-tbl th,.dp-tbl th{padding:7px 8px}
    .pulse-table td,.heatmap-tbl td,.natal-tbl td,.dp-tbl td{padding:7px 8px}
    /* Retro banner wraps cleanly */
    .retro-banner{flex-wrap:wrap;gap:6px;padding:8px 10px;font-size:.78rem}
    /* Watch card narrower padding */
    .watch-card{padding:12px 14px}
    .watch-card li{font-size:.82rem}
    /* Gauge */
    .gauge-track{height:20px}
    .gauge-labels{font-size:.65rem}
  }
  /* ── Compact SI chart on very small screens ──────────────────────── */
  @media(max-width:600px){
    .si-cell{min-height:52px;padding:3px}
    .p-badge{font-size:.6rem;padding:1px 5px}
    .si-sign{font-size:.5rem}
    /* Chart title inside centre cell */
    .si-centre{padding:4px}
  }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Datetime helper
# ─────────────────────────────────────────────────────────────────────────────
def _to_utc_datetime(dt_input) -> datetime.datetime:
    if dt_input is None:
        return datetime.datetime.utcnow()
    if isinstance(dt_input, datetime.datetime):
        import pytz
        if dt_input.tzinfo is not None:
            return dt_input.astimezone(pytz.utc).replace(tzinfo=None)
        return dt_input
    return datetime.datetime.utcfromtimestamp(float(dt_input))


# ─────────────────────────────────────────────────────────────────────────────
# HTML renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_gauge_html(score: int, country: str, summary: str) -> str:
    """Horizontal Risk ↔ Reward gauge bar."""
    clamp  = max(2, min(98, score))
    if score >= 68:
        label_color = "#166534"
        badge_cls   = "ma-tag-green"
    elif score <= 32:
        label_color = "#991b1b"
        badge_cls   = "ma-tag-red"
    else:
        label_color = "#854d0e"
        badge_cls   = "ma-tag-yellow"

    return f"""{_CSS}
<div class="ma-root">
  <div class="gauge-wrap">
    <div class="gauge-row">
      <span style="font-weight:700;font-size:1.05rem;color:#1e293b">{country}</span>
      <span class="ma-tag {badge_cls}">{summary}</span>
      <span style="color:{label_color};font-weight:600;font-size:.88rem">{score}/100</span>
    </div>
    <div class="gauge-track">
      <span class="gauge-needle" style="left:{clamp}%">▼</span>
    </div>
    <div class="gauge-labels">
      <span>⚠️ High Risk</span><span>Mixed</span><span>✅ High Growth</span>
    </div>
  </div>
</div>"""


def _render_categorical_pulse_html(pulse: dict) -> str:
    """Styled categorical pulse table."""
    rows = ""
    for domain, d in pulse.items():
        emoji = d["sentiment_emoji"]
        if emoji == "🟢":
            row_style = "background:#f0fdf4"
            tag_cls   = "ma-tag-green"
        elif emoji == "🔴":
            row_style = "background:#fff1f2"
            tag_cls   = "ma-tag-red"
        else:
            row_style = "background:#fefce8"
            tag_cls   = "ma-tag-yellow"

        pos_str  = ", ".join(d["positive_triggers"]) or "—"
        risk_str = ", ".join(d["risk_triggers"])     or "—"
        trigger  = f'<span style="color:#166534">{pos_str}</span>'
        if d["risk_triggers"]:
            trigger += f' &nbsp;|&nbsp; <span style="color:#991b1b">{risk_str}</span>'

        tip_html = ""
        if "market_tip" in d:
            tip_html = f'<div class="ma-tip">{d["market_tip"]}</div>'

        rows += f"""
<tr>
  <td style="{row_style};color:#1e293b;padding:9px 12px;border-bottom:1px solid #e2e8f0;vertical-align:top">
    <b style="color:#1e293b">{d["icon"]} {domain}</b>{tip_html}
  </td>
  <td style="{row_style};color:#1e293b;padding:9px 12px;border-bottom:1px solid #e2e8f0;font-weight:600">
    {d["status"]}
  </td>
  <td style="{row_style};color:#1e293b;padding:9px 12px;border-bottom:1px solid #e2e8f0">
    {emoji} <span class="ma-tag {tag_cls}">{d["sentiment_label"]}</span>
  </td>
  <td style="{row_style};color:#1e293b;padding:9px 12px;border-bottom:1px solid #e2e8f0;font-size:.82rem">
    {trigger}
  </td>
</tr>"""

    return f"""{_CSS}
<div class="ma-root">
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table class="pulse-table" style="min-width:480px">
      <thead>
        <tr>
          <th>Category</th><th>Status</th><th>Sentiment</th><th>Planetary Trigger</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def _render_analysis_cards_html(bright_side: str, strategic_risks: str,
                                  market_tip: str = "") -> str:
    """Side-by-side Bright Side vs Strategic Risks inside a collapsible accordion."""
    LI = 'style="margin-bottom:6px;color:#1e293b !important;font-size:.87rem;line-height:1.7"'
    UL = 'style="margin:0;padding-left:18px;color:#1e293b !important"'

    def _to_li(text: str) -> str:
        bullets = _text_to_bullets(text)
        items = bullets if bullets else [text]
        return "".join(f'<li {LI}>{b}</li>' for b in items if b)

    bright_li = _to_li(bright_side)
    risks_li  = _to_li(strategic_risks)

    tip_html = ""
    if market_tip:
        tip_html = (
            f'<div style="margin-top:10px;padding:8px 12px;background:#eff6ff !important;'
            f'border-radius:8px;font-size:.82rem;color:#1e40af !important">{market_tip}</div>'
        )

    CARD_BASE = (
        "flex:1;min-width:260px;border-radius:12px;padding:16px 18px;"
        "font-size:.87rem;color:#1e293b !important"
    )
    H4 = 'style="margin:0 0 10px;font-size:.95rem;font-weight:700;color:#1e293b !important"'

    inner = f"""
  <div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:6px">
    <div style="{CARD_BASE};background:#f0fdf4 !important;border:1px solid #86efac">
      <h4 {H4}>🌟 The Bright Side</h4>
      <ul {UL}>{bright_li}</ul>
    </div>
    <div style="{CARD_BASE};background:#fff1f2 !important;border:1px solid #fca5a5">
      <h4 {H4}>⚠️ Strategic Risks</h4>
      <ul {UL}>{risks_li}</ul>
      {tip_html}
    </div>
  </div>"""

    return f"""{_CSS}
<div class="ma-root">
  <details class="ma-accordion">
    <summary>📚 Detailed Astro-Synthesis — click to expand</summary>
    <div class="acc-body" style="background:#ffffff !important;padding:14px 16px">{inner}</div>
  </details>
</div>"""


def _render_heatmap_html(rows: list) -> str:
    """Global heatmap table with icon-based planet cells."""
    header_cells = "".join(f"<th>{p}</th>" for p in PLANET_ORDER)
    tbody = ""
    for row in rows:
        if row["summary"] == "High Risk":
            row_cls = "hm-high-risk"
            badge   = '<span class="ma-tag ma-tag-red">High Risk</span>'
        elif row["summary"] == "High Growth":
            row_cls = "hm-high-growth"
            badge   = '<span class="ma-tag ma-tag-green">High Growth</span>'
        else:
            row_cls = "hm-mixed"
            badge   = '<span class="ma-tag ma-tag-yellow">Mixed</span>'

        if row["summary"] == "High Risk":
            bg = "#fff1f2"
        elif row["summary"] == "High Growth":
            bg = "#f0fdf4"
        else:
            bg = "#fefce8"

        td_base = f'style="background:{bg};color:#1e293b"'

        planet_cells = ""
        for p in PLANET_ORDER:
            pd_ = row["planets"].get(p, {})
            house = pd_.get("house", "?")
            icon  = pd_.get("icon", "")
            color = pd_.get("color", "#475569")
            planet_cells += (
                f'<td style="background:{bg};color:{color};font-weight:700">'
                f'{icon} H{house}</td>'
            )

        tbody += f"""
<tr>
  <td style="background:{bg};color:#1e293b;font-weight:700">{row['country']}</td>
  <td style="background:{bg};color:#475569;font-size:.8rem">{row['lagna']}</td>
  <td style="background:{bg}">{badge}</td>
  {planet_cells}
</tr>"""

    return f"""{_CSS}
<div class="ma-root">
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table class="heatmap-tbl" style="min-width:600px">
      <thead>
        <tr>
          <th>Country</th><th>Lagna</th><th>Summary</th>
          {header_cells}
        </tr>
      </thead>
      <tbody>{tbody}</tbody>
    </table>
  </div>
  <div class="hm-legend">
    💰 Economy &nbsp;|&nbsp; 🛡️ Security &nbsp;|&nbsp; 🏛️ Governance &nbsp;|&nbsp; 🚀 Tech/Media
  </div>
</div>"""


def _render_mundane_html(text: str, country: str) -> str:
    """Mundane events context as a clean card."""
    bullets = _text_to_bullets(text)
    if bullets:
        li_html = "".join(
            f'<li style="margin-bottom:8px;color:#1e293b !important">{b}</li>'
            for b in bullets
        )
    elif text.strip():
        li_html = f'<li style="color:#1e293b !important">{text.strip()}</li>'
    else:
        li_html = '<li style="color:#64748b !important"><em>Set OPENAI_API_KEY to enable AI-generated mundane context.</em></li>'

    return f"""{_CSS}
<div class="ma-root">
  <div style="background:#f8fafc !important;border-left:5px solid #94a3b8;border-radius:12px;
              padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.08)">
    <h4 style="margin:0 0 12px;font-weight:700;font-size:1rem;color:#1e293b !important">
      🌍 Mundane Events Context — {country}
    </h4>
    <ul style="margin:0;padding-left:20px;font-size:.88rem;line-height:1.85;color:#1e293b !important">
      {li_html}
    </ul>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# New: Watch-tab HTML renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_retro_banner(retro_status: dict) -> str:
    """Dark banner showing currently retrograde planets + upcoming stations."""
    currently = retro_status.get("currently_retrograde", [])
    stations  = retro_status.get("upcoming_stations", [])

    if currently:
        pills = " ".join(f'<span class="retro-pill">{p} ℞</span>' for p in currently)
        retro_html = f'<span style="color:#f1f5f9;font-weight:600">Currently Retrograde:</span> {pills}'
    else:
        retro_html = '<span style="color:#86efac">✅ No planets retrograde right now</span>'

    station_html = ""
    if stations:
        sp = " ".join(
            f'<span class="station-pill">{s["planet"]} {s["event"]} — {s["days_away"]}d ({s["date"]})</span>'
            for s in stations[:4]
        )
        station_html = f'<div style="margin-top:6px"><span style="color:#f1f5f9;font-size:.78rem">Upcoming:</span> {sp}</div>'

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div class="retro-banner">
    <span style="font-size:.85rem;font-weight:700;color:#fbbf24">🔄 Retrograde Tracker</span>
    <span>{retro_html}</span>
  </div>
  {f'<div class="retro-banner" style="margin-top:6px">{station_html}</div>' if station_html else ''}
</div>"""


def _render_ingress_cards(ingresses: list) -> str:
    """Grid of upcoming planet sign-change cards."""
    cards = ""
    for ing in ingresses:
        urgent_style = "border-color:#f97316;border-width:2px" if ing["days_away"] <= 7 else ""
        cards += f"""
<div class="ingress-card" style="{urgent_style}">
  <div class="planet">🪐 {ing['planet']}</div>
  <div class="arrow" style="color:#1e293b">{ing['from_sign']} → <strong style="color:#7c3aed">{ing['to_sign']}</strong></div>
  <div class="days">{ing['days_away']}d</div>
  <div class="date" style="color:#64748b">{ing['date']}</div>
  <div class="houses" style="color:#475569">{ing['house_impact']}</div>
</div>"""

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div style="font-weight:700;font-size:.9rem;color:#1e293b;margin-bottom:8px">
    🚀 Planet Ingress Countdown
  </div>
  <div class="ingress-grid">{cards}</div>
  <div style="font-size:.72rem;color:#64748b;margin-top:4px">
    House impact: I=India · U=USA · C=China · E=EU &nbsp;|&nbsp; 🟠 = within 7 days
  </div>
</div>"""


def _render_lunation_alerts(lunations: list) -> str:
    """Cards for upcoming New Moon / Full Moon / Eclipse events."""
    cards = ""
    for ev in lunations:
        if "Eclipse" in ev["type"]:
            cls = "luna-eclipse"
        elif "New" in ev["type"]:
            cls = "luna-new"
        else:
            cls = "luna-full"

        cards += f"""
<div class="luna-card {cls}">
  <div class="ltype" style="color:#1e293b">{ev['type']}</div>
  <div class="lsign" style="color:#475569">in <strong style="color:#1e293b">{ev['sign']}</strong></div>
  <div class="ldays" style="color:#7c3aed">{ev['days_away']}d — {ev['date']}</div>
  <div class="lhouses" style="color:#475569">{ev['house_impact']}</div>
</div>"""

    if not cards:
        cards = '<div style="color:#64748b;font-size:.85rem">No lunations found in scan range.</div>'

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div style="font-weight:700;font-size:.9rem;color:#1e293b;margin-bottom:8px">
    🌙 Eclipse & Lunation Alerts
  </div>
  <div class="luna-list">{cards}</div>
</div>"""


def _render_watch_summary(text: str) -> str:
    """Dark gradient card for the 'What to Watch' AI summary."""
    bullets = _text_to_bullets(text)
    if bullets:
        li_html = "".join(f'<li style="color:#e2e8f0">{b}</li>' for b in bullets)
    elif text.strip():
        li_html = f'<li style="color:#e2e8f0">{text.strip()}</li>'
    else:
        li_html = '<li style="color:#94a3b8"><em>Set OPENAI_API_KEY to enable this summary.</em></li>'

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div class="watch-card">
    <h3 style="color:#fbbf24">🔭 What to Watch This Week</h3>
    <ul>{li_html}</ul>
  </div>
</div>"""


def _render_natal_chart(country: str, natal_data: dict,
                         transit_data: dict, house_pos: dict) -> str:
    """Side-by-side natal vs transit table for one country."""
    event = natal_data.get("_event", "")
    lagna  = natal_data.get("_lagna", "")

    rows = ""
    for planet in VEDIC_PLANETS:
        nat  = natal_data.get(planet, {})
        tran = transit_data.get(planet, {})
        if not nat or not tran:
            continue

        nat_sign  = nat.get("sign",  "?")
        nat_house = nat.get("house", "?")
        tr_sign   = tran.get("sign", "?")
        tr_house  = house_pos.get(planet, "?")
        retro     = "℞" if tran.get("retrograde") else ""

        # Highlight when transit sign matches natal sign (planet returns home)
        match_cls = "natal-same" if nat_sign == tr_sign else "natal-diff"

        rows += f"""
<tr>
  <td style="font-weight:600;color:#1e293b;background:#f8fafc">{planet}</td>
  <td style="color:#1e293b;background:#ffffff">{nat_sign}</td>
  <td style="color:#475569;background:#ffffff;text-align:center">{nat_house}</td>
  <td class="{match_cls}" style="background:#ffffff">{tr_sign} {retro}</td>
  <td style="color:#475569;background:#ffffff;text-align:center">{tr_house}</td>
</tr>"""

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div style="margin-bottom:10px">
    <span style="font-weight:700;font-size:.95rem;color:#1e293b">
      📜 {country} Natal Chart vs Current Transits
    </span><br>
    <span style="font-size:.78rem;color:#64748b">{event}</span><br>
    <span style="font-size:.78rem;color:#475569">Lagna: <strong style="color:#1e293b">{lagna}</strong></span>
  </div>
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table class="natal-tbl" style="min-width:400px">
      <thead>
        <tr>
          <th>Planet</th>
          <th>Natal Sign</th>
          <th style="text-align:center">Natal H</th>
          <th>Transit Sign</th>
          <th style="text-align:center">Transit H</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div style="font-size:.72rem;color:#64748b;margin-top:6px">
    🟢 Green = planet transiting its natal sign
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# South Indian Square Chart renderer
# ─────────────────────────────────────────────────────────────────────────────

# Fixed sign positions in the 4×4 South Indian grid (-1 = center merged cell)
_SI_GRID = [
    [11,  0,  1,  2],   # Pisces  Aries  Taurus   Gemini
    [10, -1, -1,  3],   # Aquarius  CENTER    Cancer
    [ 9, -1, -1,  4],   # Capricorn  CENTER    Leo
    [ 8,  7,  6,  5],   # Sagittarius  Scorpio  Libra  Virgo
]

_SIGN_ABBR = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
_SIGN_SYM  = ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓"]

_PLANET_SHORT = {
    "Sun":"Su","Moon":"Mo","Mercury":"Me","Venus":"Ve","Mars":"Ma",
    "Jupiter":"Ju","Saturn":"Sa","Rahu":"Ra","Ketu":"Ke",
}
_PLANET_COLOR = {
    "Sun":     "#d97706",
    "Moon":    "#2563eb",
    "Mercury": "#7c3aed",
    "Venus":   "#16a34a",
    "Mars":    "#dc2626",
    "Jupiter": "#15803d",
    "Saturn":  "#92400e",
    "Rahu":    "#991b1b",
    "Ketu":    "#9f1239",
}
_CRISIS_SET = {"Mars", "Rahu", "Saturn", "Ketu"}
_GROWTH_SET = {"Jupiter", "Venus"}


def draw_south_indian_chart(
    planet_sign_map: dict,
    lagna_sign_index: int,
    chart_title: str,
    chart_subtitle: str = "",
    retro_set: set = None,
    natal_sign_map: dict = None,
) -> str:
    """
    Render a South Indian 4×4 square chart as an HTML table.

    planet_sign_map  : {planet_name: sign_index (0-11)}
    lagna_sign_index : 0-11 — Lagna/ASC sign
    retro_set        : planet names currently retrograde
    natal_sign_map   : if provided, signs occupied by natal planets get gold border
    """
    if retro_set is None:
        retro_set = set()

    # Build sign_index → [planet names] mapping
    sign_planets: dict = {i: [] for i in range(12)}
    for planet, idx in planet_sign_map.items():
        if 0 <= idx <= 11:
            sign_planets[idx].append(planet)

    # Signs with natal planets (for conjunction border)
    natal_signs: set = set()
    if natal_sign_map:
        natal_signs = {idx for idx in natal_sign_map.values() if 0 <= idx <= 11}

    def _badge(planet: str, retro: bool) -> str:
        """Fully inline-styled pill badge — immune to Gradio theme overrides."""
        short = _PLANET_SHORT.get(planet, planet[:2])
        mark  = "℞" if retro else ""
        if planet in _GROWTH_SET:
            bg, fg = "#dcfce7", "#166534"
        elif planet in _CRISIS_SET:
            bg, fg = "#fee2e2", "#991b1b"
        elif planet == "Sun":
            bg, fg = "#fef3c7", "#92400e"
        elif planet == "Moon":
            bg, fg = "#dbeafe", "#1e40af"
        elif planet == "Mercury":
            bg, fg = "#ede9fe", "#5b21b6"
        else:
            bg, fg = "#f1f5f9", "#475569"
        return (
            f'<span style="display:inline-block;border-radius:99px;padding:1px 7px;'
            f'font-size:.7rem;font-weight:700;margin:1px 1px 2px;'
            f'background:{bg};color:{fg} !important;'
            f'line-height:1.5;white-space:nowrap">{short}{mark}</span>'
        )

    def _cell(sign_idx: int) -> str:
        planets  = sign_planets[sign_idx]
        is_lagna = (sign_idx == lagna_sign_index)

        crisis   = any(p in _CRISIS_SET for p in planets)
        growth   = any(p in _GROWTH_SET for p in planets)
        conjunct = natal_sign_map is not None and sign_idx in natal_signs and bool(planets)

        if crisis and growth:
            bg = "#fefce8"
        elif crisis:
            bg = "#fff1f2"
        elif growth:
            bg = "#f0fdf4"
        else:
            bg = "#f8fafc"

        border = "3px solid #f59e0b" if conjunct else "1px solid #cbd5e1"

        # Lagna: overlay diagonal red slash on cell background
        lagna_grad = (
            ",linear-gradient(45deg,transparent 48%,"
            "#ff4b4b 49%,#ff4b4b 51%,transparent 52%)"
            if is_lagna else ""
        )

        td_style = (
            f"background:{bg}{lagna_grad};border:{border};"
            f"padding:5px 5px 4px;vertical-align:top;"
            f"width:25%;min-height:80px;position:relative;"
        )

        sign_label = (
            f'<div style="font-size:.58rem;color:#94a3b8 !important;'
            f'text-align:right;line-height:1;margin-bottom:2px">'
            f'{_SIGN_SYM[sign_idx]} {_SIGN_ABBR[sign_idx]}</div>'
        )

        asc_html = ""
        if is_lagna:
            asc_html = (
                '<div style="font-size:.56rem;font-weight:700;color:#1d4ed8 !important;'
                'background:#dbeafe;border-radius:3px;padding:1px 4px;'
                'display:inline-block;margin-bottom:2px">ASC</div>'
            )

        badges = "".join(_badge(p, p in retro_set) for p in planets)
        return f'<td style="{td_style}">{sign_label}{asc_html}{badges}</td>'

    # Centre merged cell (2 cols × 2 rows) — fully inline styled
    centre = (
        f'<td colspan="2" rowspan="2" style="'
        f'background:linear-gradient(135deg,#0f172a,#1e3a5f);'
        f'border:1px solid #334155;text-align:center;vertical-align:middle;padding:8px">'
        f'<div style="color:#fbbf24 !important;font-weight:700;font-size:.85rem">{chart_title}</div>'
        f'<div style="color:#94a3b8 !important;font-size:.63rem;margin-top:4px">{chart_subtitle}</div>'
        f'</td>'
    )

    row0 = f"<tr>{_cell(11)}{_cell(0)}{_cell(1)}{_cell(2)}</tr>"
    row1 = f"<tr>{_cell(10)}{centre}{_cell(3)}</tr>"
    row2 = f"<tr>{_cell(9)}{_cell(4)}</tr>"
    row3 = f"<tr>{_cell(8)}{_cell(7)}{_cell(6)}{_cell(5)}</tr>"

    tbl_style = (
        "border-collapse:collapse;width:100%;table-layout:fixed;"
        "font-family:'Segoe UI',system-ui,sans-serif;"
    )
    return f'<table style="{tbl_style}">{row0}{row1}{row2}{row3}</table>'


def render_south_indian_html(planet_data: dict, lagna_sign: str,
                              chart_title: str = "", chart_subtitle: str = "",
                              natal_planet_data: dict = None) -> str:
    """
    Public API: render South Indian chart from full planet_data dicts.

    planet_data       : {planet: {sign_index, retrograde, ...}}
    lagna_sign        : sign name string e.g. "Taurus"
    natal_planet_data : if provided, conjunctions (transit on natal sign) are highlighted
    """
    from astrology_engine import RASIS_ENGLISH
    lagna_idx = RASIS_ENGLISH.index(lagna_sign) if lagna_sign in RASIS_ENGLISH else 0
    sign_map  = {p: d["sign_index"] for p, d in planet_data.items()
                 if isinstance(d, dict) and "sign_index" in d}
    retro_set = {p for p, d in planet_data.items()
                 if isinstance(d, dict) and d.get("retrograde")}
    natal_map = None
    if natal_planet_data:
        natal_map = {p: d["sign_index"] for p, d in natal_planet_data.items()
                     if isinstance(d, dict) and "sign_index" in d}
    return draw_south_indian_chart(sign_map, lagna_idx, chart_title, chart_subtitle,
                                   retro_set, natal_map)


def _render_chart_legend() -> str:
    def _pill(bg, border, text):
        return (f'<span style="background:{bg} !important;color:#1e293b !important;'
                f'padding:1px 6px;border-radius:4px;border:1px solid {border}">{text}</span>')
    return (
        '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;font-size:.72rem;'
        'color:#1e293b !important;align-items:center;background:#f8fafc !important;'
        'border-radius:8px;padding:8px 12px">'
        '<strong style="color:#1e293b !important">Legend:</strong>'
        f'<span style="color:#1e293b !important">🟢 {_pill("#f0fdf4","#86efac","Benefic — Growth/Economy")}</span>'
        f'<span style="color:#1e293b !important">🔴 {_pill("#fff1f2","#fca5a5","Malefic — Risk/Conflict")}</span>'
        f'<span style="color:#1e293b !important">🟡 {_pill("#fefce8","#fde047","Mixed Influence")}</span>'
        '<span style="color:#1e293b !important">⭐ '
        '<span style="border:3px solid #f59e0b;padding:1px 6px;border-radius:4px;'
        'color:#1e293b !important">Natal + Transit Conjunction</span></span>'
        '<span style="color:#64748b !important">ASC = Country Lagna &nbsp;|&nbsp; ℞ = Retrograde</span>'
        '</div>'
    )


# Air sign indices: Gemini=2, Libra=6, Aquarius=10
_AIR_SIGNS = {2, 6, 10}


def _render_daily_pulse(house_pos: dict, transit_data: dict, country: str) -> str:
    """
    Build a 4-row 'Daily Pulse' summary table for Finance, Governance,
    Tech/Innovation, and Risk domains.
    """
    # ── Finance (H2 / H11) ────────────────────────────────────────────────
    finance_planets = [p for p, h in house_pos.items() if h in {2, 11}]
    fin_benefics = [p for p in finance_planets if p in _GROWTH_SET]
    fin_malefics = [p for p in finance_planets if p in _CRISIS_SET]
    if fin_benefics and not fin_malefics:
        fin_badge, fin_status = "dp-ok",   "💚 Bullish"
        fin_note = f"Benefic{'s' if len(fin_benefics)>1 else ''} ({', '.join(fin_benefics)}) in wealth houses"
    elif fin_malefics and not fin_benefics:
        fin_badge, fin_status = "dp-warn", "🔴 Bearish pressure"
        fin_note = f"Malefic{'s' if len(fin_malefics)>1 else ''} ({', '.join(fin_malefics)}) in wealth houses"
    elif fin_benefics and fin_malefics:
        fin_badge, fin_status = "dp-mid",  "🟡 Mixed signals"
        fin_note = f"Both benefics ({', '.join(fin_benefics)}) & malefics ({', '.join(fin_malefics)}) active"
    else:
        fin_badge, fin_status = "dp-mid",  "🟡 Neutral"
        fin_note = "No dominant influence on H2/H11"

    # ── Governance (H10) ──────────────────────────────────────────────────
    gov_planets = [p for p, h in house_pos.items() if h == 10]
    gov_strong  = [p for p in gov_planets if p in {"Sun", "Jupiter"}]
    gov_stress  = [p for p in gov_planets if p in {"Saturn", "Rahu"}]
    if gov_strong and not gov_stress:
        gov_badge, gov_status = "dp-ok",   "💚 Leadership stable"
        gov_note = f"{', '.join(gov_strong)} in H10 — policy momentum"
    elif gov_stress:
        gov_badge, gov_status = "dp-warn", "🔴 Political tension"
        gov_note = f"{', '.join(gov_stress)} in H10 — bureaucratic gridlock risk"
    elif gov_planets:
        gov_badge, gov_status = "dp-mid",  "🟡 Under watch"
        gov_note = f"{', '.join(gov_planets)} in H10 — monitoring advised"
    else:
        gov_badge, gov_status = "dp-ok",   "🟢 Stable"
        gov_note = "No major planetary pressure on H10"

    # ── Tech / Innovation (Mercury + Rahu in Air signs) ───────────────────
    merc_data  = transit_data.get("Mercury", {})
    rahu_data  = transit_data.get("Rahu", {})
    merc_air   = merc_data.get("sign_index", -1) in _AIR_SIGNS
    rahu_air   = rahu_data.get("sign_index", -1) in _AIR_SIGNS
    merc_retro = merc_data.get("retrograde", False)
    if merc_retro:
        tech_badge, tech_status = "dp-warn", "⚠️ Comms disrupted"
        tech_note = f"Mercury retrograde in {merc_data.get('sign','?')} — delays, contract renegotiations"
    elif merc_air and rahu_air:
        tech_badge, tech_status = "dp-ok",   "💚 Innovation surge"
        tech_note = f"Mercury + Rahu both in Air signs — rapid ideas & tech breakthroughs"
    elif merc_air or rahu_air:
        active = "Mercury" if merc_air else "Rahu"
        sign   = merc_data.get("sign","?") if merc_air else rahu_data.get("sign","?")
        tech_badge, tech_status = "dp-ok",   "🟢 Moderate momentum"
        tech_note = f"{active} in Air sign ({sign}) — steady digital/media activity"
    else:
        tech_badge, tech_status = "dp-mid",  "🟡 Routine"
        tech_note = "Mercury & Rahu not in Air signs — standard tech cadence"

    # ── Risks (H6 / H8 / H12) ────────────────────────────────────────────
    risk_planets = [p for p, h in house_pos.items() if h in {6, 8, 12}]
    active_risks = [p for p in risk_planets if p in _CRISIS_SET]
    if len(active_risks) >= 2:
        risk_badge, risk_status = "dp-warn", "🔴 High alert"
        risk_note = f"Multiple malefics ({', '.join(active_risks)}) in crisis houses (H6/H8/H12)"
    elif len(active_risks) == 1:
        risk_badge, risk_status = "dp-mid",  "⚠️ Elevated risk"
        risk_note = f"{active_risks[0]} in adversarial house — watch for disputes or hidden threats"
    elif risk_planets:
        risk_badge, risk_status = "dp-mid",  "🟡 Mild caution"
        risk_note = f"{', '.join(risk_planets)} in H6/H8/H12 — minor turbulence possible"
    else:
        risk_badge, risk_status = "dp-ok",   "🟢 Low risk"
        risk_note = "No malefics in crisis houses — calm operational environment"

    _DP_BADGE = {
        "dp-ok":   ("background:#dcfce7 !important;color:#166534 !important", "#dcfce7", "#166534"),
        "dp-warn": ("background:#fee2e2 !important;color:#991b1b !important", "#fee2e2", "#991b1b"),
        "dp-mid":  ("background:#fef9c3 !important;color:#854d0e !important", "#fef9c3", "#854d0e"),
    }

    def _row(icon, category, badge_cls, status, note):
        style_str, _bg, _fg = _DP_BADGE.get(
            badge_cls,
            ("background:#f1f5f9 !important;color:#475569 !important", "#f1f5f9", "#475569")
        )
        return (
            f"<tr>"
            f'<td style="font-weight:700;color:#1e293b !important;background:#f8fafc !important;'
            f'padding:9px 12px;border-bottom:1px solid #e2e8f0">{icon} {category}</td>'
            f'<td style="background:#ffffff !important;padding:9px 12px;border-bottom:1px solid #e2e8f0">'
            f'<span style="display:inline-block;border-radius:6px;padding:2px 10px;font-size:.78rem;'
            f'font-weight:700;{style_str}">{status}</span></td>'
            f'<td style="font-size:.82rem;color:#475569 !important;background:#ffffff !important;'
            f'padding:9px 12px;border-bottom:1px solid #e2e8f0">{note}</td>'
            f"</tr>"
        )

    rows = (
        _row("💰", "Finance", fin_badge, fin_status, fin_note)
        + _row("🏛️", "Governance", gov_badge, gov_status, gov_note)
        + _row("🚀", "Tech / Innovation", tech_badge, tech_status, tech_note)
        + _row("⚠️", "Risks", risk_badge, risk_status, risk_note)
    )

    return f"""{_CSS}
<div class="ma-root">
  <div style="font-weight:700;font-size:.88rem;color:#1e293b;margin-bottom:6px">
    📊 Daily Pulse — {country}
  </div>
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table class="dp-tbl" style="min-width:420px">
      <thead>
        <tr>
          <th style="width:28%">Domain</th>
          <th style="width:24%">Signal</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Raw ephemeris DataFrame
# ─────────────────────────────────────────────────────────────────────────────
def _build_raw_ephemeris_df(transit_data: dict) -> pd.DataFrame:
    rows = []
    for planet in VEDIC_PLANETS:
        if planet not in transit_data:
            continue
        d = transit_data[planet]
        rows.append({
            "Planet":         planet,
            "Longitude (°)":  d["longitude"],
            "Sign (Tamil)":   d["rasi"],
            "Sign (English)": d["sign"],
            "Nakshatra":      d["nakshatra"],
            "Pada":           d["pada"],
            "Status":         "Retrograde (R)" if d["retrograde"] else "Direct",
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Core calculation functions
# ─────────────────────────────────────────────────────────────────────────────
def run_calculations(dt_input):
    """Tab 1: Global Heatmap."""
    dt         = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    all_hp     = get_all_house_positions(transit_data)

    all_data = {}
    for country in COUNTRIES:
        hp    = all_hp[country]
        cats  = categorize_transits(hp)
        pulse = build_categorical_pulse(transit_data, hp)
        all_data[country] = {
            "house_positions": hp,
            "categories":      cats,
            "summary":         get_country_summary(cats),
            "pulse":           pulse,
        }

    heatmap_rows = build_heatmap_data(transit_data, all_data)
    heatmap_html = _render_heatmap_html(heatmap_rows)
    raw_df       = _build_raw_ephemeris_df(transit_data)
    return heatmap_html, raw_df


def mundane_analysis(dt_input, country):
    """Tab 3: Mundane Events Context + Raw Ephemeris."""
    dt           = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    house_pos    = get_house_positions(transit_data, country)
    categories   = categorize_transits(house_pos)

    llm    = generate_llm_analysis(
        country, transit_data, house_pos, categories, OPENAI_API_KEY
    )
    raw_df = _build_raw_ephemeris_df(transit_data)

    mundane_html = _render_mundane_html(llm["mundane_context"], country)
    return mundane_html, raw_df


def regional_analysis(dt_input, country):
    """Tab 2: Gauge + Categorical Pulse + Analysis Cards + Natal Chart."""
    dt           = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    house_pos    = get_house_positions(transit_data, country)
    categories   = categorize_transits(house_pos)
    summary      = get_country_summary(categories)
    pulse        = build_categorical_pulse(transit_data, house_pos)

    scores        = [v["score"] for v in pulse.values()]
    overall_score = int(sum(scores) / len(scores)) if scores else 50

    gauge_html  = _render_gauge_html(overall_score, country, summary)
    pulse_html  = _render_categorical_pulse_html(pulse)

    llm = generate_llm_analysis(
        country, transit_data, house_pos, categories, OPENAI_API_KEY
    )

    market_tip = pulse.get("Share Market & Economy", {}).get("market_tip", "")
    cards_html = _render_analysis_cards_html(
        llm["bright_side"], llm["strategic_risks"], market_tip
    )

    natal_data  = get_natal_chart(country)
    natal_html  = _render_natal_chart(country, natal_data, transit_data, house_pos)

    return gauge_html, pulse_html, cards_html, natal_html


def weekly_watch(dt_input):
    """Tab 4: Retrograde banner + Ingress countdown + Lunation alerts + Watch summary."""
    dt           = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    all_hp       = get_all_house_positions(transit_data)

    all_data = {}
    for country in COUNTRIES:
        hp    = all_hp[country]
        cats  = categorize_transits(hp)
        pulse = build_categorical_pulse(transit_data, hp)
        all_data[country] = {
            "house_positions": hp,
            "categories":      cats,
            "summary":         get_country_summary(cats),
            "pulse":           pulse,
        }

    retro_status = get_retrograde_status(transit_data, dt)
    ingresses    = get_next_ingresses(dt, max_days=90, top_n=8)
    lunations    = get_next_lunations(dt, count=5)
    watch_text   = generate_watch_summary(
        all_data, ingresses, retro_status, lunations, OPENAI_API_KEY
    )

    retro_html    = _render_retro_banner(retro_status)
    ingress_html  = _render_ingress_cards(ingresses)
    lunation_html = _render_lunation_alerts(lunations)
    watch_html    = _render_watch_summary(watch_text)

    return retro_html, ingress_html, lunation_html, watch_html


def _render_quick_pulse(house_pos: dict, transit_data: dict, country: str) -> str:
    """
    Financial-dashboard-style 'Quick Summary Pulse' table.
    5 rows: Finance · Security · Governance · Tech · Hidden Risks
    Special rule: Mars + Rahu both in H10 → 'Hidden Tensions'.
    """
    mars_h  = house_pos.get("Mars", 0)
    rahu_h  = house_pos.get("Rahu", 0)
    ketu_h  = house_pos.get("Ketu", 0)
    sat_h   = house_pos.get("Saturn", 0)
    jup_h   = house_pos.get("Jupiter", 0)
    ven_h   = house_pos.get("Venus", 0)
    sun_h   = house_pos.get("Sun", 0)
    merc_td = transit_data.get("Mercury", {})
    rahu_td = transit_data.get("Rahu", {})
    merc_retro = merc_td.get("retrograde", False)
    merc_sign  = merc_td.get("sign_index", -1)
    rahu_sign  = rahu_td.get("sign_index", -1)

    rows_data = []

    # ── Finance (H2 / H11) ────────────────────────────────────────────────
    fin_ben = [p for p, h in [("Jupiter", jup_h), ("Venus", ven_h)] if h in {2, 11}]
    fin_mal = [p for p, h in [("Mars", mars_h), ("Saturn", sat_h), ("Rahu", rahu_h)] if h in {2, 11}]
    if fin_ben and not fin_mal:
        rows_data.append(("💰", "Finance", "#22c55e", "Expansionary",
                          f"{', '.join(fin_ben)} in wealth house(s) — growth-oriented outlook"))
    elif fin_mal and not fin_ben:
        rows_data.append(("💰", "Finance", "#ef4444", "Contraction Risk",
                          f"{', '.join(fin_mal)} pressuring H2/H11 — cautious stance advised"))
    elif fin_ben and fin_mal:
        rows_data.append(("💰", "Finance", "#eab308", "Mixed Outlook",
                          f"Competing signals: {', '.join(fin_ben)} vs {', '.join(fin_mal)}"))
    else:
        rows_data.append(("💰", "Finance", "#94a3b8", "Neutral",
                          "No dominant planetary influence on wealth houses"))

    # ── National Security (H1/H6/H7/H8/H12) ──────────────────────────────
    hostile_h  = {1, 6, 7, 8, 12}
    sec_malef  = [p for p, h in [("Mars", mars_h), ("Rahu", rahu_h), ("Ketu", ketu_h)]
                  if h in hostile_h]
    if mars_h in hostile_h and rahu_h in hostile_h and mars_h == rahu_h:
        rows_data.append(("🛡️", "National Security", "#ef4444", "Imminent Risk",
                          f"Mars + Rahu conjunct in H{mars_h} — conflict/covert threat heightened"))
    elif mars_h == 8:
        rows_data.append(("🛡️", "National Security", "#ef4444", "Sudden Strike Risk",
                          "Mars in H8 — unexpected confrontations, hidden enemies active"))
    elif jup_h in {6, 9}:
        rows_data.append(("🛡️", "National Security", "#22c55e", "Diplomatic Strength",
                          f"Jupiter in H{jup_h} — strong foreign affairs, legal protections"))
    elif sec_malef:
        rows_data.append(("🛡️", "National Security", "#eab308", "Elevated Vigilance",
                          f"{', '.join(sec_malef)} in adversarial houses — monitor border/intel"))
    else:
        rows_data.append(("🛡️", "National Security", "#22c55e", "Stable",
                          "No critical planetary stress on security houses"))

    # ── Governance (H10) — Mars+Rahu special rule ─────────────────────────
    if mars_h == 10 and rahu_h == 10:
        rows_data.append(("🏛️", "Governance", "#ef4444", "Hidden Tensions",
                          "Mars + Rahu in H10 — covert power struggles, leadership credibility at risk"))
    elif sun_h == 10 and jup_h in {1, 5, 9, 10}:
        rows_data.append(("🏛️", "Governance", "#22c55e", "Policy Momentum",
                          f"Sun in H10, Jupiter in H{jup_h} — decisive leadership, reform-friendly"))
    elif sat_h == 10:
        rows_data.append(("🏛️", "Governance", "#eab308", "Slow Reform",
                          "Saturn in H10 — methodical restructuring, institutional discipline"))
    elif rahu_h == 10:
        rows_data.append(("🏛️", "Governance", "#eab308", "Unconventional Push",
                          "Rahu in H10 — maverick leadership, non-traditional policy approaches"))
    else:
        h10_planets = [p for p, h in house_pos.items() if h == 10] or ["None"]
        rows_data.append(("🏛️", "Governance", "#eab308", "Strategic Transition",
                          f"H10: {', '.join(h10_planets)} — steady but watch for sudden shifts"))

    # ── Tech & Innovation (Mercury / Rahu + Air signs) ────────────────────
    if merc_retro:
        rows_data.append(("🚀", "Tech & Innovation", "#ef4444", "Disruption Alert",
                          f"Mercury ℞ in {merc_td.get('sign','?')} — system failures, contract delays"))
    elif merc_sign in _AIR_SIGNS and rahu_sign in _AIR_SIGNS:
        rows_data.append(("🚀", "Tech & Innovation", "#22c55e", "Innovation Surge",
                          "Mercury + Rahu both in Air signs — rapid breakthroughs, viral media"))
    elif merc_sign in _AIR_SIGNS:
        rows_data.append(("🚀", "Tech & Innovation", "#22c55e", "Active Development",
                          f"Mercury in Air sign ({merc_td.get('sign','?')}) — steady digital momentum"))
    else:
        rows_data.append(("🚀", "Tech & Innovation", "#94a3b8", "Standard Cycle",
                          "Mercury not in Air sign — incremental, not breakthrough, progress"))

    # ── Hidden Risks (H6/H8/H12) ──────────────────────────────────────────
    risk_active = [(p, h) for p, h in house_pos.items() if p in _CRISIS_SET and h in {6, 8, 12}]
    if len(risk_active) >= 2:
        detail = ", ".join(f"{p}(H{h})" for p, h in risk_active)
        rows_data.append(("⚡", "Hidden Risks", "#ef4444", "High Alert",
                          f"Multiple malefics in crisis houses — {detail}"))
    elif len(risk_active) == 1:
        p, h = risk_active[0]
        note = "debts/enemies active" if h == 6 else "sudden reversals" if h == 8 else "isolation/loss risk"
        rows_data.append(("⚡", "Hidden Risks", "#eab308", "Caution",
                          f"{p} in H{h} — {note}"))
    else:
        rows_data.append(("⚡", "Hidden Risks", "#22c55e", "Low Risk",
                          "No malefics in H6/H8/H12 — clean operational environment"))

    # ── Build HTML ─────────────────────────────────────────────────────────
    def _dot(color: str) -> str:
        return (
            f'<span style="display:inline-block;width:9px;height:9px;'
            f'border-radius:50%;background:{color};margin-right:7px;'
            f'vertical-align:middle;flex-shrink:0"></span>'
        )

    tbody = ""
    for i, (icon, cat, dot_color, status, why) in enumerate(rows_data):
        bg_row = "#ffffff" if i % 2 == 0 else "#f8fafc"
        # Map dot color to status-badge variant class + inline fallback colors
        if dot_color == "#22c55e":
            badge_cls, sbg, sfg = "status-badge status-badge-green",  "#dcfce7", "#166534"
        elif dot_color == "#ef4444":
            badge_cls, sbg, sfg = "status-badge status-badge-red",    "#fee2e2", "#991b1b"
        elif dot_color == "#eab308":
            badge_cls, sbg, sfg = "status-badge status-badge-yellow", "#fef9c3", "#854d0e"
        else:
            badge_cls, sbg, sfg = "status-badge status-badge-grey",   "#f1f5f9", "#475569"

        # Inline style as fallback for when global CSS classes aren't loaded yet
        status_badge = (
            f'<span class="{badge_cls}" '
            f'style="background:{sbg};color:{sfg} !important;'
            f'border-radius:9999px;padding:3px 10px;font-size:.73rem;font-weight:700">'
            f'{status}</span>'
        )
        tbody += (
            f'<tr>'
            f'<td style="background:{bg_row};color:#1e293b !important;padding:10px 12px;'
            f'font-weight:700;font-size:.83rem;border-bottom:1px solid #e2e8f0;'
            f'white-space:nowrap">{icon} {cat}</td>'
            f'<td style="background:{bg_row};padding:10px 12px;border-bottom:1px solid #e2e8f0">'
            f'<div style="display:flex;align-items:center">{_dot(dot_color)}{status_badge}</div>'
            f'</td>'
            f'<td style="background:{bg_row};color:#475569 !important;padding:10px 12px;'
            f'font-size:.78rem;line-height:1.5;border-bottom:1px solid #e2e8f0">{why}</td>'
            f'</tr>'
        )

    return f"""{_CSS}
<div class="ma-root" style="padding:4px">
  <div style="background:#ffffff;border-radius:12px;
              box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden">
    <div style="background:linear-gradient(90deg,#0f172a,#1e3a5f);padding:11px 16px">
      <span style="color:#fbbf24 !important;font-weight:700;font-size:.9rem">
        ⚡ Quick Summary Pulse
      </span>
      <span style="color:#94a3b8 !important;font-size:.72rem;margin-left:8px">— {country}</span>
    </div>
    <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table style="width:100%;min-width:420px;border-collapse:collapse;font-family:'Segoe UI',system-ui,sans-serif">
      <thead>
        <tr>
          <th style="background:#f8fafc;color:#64748b !important;padding:7px 12px;
                     text-align:left;font-size:.72rem;font-weight:700;
                     border-bottom:2px solid #e2e8f0;width:26%">CATEGORY</th>
          <th style="background:#f8fafc;color:#64748b !important;padding:7px 12px;
                     text-align:left;font-size:.72rem;font-weight:700;
                     border-bottom:2px solid #e2e8f0;width:26%">STATUS</th>
          <th style="background:#f8fafc;color:#64748b !important;padding:7px 12px;
                     text-align:left;font-size:.72rem;font-weight:700;
                     border-bottom:2px solid #e2e8f0">WHY</th>
        </tr>
      </thead>
      <tbody>{tbody}</tbody>
    </table>
    </div>
  </div>
</div>"""


def visual_astro_charts(dt_input, country):
    """Tab 5: South Indian natal + transit charts + daily pulse."""
    dt           = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    lagna_sign   = get_lagna_sign(country)
    natal_data   = get_natal_chart(country)
    event_label  = natal_data.get("_event", "")
    dt_str       = dt.strftime("%d %b %Y %H:%M UTC")

    # Slim down natal_data to planet-only entries for render_south_indian_html
    natal_planet_data = {p: natal_data[p] for p in VEDIC_PLANETS
                         if p in natal_data and isinstance(natal_data[p], dict)}

    natal_tbl = render_south_indian_html(
        natal_planet_data, lagna_sign,
        chart_title=f"🏛️ {country}", chart_subtitle="Natal Chart",
    )
    transit_tbl = render_south_indian_html(
        transit_data, lagna_sign,
        chart_title=f"🌍 {country}", chart_subtitle="Live Transits",
        natal_planet_data=natal_planet_data,
    )
    legend = _render_chart_legend()

    house_pos     = get_house_positions(transit_data, country)
    pulse_html    = _render_daily_pulse(house_pos, transit_data, country)
    qpulse_html   = _render_quick_pulse(house_pos, transit_data, country)

    natal_html = f"""{_CSS}
<div class="ma-root" style="max-width:100%;overflow:hidden">
  <div style="font-weight:700;font-size:.88rem;color:#1e293b;margin-bottom:6px">
    📜 Natal Chart — {country}
    <span style="font-size:.7rem;font-weight:400;color:#64748b;margin-left:6px">{event_label}</span>
  </div>
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <div style="min-width:260px">{natal_tbl}</div>
  </div>
</div>"""

    transit_html = f"""{_CSS}
<div class="ma-root" style="max-width:100%;overflow:hidden">
  <div style="font-weight:700;font-size:.88rem;color:#1e293b;margin-bottom:6px">
    🌐 Transit Chart — {country}
    <span style="font-size:.7rem;font-weight:400;color:#64748b;margin-left:6px">{dt_str}</span>
  </div>
  <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
    <div style="min-width:260px">{transit_tbl}</div>
  </div>
  {legend}
</div>"""

    return natal_html, transit_html, qpulse_html, pulse_html


# ─────────────────────────────────────────────────────────────────────────────
# Gradio UI
# ─────────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="Mundane Astrology Dashboard") as demo:

    gr.Markdown(
        "# 🪐 Mundane Astrology Dashboard\n"
        "**Vedic Gocharam (Transit) Analysis for Nations** — "
        "India · USA · China · EU"
    )

    # Shared inputs
    with gr.Row():
        date_input = gr.DateTime(
            label="Transit Date & Time (UTC)",
            value=datetime.datetime.utcnow(),
            include_time=True,
            type="datetime",
        )
        calc_btn = gr.Button("🔭 Calculate Transits", variant="primary", scale=0)

    with gr.Tabs():

        # ── Tab 1: Global Heatmap ──────────────────────────────────────────
        with gr.Tab("🌍 Global Heatmap"):
            gr.Markdown(
                "Icon-coded planetary status for all nations. "
                "💰 Economy · 🛡️ Security · 🏛️ Governance · 🚀 Tech"
            )
            heatmap_html_out = gr.HTML()
            with gr.Accordion("📡 Technical Astronomical Data", open=False):
                raw_ephe_out = gr.DataFrame(
                    label="Raw Swiss Ephemeris",
                    interactive=False,
                )

        # ── Tab 2: Regional Analysis ───────────────────────────────────────
        with gr.Tab("🔍 Regional Analysis"):
            country_dd = gr.Dropdown(
                choices=COUNTRIES, value="India", label="Select Country"
            )
            gauge_out    = gr.HTML(label="Risk vs Reward Gauge")
            pulse_out    = gr.HTML(label="Categorical Pulse")
            analysis_out = gr.HTML(label="Bright Side vs Strategic Risks")
            with gr.Accordion("📜 Natal Chart vs Current Transits", open=False):
                natal_out = gr.HTML()

        # ── Tab 3: Mundane News Alerts ─────────────────────────────────────
        with gr.Tab("📰 Mundane News Alerts"):
            gr.Markdown(
                "AI-generated interpretation of current world events "
                "through the Gocharam lens."
            )
            country_dd2   = gr.Dropdown(
                choices=COUNTRIES, value="India", label="Select Country"
            )
            mundane_html_out = gr.HTML()
            with gr.Accordion("📡 Technical Astronomical Data", open=False):
                raw_ephe_out2 = gr.DataFrame(
                    label="Raw Swiss Ephemeris",
                    interactive=False,
                )

        # ── Tab 4: Weekly Watch ────────────────────────────────────────────
        with gr.Tab("🌟 Weekly Watch"):
            gr.Markdown(
                "Retrograde tracker · Planet ingress countdown · "
                "Lunation & eclipse alerts · AI weekly briefing"
            )
            retro_html_out    = gr.HTML()
            ingress_html_out  = gr.HTML()
            lunation_html_out = gr.HTML()
            watch_html_out    = gr.HTML()

        # ── Tab 5: Visual Astro Charts ─────────────────────────────────────
        with gr.Tab("🗺️ Visual Astro Charts"):
            gr.Markdown(
                "South Indian square charts + financial-dashboard pulse. "
                "⭐ Gold border = Natal+Transit conjunction. "
                "🔴 Diagonal slash = Country Lagna (ASC)."
            )
            country_dd5 = gr.Dropdown(
                choices=COUNTRIES, value="India", label="Select Country"
            )
            # Row 1: both charts side by side
            with gr.Row():
                natal_chart_out   = gr.HTML(label="📜 National Natal Chart (Fixed)")
                transit_chart_out = gr.HTML(label="🌐 Live Transit Chart (Gocharam)")
            # Row 2: transit chart beside Quick Summary Pulse
            with gr.Row():
                with gr.Column(scale=3):
                    quick_pulse_out = gr.HTML(label="⚡ Quick Summary Pulse")
                with gr.Column(scale=2):
                    daily_pulse_out = gr.HTML(label="📊 Daily Pulse")

    # ── Event wiring ──────────────────────────────────────────────────────
    calc_btn.click(
        fn=run_calculations,
        inputs=[date_input],
        outputs=[heatmap_html_out, raw_ephe_out],
    )
    calc_btn.click(
        fn=regional_analysis,
        inputs=[date_input, country_dd],
        outputs=[gauge_out, pulse_out, analysis_out, natal_out],
    )
    calc_btn.click(
        fn=mundane_analysis,
        inputs=[date_input, country_dd2],
        outputs=[mundane_html_out, raw_ephe_out2],
    )
    calc_btn.click(
        fn=weekly_watch,
        inputs=[date_input],
        outputs=[retro_html_out, ingress_html_out, lunation_html_out, watch_html_out],
    )
    country_dd.change(
        fn=regional_analysis,
        inputs=[date_input, country_dd],
        outputs=[gauge_out, pulse_out, analysis_out, natal_out],
    )
    country_dd2.change(
        fn=mundane_analysis,
        inputs=[date_input, country_dd2],
        outputs=[mundane_html_out, raw_ephe_out2],
    )
    calc_btn.click(
        fn=visual_astro_charts,
        inputs=[date_input, country_dd5],
        outputs=[natal_chart_out, transit_chart_out, quick_pulse_out, daily_pulse_out],
    )
    country_dd5.change(
        fn=visual_astro_charts,
        inputs=[date_input, country_dd5],
        outputs=[natal_chart_out, transit_chart_out, quick_pulse_out, daily_pulse_out],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(),
        css=_GRADIO_CSS,
    )
