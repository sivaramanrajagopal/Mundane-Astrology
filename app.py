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

from dasha_logic import (
    get_country_dasha, get_dasha_risk_level,
    DASHA_FOCUS, BHUKTI_TRIGGER, get_relationship,
    PLANET_FRIENDSHIPS, DASA_DURATIONS,
)
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
from natal_protection import (
    AstrologyProtection,
    geocode_place,
    NATAL_PLANETS,
    ALL_DISPLAY_PLANETS,
    calculate_vimshottari_dasha,
    get_current_dasha_bhukti,
    scan_transit_affliction,
    scan_pushkara_transit,
    VIMSHOTTARI_YEARS,
    check_pushkara,
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
COUNTRIES      = list(COUNTRY_LAGNAS.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS injected via gr.Blocks(css=...) — fixes Gradio chrome visibility
# ─────────────────────────────────────────────────────────────────────────────
_GRADIO_CSS = """
/* ── Dark app shell + prevent horizontal page scroll ────────────────── */
body, html { background: #0b0f19 !important; overflow-x: hidden; max-width: 100vw; }
.gradio-container {
  background-color: #0b0f19 !important;
  color: #f8fafc !important;
  overflow-x: hidden !important;
  max-width: 100% !important;
}

/* ── Tab navigation — always scrollable so 7+ tabs never clip ────────── */
.tab-nav, div[role="tablist"] {
  overflow-x: auto !important;
  -webkit-overflow-scrolling: touch;
  flex-wrap: nowrap !important;
  scrollbar-width: none;
}
.tab-nav::-webkit-scrollbar, div[role="tablist"]::-webkit-scrollbar { display: none; }
.tab-nav button, div[role="tablist"] button {
  color: #94a3b8 !important;
  background: transparent !important;
  white-space: nowrap;
  flex-shrink: 0;
}
.tab-nav button.selected, div[role="tablist"] button[aria-selected="true"] {
  color: #f8fafc !important;
  border-bottom: 2px solid #7c3aed !important;
}

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

/* ── Mobile breakpoint ───────────────────────────────────────────────── */
@media (max-width: 768px) {
  /* Scrollable tab nav */
  .tab-nav {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    flex-wrap: nowrap !important;
    scrollbar-width: none;
  }
  .tab-nav::-webkit-scrollbar { display: none; }
  .tab-nav button {
    min-width: 60px !important;
    font-size: .68rem !important;
    white-space: nowrap;
    padding: 6px 8px !important;
  }

  /* Stack the top date+button inputs row */
  .top-inputs-row {
    flex-wrap: wrap !important;
    gap: 8px !important;
  }
  .top-inputs-row > * {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }

  /* Stack the two SI charts (Tab 5, Row 1) */
  .charts-row {
    flex-wrap: wrap !important;
  }
  .charts-row > * {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }

  /* Stack the Quick Pulse + Daily Pulse row (Tab 5, Row 2) */
  .pulse-row {
    flex-wrap: wrap !important;
  }
  .pulse-row > * {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }

  /* Touch-friendly tap targets */
  button { min-height: 44px; }
  select, input { min-height: 40px; font-size: 16px !important; }

  /* Full-width primary button */
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
           border-radius:10px;padding:10px;line-height:1.5;
           max-width:100%;overflow-x:hidden;word-break:break-word}
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
  .gauge-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;color:#1e293b !important;flex-wrap:wrap}
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
    .ma-root{padding:6px}
    /* Cards full-width on mobile */
    .split-card{min-width:unset !important;width:100% !important;flex:1 1 100% !important}
    .ingress-card{min-width:unset !important;width:100% !important}
    .luna-card{min-width:unset !important;width:100% !important}
    /* Stack flex grids to single column */
    .ingress-grid{flex-direction:column !important}
    .luna-list{flex-direction:column !important}
    .split-wrap{flex-direction:column !important}
    /* Smaller table font */
    .pulse-table,.heatmap-tbl,.natal-tbl,.dp-tbl{font-size:.76rem}
    .pulse-table th,.heatmap-tbl th,.natal-tbl th,.dp-tbl th{padding:6px 7px}
    .pulse-table td,.heatmap-tbl td,.natal-tbl td,.dp-tbl td{padding:6px 7px}
    /* Retro banner wraps cleanly */
    .retro-banner{flex-wrap:wrap;gap:6px;padding:8px 10px;font-size:.78rem}
    /* Watch card */
    .watch-card{padding:12px 14px}
    .watch-card li{font-size:.82rem}
    /* Gauge */
    .gauge-track{height:18px}
    .gauge-labels{font-size:.63rem}
    /* Ingress/lunation card padding */
    .ingress-card{padding:8px 10px}
    .luna-card{padding:8px 10px}
    /* Analysis accordion body padding */
    details.ma-accordion .acc-body{padding:10px 12px}
  }
  /* ── Compact SI chart on very small screens ──────────────────────── */
  @media(max-width:600px){
    .si-cell{min-height:44px;padding:2px 3px}
    .p-badge{font-size:.58rem;padding:1px 4px}
    .si-sign{font-size:.48rem}
    .si-asc{font-size:.5rem;padding:1px 3px}
    .si-centre{padding:4px}
  }
  /* ── Extra-small screens (≤380px) ───────────────────────────────── */
  @media(max-width:380px){
    .ma-root{padding:4px;border-radius:6px}
    .ma-card{padding:10px 12px}
    .watch-card{padding:10px 12px}
    .p-badge{font-size:.55rem;padding:1px 3px}
  }
  /* ── Dasha Timeline tab styles ───────────────────────────────────── */
  .dasha-strip{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0}
  .dasha-card{flex:1;min-width:200px;border-radius:14px;padding:16px 18px;
              box-shadow:0 2px 10px rgba(0,0,0,.10);color:#1e293b !important}
  .dasha-maha{background:linear-gradient(135deg,#1e293b,#1e3a5f);
              border:1px solid #334155}
  .dasha-bhuk{background:#f8fafc;border:1px solid #e2e8f0}
  .dasha-planet-lbl{font-size:.7rem;font-weight:600;color:#94a3b8;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
  .dasha-planet-name{font-size:1.55rem;font-weight:800;letter-spacing:-.02em;margin-bottom:4px}
  .dasha-maha .dasha-planet-name{color:#fbbf24 !important}
  .dasha-bhuk .dasha-planet-name{color:#1e293b !important}
  .dasha-focus{font-size:.77rem;line-height:1.5;margin-bottom:8px}
  .dasha-maha .dasha-focus{color:#94a3b8 !important}
  .dasha-bhuk .dasha-focus{color:#475569 !important}
  .dasha-meta{font-size:.7rem;color:#64748b !important}
  .dasha-maha .dasha-meta{color:#64748b !important}
  .dasha-remaining{display:inline-block;margin-top:6px;border-radius:99px;
                   padding:2px 10px;font-size:.72rem;font-weight:700}
  .dasha-maha .dasha-remaining{background:#334155;color:#fbbf24 !important}
  .dasha-bhuk .dasha-remaining{background:#dbeafe;color:#1e40af !important}
  /* Relationship badge */
  .rel-strip{text-align:center;margin:6px 0 12px;font-size:.85rem;font-weight:700}
  .rel-friend {color:#166534 !important;background:#dcfce7;
               border-radius:99px;padding:4px 14px;display:inline-block}
  .rel-enemy  {color:#991b1b !important;background:#fee2e2;
               border-radius:99px;padding:4px 14px;display:inline-block}
  .rel-neutral{color:#854d0e !important;background:#fef9c3;
               border-radius:99px;padding:4px 14px;display:inline-block}
  /* Double-trigger alert */
  .dt-alert{border-radius:12px;padding:14px 18px;margin:10px 0;font-size:.87rem}
  .dt-critical{background:#fff1f2;border:2px solid #ef4444}
  .dt-mixed   {background:#fefce8;border:1px solid #eab308}
  .dt-aligned {background:#f0fdf4;border:1px solid #22c55e}
  .dt-neutral {background:#f8fafc;border:1px solid #e2e8f0}
  .dt-title{font-weight:800;font-size:.95rem;margin-bottom:6px}
  .dt-critical .dt-title{color:#b91c1c !important}
  .dt-mixed    .dt-title{color:#92400e !important}
  .dt-aligned  .dt-title{color:#166534 !important}
  .dt-neutral  .dt-title{color:#1e293b !important}
  /* Upcoming bhukti pills */
  .bh-upcoming{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
  .bh-pill{flex:1;min-width:120px;background:#f8fafc;border:1px solid #e2e8f0;
           border-radius:10px;padding:8px 12px;text-align:center;
           color:#1e293b !important}
  .bh-pill-planet{font-weight:700;font-size:.85rem;color:#1e293b !important}
  .bh-pill-date  {font-size:.68rem;color:#64748b !important;margin-top:2px}
  /* Full dasha table */
  .dasha-tbl{width:100%;border-collapse:collapse;font-size:.83rem;color:#1e293b}
  .dasha-tbl th{background:#1e293b;color:#f1f5f9 !important;padding:8px 12px;
                text-align:left;font-weight:600}
  .dasha-tbl td{padding:8px 12px;border-bottom:1px solid #e2e8f0;
                color:#1e293b !important;background:#ffffff}
  .dasha-tbl tr.dt-current td{background:#fef9c3 !important;font-weight:700}
  .dasha-tbl tr:nth-child(even) td{background:#f8fafc}
  .dasha-tbl tr.dt-current:nth-child(even) td{background:#fef9c3 !important}
  /* D/B marker on chart badges */
  .db-marker{font-size:.55rem;font-weight:800;vertical-align:super;
             margin-left:1px;letter-spacing:0}
  /* Mobile: dasha tab */
  @media(max-width:768px){
    .dasha-card{min-width:unset !important;width:100% !important;padding:12px 14px}
    .dasha-planet-name{font-size:1.25rem}
    .bh-pill{min-width:unset !important;width:100% !important}
    .dasha-tbl{font-size:.76rem}
    .dasha-tbl th,.dasha-tbl td{padding:6px 8px}
    .dt-alert{padding:10px 12px}
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
  <div class="split-wrap">
    <div class="split-card split-green" style="{CARD_BASE};background:#f0fdf4 !important;border:1px solid #86efac">
      <h4 {H4}>🌟 The Bright Side</h4>
      <ul {UL}>{bright_li}</ul>
    </div>
    <div class="split-card split-red" style="{CARD_BASE};background:#fff1f2 !important;border:1px solid #fca5a5">
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
    dasha_planet: str = "",
    bhukti_planet: str = "",
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
        """Fully inline-styled pill badge — immune to Gradio theme overrides.
        Shows D marker for Mahadasha lord, B marker for Bhukti lord."""
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
        # D/B superscript markers for Dasha/Bhukti lords
        db_mark = ""
        if planet == dasha_planet:
            db_mark += '<sup style="font-size:.5rem;font-weight:900;color:#7c3aed !important;margin-left:1px">D</sup>'
        if planet == bhukti_planet:
            db_mark += '<sup style="font-size:.5rem;font-weight:900;color:#dc2626 !important;margin-left:1px">B</sup>'
        return (
            f'<span style="display:inline-block;border-radius:99px;padding:1px 7px;'
            f'font-size:.7rem;font-weight:700;margin:1px 1px 2px;'
            f'background:{bg};color:{fg} !important;'
            f'line-height:1.5;white-space:nowrap">{short}{mark}{db_mark}</span>'
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
                              natal_planet_data: dict = None,
                              dasha_planet: str = "",
                              bhukti_planet: str = "") -> str:
    """
    Public API: render South Indian chart from full planet_data dicts.

    planet_data       : {planet: {sign_index, retrograde, ...}}
    lagna_sign        : sign name string e.g. "Taurus"
    natal_planet_data : if provided, conjunctions (transit on natal sign) are highlighted
    dasha_planet      : current Mahadasha lord name — shown with ᴰ superscript
    bhukti_planet     : current Bhukti lord name — shown with ᴮ superscript
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
                                   retro_set, natal_map, dasha_planet, bhukti_planet)


def _render_chart_legend() -> str:
    def _pill(bg, border, text):
        return (f'<span style="background:{bg} !important;color:#1e293b !important;'
                f'padding:1px 6px;border-radius:4px;border:1px solid {border}">{text}</span>')
    return (
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;font-size:.72rem;'
        'color:#1e293b !important;align-items:center;background:#f8fafc !important;'
        'border-radius:8px;padding:8px 10px;overflow-x:auto;-webkit-overflow-scrolling:touch">'
        '<strong style="color:#1e293b !important">Legend:</strong>'
        f'<span style="color:#1e293b !important">🟢 {_pill("#f0fdf4","#86efac","Benefic — Growth/Economy")}</span>'
        f'<span style="color:#1e293b !important">🔴 {_pill("#fff1f2","#fca5a5","Malefic — Risk/Conflict")}</span>'
        f'<span style="color:#1e293b !important">🟡 {_pill("#fefce8","#fde047","Mixed Influence")}</span>'
        '<span style="color:#1e293b !important">⭐ '
        '<span style="border:3px solid #f59e0b;padding:1px 6px;border-radius:4px;'
        'color:#1e293b !important">Natal + Transit Conjunction</span></span>'
        '<span style="color:#64748b !important">ASC = Country Lagna &nbsp;|&nbsp; ℞ = Retrograde</span>'
        '<span style="color:#64748b !important">'
        '<sup style="color:#7c3aed !important;font-weight:900">D</sup> = Mahadasha Lord &nbsp;|&nbsp;'
        '<sup style="color:#dc2626 !important;font-weight:900">B</sup> = Bhukti Lord'
        '</span>'
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
# Dasha Timeline renderers
# ─────────────────────────────────────────────────────────────────────────────
_PLANET_COLOR_DASHA = {
    "Sun": "#d97706", "Moon": "#2563eb", "Mercury": "#7c3aed", "Venus": "#16a34a",
    "Mars": "#dc2626", "Jupiter": "#15803d", "Saturn": "#92400e",
    "Rahu": "#991b1b", "Ketu": "#9f1239",
}
_MALEFIC_SET  = {"Mars", "Saturn", "Rahu", "Ketu"}
_BENEFIC_SET  = {"Jupiter", "Venus"}


def _dasha_planet_emoji(planet: str) -> str:
    return {
        "Sun":"☀️","Moon":"🌙","Mercury":"☿","Venus":"♀","Mars":"♂",
        "Jupiter":"♃","Saturn":"♄","Rahu":"☊","Ketu":"☋",
    }.get(planet, "⭐")


def _render_dasha_timeline_html(dasha_info: dict, house_pos: dict,
                                 transit_data: dict) -> str:
    """Full Dasha & Bhukti Timeline tab HTML."""
    if not dasha_info:
        return f'{_CSS}<div class="ma-root"><p style="color:#64748b">No dasha data available for this country.</p></div>'

    country  = dasha_info["country"]
    notes    = dasha_info["notes"]
    nak      = dasha_info["nakshatra"]
    pada     = dasha_info["pada"]
    md       = dasha_info["mahadasha"]
    bh       = dasha_info["bhukti"]
    rel      = dasha_info["relationship"]
    upcoming = dasha_info.get("upcoming_bhuktis", [])
    nxt_d    = dasha_info.get("next_dashas", [])

    # ── Moon nakshatra header ────────────────────────────────────────────────
    header_html = f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
            padding:10px 14px;margin-bottom:10px;color:#1e293b !important">
  <span style="font-weight:700;font-size:.92rem;color:#1e293b !important">
    🌙 Natal Moon: <strong style="color:#7c3aed !important">{nak}</strong> Pada {pada}
  </span>
  <span style="margin-left:10px;font-size:.75rem;color:#64748b !important">{notes}</span>
</div>"""

    # ── Mahadasha progress bar ───────────────────────────────────────────────
    md_elapsed = round(md["years"] - float(md["remaining"]), 2)
    md_pct     = max(2, min(100, int(md_elapsed / md["years"] * 100))) if md["years"] else 0

    # ── Bhukti progress bar ───────────────────────────────────────────────────
    try:
        import datetime as _dt_mod
        _bhs = _dt_mod.datetime.strptime(bh["start"].strip(), "%b %Y")
        _bhe = _dt_mod.datetime.strptime(bh["end"].strip(),   "%b %Y")
        bh_total_m = (_bhe.year - _bhs.year) * 12 + (_bhe.month - _bhs.month)
    except Exception:
        bh_total_m = 0
    bh_elapsed_m = max(0, bh_total_m - float(bh["remaining_months"]))
    bh_pct = max(2, min(100, int(bh_elapsed_m / bh_total_m * 100))) if bh_total_m else 0

    def _prog_bar(pct: int, filled_color: str, track_color: str = "#e2e8f0") -> str:
        """Inline HTML progress bar — no CSS class dependency."""
        return (
            f'<div style="margin-top:10px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:.68rem;color:#64748b !important;margin-bottom:3px">'
            f'<span style="color:#64748b !important">Elapsed</span>'
            f'<span style="color:#64748b !important">{pct}%</span>'
            f'</div>'
            f'<div style="background:{track_color};border-radius:99px;height:8px;overflow:hidden">'
            f'<div style="background:{filled_color};width:{pct}%;height:100%;'
            f'border-radius:99px;transition:width .4s ease"></div>'
            f'</div>'
            f'</div>'
        )

    md_col  = _PLANET_COLOR_DASHA.get(md["planet"], "#475569")
    md_emj  = _dasha_planet_emoji(md["planet"])
    md_card = f"""
<div class="dasha-card dasha-maha">
  <div class="dasha-planet-lbl" style="color:#94a3b8 !important">Mahadasha (Major Period)</div>
  <div class="dasha-planet-name" style="color:{md_col} !important">{md_emj} {md["planet"]}</div>
  <div class="dasha-focus" style="color:#94a3b8 !important">{md["focus"]}</div>
  <div class="dasha-meta" style="color:#64748b !important">
    {md["start"]} → {md["end"]} &nbsp;·&nbsp; {md["years"]} yrs total
  </div>
  {_prog_bar(md_pct, md_col, "#1e293b")}
  <div class="dasha-remaining" style="background:#334155;color:#fbbf24 !important">
    ⏳ {md["remaining"]} yrs remaining
  </div>
</div>"""

    # ── Bhukti card ──────────────────────────────────────────────────────────
    bh_col  = _PLANET_COLOR_DASHA.get(bh["planet"], "#475569")
    bh_emj  = _dasha_planet_emoji(bh["planet"])
    bh_card = f"""
<div class="dasha-card dasha-bhuk">
  <div class="dasha-planet-lbl" style="color:#64748b !important">Bhukti (Sub-Period Trigger)</div>
  <div class="dasha-planet-name" style="color:{bh_col} !important">{bh_emj} {bh["planet"]}</div>
  <div class="dasha-focus" style="color:#475569 !important">{bh["trigger"]}</div>
  <div class="dasha-meta" style="color:#64748b !important">
    {bh["start"]} → {bh["end"]}
  </div>
  {_prog_bar(bh_pct, bh_col, "#dbeafe")}
  <div class="dasha-remaining" style="background:#dbeafe;color:#1e40af !important">
    ⏳ {bh["remaining_months"]} months remaining
  </div>
</div>"""

    dasha_strip = f'<div class="dasha-strip">{md_card}{bh_card}</div>'

    # ── Relationship badge ───────────────────────────────────────────────────
    if rel == "Same":
        rel_cls, rel_icon = "rel-friend",  f"⚡ Intensified — {md['planet']}–{md['planet']} Period"
        rel_note = f"Same planet rules both Mahadasha and Bhukti — its qualities are magnified and operate without dilution. Strong single-planet focus."
    elif rel == "Friend":
        rel_cls, rel_icon = "rel-friend",  "🤝 Harmonious Period"
        rel_note = f"{md['planet']} and {bh['planet']} are natural friends — their energies amplify each other positively."
    elif rel == "Enemy":
        rel_cls, rel_icon = "rel-enemy",   "⚔️ Tense Period"
        rel_note = f"{md['planet']} and {bh['planet']} are natural enemies — conflicting impulses, internal friction."
    else:
        rel_cls, rel_icon = "rel-neutral", "⚖️ Neutral Period"
        rel_note = f"{md['planet']} and {bh['planet']} are neutral — outcomes depend on transits and house lordships."

    rel_html = f"""
<div class="rel-strip">
  <span class="{rel_cls}">{rel_icon}</span>
  <div style="font-size:.78rem;font-weight:400;color:#475569 !important;margin-top:6px;text-align:left;
              background:#f8fafc;border-radius:8px;padding:8px 12px">{rel_note}</div>
</div>"""

    # ── Double Trigger alert ─────────────────────────────────────────────────
    dt_html = _render_double_trigger_html(dasha_info, house_pos, transit_data)

    # ── Upcoming bhuktis ─────────────────────────────────────────────────────
    up_pills = ""
    for ub in upcoming:
        c = _PLANET_COLOR_DASHA.get(ub["planet"], "#475569")
        e = _dasha_planet_emoji(ub["planet"])
        up_pills += f"""
<div class="bh-pill">
  <div class="bh-pill-planet" style="color:{c} !important">{e} {ub["planet"]}</div>
  <div class="bh-pill-date">{ub["start"]}</div>
  <div class="bh-pill-date">{ub["end"]}</div>
</div>"""

    upcoming_html = f"""
<div style="margin-top:12px">
  <div style="font-weight:700;font-size:.83rem;color:#475569 !important;
              margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em">
    ▶ Next Bhuktis
  </div>
  <div class="bh-upcoming">{up_pills or '<span style="color:#94a3b8;font-size:.82rem">End of dasha cycle</span>'}</div>
</div>"""

    # ── Full dasha timeline table ─────────────────────────────────────────────
    all_dashas_rows = ""
    # Build complete list: current + next
    cur_row = f"""<tr class="dt-current">
  <td style="background:#fef9c3 !important;font-weight:700;color:#1e293b !important">
    {_dasha_planet_emoji(md["planet"])} {md["planet"]} ← NOW
  </td>
  <td style="background:#fef9c3 !important;color:#1e293b !important">{md["start"]}</td>
  <td style="background:#fef9c3 !important;color:#1e293b !important">{md["end"]}</td>
  <td style="background:#fef9c3 !important;color:#1e293b !important">{md["years"]} yrs</td>
  <td style="background:#fef9c3 !important;color:#1e293b !important;font-size:.75rem">
    {md["focus"]}</td>
</tr>"""
    for nd in nxt_d:
        c = _PLANET_COLOR_DASHA.get(nd["planet"], "#475569")
        e = _dasha_planet_emoji(nd["planet"])
        f_txt = DASHA_FOCUS.get(nd["planet"], "")
        all_dashas_rows += f"""<tr>
  <td style="color:#1e293b !important;font-weight:600">
    <span style="color:{c} !important">{e}</span> {nd["planet"]}
  </td>
  <td style="color:#475569 !important">{nd["start"]}</td>
  <td style="color:#475569 !important">{nd["end"]}</td>
  <td style="color:#475569 !important">{nd["years"]} yrs</td>
  <td style="color:#475569 !important;font-size:.75rem">{f_txt}</td>
</tr>"""

    full_table = f"""
<details class="ma-accordion" style="margin-top:14px">
  <summary style="background:#f8fafc !important;color:#1e293b !important">
    📅 Full Dasha Timeline — click to expand
  </summary>
  <div class="acc-body" style="background:#ffffff !important;padding:14px 16px;overflow-x:auto;-webkit-overflow-scrolling:touch">
    <table class="dasha-tbl" style="min-width:480px">
      <thead>
        <tr>
          <th>Planet</th><th>Starts</th><th>Ends</th><th>Duration</th><th>Focus Area</th>
        </tr>
      </thead>
      <tbody>
        {cur_row}
        {all_dashas_rows}
      </tbody>
    </table>
    <div style="font-size:.7rem;color:#64748b;margin-top:6px">
      🟡 Highlighted row = current Mahadasha
    </div>
  </div>
</details>"""

    return f"""{_CSS}
<div class="ma-root">
  {header_html}
  {dasha_strip}
  {rel_html}
  {dt_html}
  {upcoming_html}
  {full_table}
</div>"""


def _render_double_trigger_html(dasha_info: dict, house_pos: dict,
                                 transit_data: dict) -> str:
    """
    Double Trigger: cross-reference Dasha risk with transit risk.
    CRITICAL ALERT  — both dasha + transit = high risk
    Mixed Signals   — one positive, one negative
    Aligned Opportunity — both positive
    Standard Watch  — neutral
    """
    if not dasha_info:
        return ""

    md_planet = dasha_info["mahadasha"]["planet"]
    bh_planet = dasha_info["bhukti"]["planet"]
    dasha_risk = get_dasha_risk_level(dasha_info)

    # Transit risk: count malefics in crisis houses (H6/H8/H12) + H10 Mars/Rahu
    crisis_houses = {6, 8, 12}
    crisis_count = sum(
        1 for p, h in house_pos.items()
        if p in _MALEFIC_SET and h in crisis_houses
    )
    mars_h = house_pos.get("Mars", 0)
    rahu_h = house_pos.get("Rahu", 0)
    h10_tension = (mars_h == 10 and rahu_h == 10)

    # Overall transit risk level
    if crisis_count >= 2 or h10_tension:
        transit_risk = "high"
    elif crisis_count == 1:
        transit_risk = "medium"
    else:
        transit_risk = "low"

    # Determine combined alert
    if dasha_risk == "high" and transit_risk == "high":
        cls, icon, title = "dt-critical", "🚨", "CRITICAL ALERT — Dasha & Transit Aligned on Risk"
        body = (
            f"The {md_planet} Mahadasha (focus: foreign affairs/disruption) "
            f"and {bh_planet} Bhukti (trigger: {BHUKTI_TRIGGER.get(bh_planet,'')}) "
            f"are operating together with high-stress transits. "
            f"This is a compounded risk window — both the background Dasha cycle "
            f"and immediate transit positions point to turbulence."
        )
    elif dasha_risk == "high" and transit_risk == "medium":
        cls, icon, title = "dt-critical", "⚠️", "ELEVATED ALERT — Dasha Amplifies Transit Stress"
        body = (
            f"The {md_planet}–{bh_planet} dasha combination is inherently tense "
            f"and is now activating transit stress patterns. Monitor closely."
        )
    elif dasha_risk == "low" and transit_risk == "high":
        cls, icon, title = "dt-mixed", "⚖️", "MIXED SIGNALS — Transits Conflict with Dasha Ease"
        body = (
            f"Current transits are under significant stress, but the "
            f"{md_planet} Mahadasha provides a stabilizing background influence. "
            f"Short-term volatility is possible; medium-term outlook stays manageable."
        )
    elif dasha_risk == "low" and transit_risk == "low":
        cls, icon, title = "dt-aligned", "🌟", "ALIGNED OPPORTUNITY — Dasha & Transit Both Positive"
        body = (
            f"The {md_planet} Mahadasha (focus: {DASHA_FOCUS.get(md_planet,'')}) "
            f"aligns with supportive transit positions. "
            f"This window favours growth, expansion, and policy success."
        )
    else:
        cls, icon, title = "dt-mixed", "⚖️", "MIXED SIGNALS — Monitor Both Dasha and Transit"
        body = (
            f"The {md_planet} Mahadasha and {bh_planet} Bhukti produce a mixed backdrop. "
            f"Some transit positions support growth while others introduce friction. "
            f"Context-dependent outcomes — watch specific house activations."
        )

    # Add specific transit detail
    detail_parts = []
    if h10_tension:
        detail_parts.append("🔴 Mars + Rahu in H10 → covert power struggles")
    if crisis_count >= 2:
        crisis_p = [p for p, h in house_pos.items() if p in _MALEFIC_SET and h in crisis_houses]
        detail_parts.append(f"🔴 {', '.join(crisis_p)} in crisis houses (H6/H8/H12)")
    if mars_h in {1, 7}:
        detail_parts.append(f"⚠️ Mars in H{mars_h} — external aggression / border risk")
    detail_html = (
        "<ul style='margin:8px 0 0;padding-left:16px;color:#1e293b !important;font-size:.8rem'>"
        + "".join(f"<li style='color:#1e293b !important;margin-bottom:3px'>{d}</li>" for d in detail_parts)
        + "</ul>"
    ) if detail_parts else ""

    return f"""
<div class="dt-alert {cls}">
  <div class="dt-title">{icon} {title}</div>
  <div style="font-size:.83rem;color:#1e293b !important;line-height:1.6">{body}</div>
  {detail_html}
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

    dasha_info = get_country_dasha(country, dt)
    llm    = generate_llm_analysis(
        country, transit_data, house_pos, categories, OPENAI_API_KEY,
        dasha_info=dasha_info,
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

    dasha_info  = get_country_dasha(country, dt)
    llm = generate_llm_analysis(
        country, transit_data, house_pos, categories, OPENAI_API_KEY,
        dasha_info=dasha_info,
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
    moon_h  = house_pos.get("Moon", 0)
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

    # ── Public Mood (Moon's house) ─────────────────────────────────────────
    _MOON_MOOD = {
        1:  ("#22c55e", "Nationalist Sentiment",
             "Moon in H1 — strong national identity, public rallying mood"),
        2:  ("#22c55e", "Wealth & Family Focus",
             "Moon in H2 — public attention on savings, food security, family values"),
        3:  ("#94a3b8", "Media Restlessness",
             "Moon in H3 — high social media activity, rumors, short-distance travel up"),
        4:  ("#22c55e", "Domestic Comfort",
             "Moon in H4 — public focus on homeland, agriculture, housing security"),
        5:  ("#22c55e", "Optimistic Speculation",
             "Moon in H5 — creative boom, entertainment surge, risk appetite elevated"),
        6:  ("#eab308", "Health & Labor Unrest",
             "Moon in H6 — public anxiety around health, workers' concerns, service disruptions"),
        7:  ("#94a3b8", "Diplomatic Attention",
             "Moon in H7 — public focus on foreign affairs, partnerships, bilateral events"),
        8:  ("#ef4444", "Public Anxiety",
             "Moon in H8 — sudden mood shifts, hidden fears, anticipation of abrupt change"),
        9:  ("#22c55e", "Faith & Optimism",
             "Moon in H9 — religious/philosophical mood, long-distance travel sentiment up"),
        10: ("#eab308", "Leadership Scrutiny",
             "Moon in H10 — public eye on government, policy debates, leadership accountability"),
        11: ("#22c55e", "Social Solidarity",
             "Moon in H11 — community cohesion, social movements, collective aspirations"),
        12: ("#94a3b8", "Introspective Withdrawal",
             "Moon in H12 — spiritual mood, foreign cultural influence, hidden activities"),
    }
    if moon_h in _MOON_MOOD:
        m_color, m_status, m_why = _MOON_MOOD[moon_h]
    else:
        m_color, m_status, m_why = "#94a3b8", "Undefined", "Moon house not calculable for this chart"
    rows_data.append(("🌙", "Public Mood", m_color, m_status, m_why))

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

    # Get Dasha info for D/B markers on chart badges
    dasha_info   = get_country_dasha(country, dt)
    d_planet     = dasha_info.get("mahadasha", {}).get("planet", "") if dasha_info else ""
    b_planet     = dasha_info.get("bhukti",    {}).get("planet", "") if dasha_info else ""

    # Slim down natal_data to planet-only entries for render_south_indian_html
    natal_planet_data = {p: natal_data[p] for p in VEDIC_PLANETS
                         if p in natal_data and isinstance(natal_data[p], dict)}

    # Natal chart shows D/B markers on the natal planet positions
    natal_tbl = render_south_indian_html(
        natal_planet_data, lagna_sign,
        chart_title=f"🏛️ {country}", chart_subtitle="Natal Chart",
        dasha_planet=d_planet, bhukti_planet=b_planet,
    )
    # Transit chart shows D/B markers on transit planet positions + conjunction gold border
    transit_tbl = render_south_indian_html(
        transit_data, lagna_sign,
        chart_title=f"🌍 {country}", chart_subtitle="Live Transits",
        natal_planet_data=natal_planet_data,
        dasha_planet=d_planet, bhukti_planet=b_planet,
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


def dasha_timeline(dt_input, country):
    """Tab 6: Vimshottari Dasha & Bhukti Timeline."""
    dt           = _to_utc_datetime(dt_input)
    transit_data = get_transit_data(dt)
    house_pos    = get_house_positions(transit_data, country)
    dasha_info   = get_country_dasha(country, dt)
    return _render_dasha_timeline_html(dasha_info, house_pos, transit_data)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 7: Natal Protection — backend functions
# ─────────────────────────────────────────────────────────────────────────────

def resolve_location(place_name: str):
    """Geocode a place name and return (lat, lon, status_markdown)."""
    if not place_name.strip():
        return None, None, "_Enter a place name above._"
    lat, lon, display = geocode_place(place_name.strip())
    if lat is None:
        return None, None, f"⚠️ {display}"
    return round(lat, 5), round(lon, 5), f"📍 **{display}**  \n`{lat:.4f}°, {lon:.4f}°`"


def _protection_score_html(score: int) -> str:
    """Render a colored Protection Score badge."""
    if score <= 4:
        color, label = "#e53e3e", "Low"
    elif score <= 6:
        color, label = "#dd6b20", "Moderate"
    else:
        color, label = "#38a169", "Strong"
    return (
        f'<div style="text-align:center;padding:16px">'
        f'<div style="display:inline-block;background:{color};color:#fff;'
        f'border-radius:12px;padding:12px 32px;font-size:2rem;font-weight:700">'
        f'{score}/10</div>'
        f'<p style="margin:8px 0 0;font-size:1.1rem;color:{color};font-weight:600">'
        f'{label} Protection</p>'
        f'</div>'
    )


_REFERENCE_HTML = """
<details style="margin-top:14px" class="ma-accordion">
<summary style="background:#1a2535;border:1px solid #2d3748;border-radius:8px;
                padding:10px 14px;color:#a0aec0;font-size:0.82rem;cursor:pointer;
                list-style:none;display:flex;justify-content:space-between;align-items:center">
  <span>📖 Reference: Combustion Orbs · Gandanta Zones · Pushkara Navamsa</span>
  <span style="font-size:0.74rem;color:#718096">click to expand</span>
</summary>
<div style="background:#0f172a;border:1px solid #2d3748;border-top:none;
            border-radius:0 0 8px 8px;padding:14px 16px;font-size:0.82rem;color:#cbd5e0">

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">

    <!-- Combustion orbs -->
    <div>
      <div style="font-weight:700;color:#f6ad55;margin-bottom:8px">
        🔥 Combustion Orbs — same sign only
      </div>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="color:#718096;font-size:0.76rem;border-bottom:1px solid #2d3748">
            <th style="text-align:left;padding:2px 6px">Planet</th>
            <th style="padding:2px 6px">Orb</th>
            <th style="padding:2px 6px">Deep (&lt;3°)</th>
          </tr>
        </thead>
        <tbody>
          <tr><td style="padding:3px 6px">☀️ Sun</td>
              <td style="text-align:center;padding:3px 6px;color:#718096">N/A</td>
              <td style="text-align:center;padding:3px 6px;color:#718096">—</td></tr>
          <tr style="background:#16202e"><td style="padding:3px 6px">🌙 Moon</td>
              <td style="text-align:center;padding:3px 6px">12°</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr><td style="padding:3px 6px">♂️ Mars</td>
              <td style="text-align:center;padding:3px 6px">17°</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr style="background:#16202e"><td style="padding:3px 6px">☿ Mercury</td>
              <td style="text-align:center;padding:3px 6px">14° / 12°℞</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr><td style="padding:3px 6px">♃ Jupiter</td>
              <td style="text-align:center;padding:3px 6px">11°</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr style="background:#16202e"><td style="padding:3px 6px">♀️ Venus</td>
              <td style="text-align:center;padding:3px 6px">10°</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr><td style="padding:3px 6px">♄ Saturn</td>
              <td style="text-align:center;padding:3px 6px">15°</td>
              <td style="text-align:center;padding:3px 6px;color:#fc8181">≤ 3°</td></tr>
          <tr style="background:#16202e"><td style="padding:3px 6px">☊☋ Rahu/Ketu</td>
              <td style="text-align:center;padding:3px 6px;color:#718096" colspan="2">
                Shadow — not applicable</td></tr>
        </tbody>
      </table>
      <div style="margin-top:8px;padding:6px 8px;background:#1a2535;
                  border-left:3px solid #f6ad55;border-radius:4px;font-size:0.78rem;color:#a0aec0">
        <b style="color:#f6ad55">⚠️ Same-sign exception:</b> Combustion is only valid when
        Sun &amp; planet are in the <b>same rasi</b>. If they are in different signs the orb
        is shown as <span style="color:#718096">↔ Near (cross-sign)</span> — informational only,
        not a penalty.
      </div>
    </div>

    <!-- Gandanta zones -->
    <div>
      <div style="font-weight:700;color:#b794f4;margin-bottom:8px">
        ⚡ Gandanta Zones — ±3°20' at Water→Fire junctions
      </div>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="color:#718096;font-size:0.76rem;border-bottom:1px solid #2d3748">
            <th style="text-align:left;padding:2px 6px">Junction</th>
            <th style="padding:2px 6px">Water end</th>
            <th style="padding:2px 6px">Fire start</th>
          </tr>
        </thead>
        <tbody>
          <tr style="background:#16202e">
            <td style="padding:4px 6px">Pisces → Aries</td>
            <td style="text-align:center;padding:4px 6px">356°40'<br>
              <span style="color:#718096;font-size:0.74rem">(26°40' Pisces)</span></td>
            <td style="text-align:center;padding:4px 6px">3°20'<br>
              <span style="color:#718096;font-size:0.74rem">(3°20' Aries)</span></td>
          </tr>
          <tr>
            <td style="padding:4px 6px">Cancer → Leo</td>
            <td style="text-align:center;padding:4px 6px">116°40'<br>
              <span style="color:#718096;font-size:0.74rem">(26°40' Cancer)</span></td>
            <td style="text-align:center;padding:4px 6px">123°20'<br>
              <span style="color:#718096;font-size:0.74rem">(3°20' Leo)</span></td>
          </tr>
          <tr style="background:#16202e">
            <td style="padding:4px 6px">Scorpio → Sagittarius</td>
            <td style="text-align:center;padding:4px 6px">236°40'<br>
              <span style="color:#718096;font-size:0.74rem">(26°40' Scorpio)</span></td>
            <td style="text-align:center;padding:4px 6px">243°20'<br>
              <span style="color:#718096;font-size:0.74rem">(3°20' Sagittarius)</span></td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top:8px;padding:6px 8px;background:#1a1a35;
                  border-left:3px solid #b794f4;border-radius:4px;font-size:0.78rem;color:#a0aec0">
        <b style="color:#b794f4">Note:</b> The last 3°20' of each Water sign (Cancer, Scorpio,
        Pisces) and the first 3°20' of the following Fire sign (Leo, Sagittarius, Aries)
        form the Gandanta zone. Nodes at Gandanta carry especially intense karmic weight.
      </div>
    </div>

  </div>

  <!-- Pushkara Navamsa zones -->
  <div style="margin-top:14px;border-top:1px solid #2d3748;padding-top:12px">
    <div style="font-weight:700;color:#ffd700;margin-bottom:8px">
      🕉️ Pushkara Navamsa Zones — 24 divine-grace windows (3°20' each)
    </div>
    <div style="font-size:0.76rem;color:#a0aec0;margin-bottom:10px">
      A Pushkara Navamsa is a specific 3°20' division whose D9 sign falls in a Jupiter- or Venus-ruled sign.
      A planet here receives <b style="color:#ffd700">divine grace</b>.
      If it is also <b>deeply combust or Gandanta</b>, its Visha Gati (poisonous movement) is
      <b>neutralised</b> — initial struggle transforms into unexpected recovery. Score <b style="color:#ffd700">+5</b>.
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">

      <div style="background:#16202e;border-radius:6px;padding:8px">
        <div style="font-weight:600;color:#fc8181;margin-bottom:5px;font-size:0.78rem">🔥 Fire Signs</div>
        <div style="color:#e2e8f0;font-size:0.75rem;line-height:1.8">
          <b>Aries:</b> 20°00'–23°20' · 26°40'–30°00'<br>
          <b>Leo:</b> 20°00'–23°20' · 26°40'–30°00'<br>
          <b>Sagittarius:</b> 20°00'–23°20' · 26°40'–30°00'
        </div>
      </div>

      <div style="background:#16202e;border-radius:6px;padding:8px">
        <div style="font-weight:600;color:#68d391;margin-bottom:5px;font-size:0.78rem">🌿 Earth Signs</div>
        <div style="color:#e2e8f0;font-size:0.75rem;line-height:1.8">
          <b>Taurus:</b> 6°40'–10°00' · 13°20'–16°40'<br>
          <b>Virgo:</b> 6°40'–10°00' · 13°20'–16°40'<br>
          <b>Capricorn:</b> 6°40'–10°00' · 13°20'–16°40'
        </div>
      </div>

      <div style="background:#16202e;border-radius:6px;padding:8px">
        <div style="font-weight:600;color:#90cdf4;margin-bottom:5px;font-size:0.78rem">💨 Air Signs</div>
        <div style="color:#e2e8f0;font-size:0.75rem;line-height:1.8">
          <b>Gemini:</b> 16°40'–20°00' · 23°20'–26°40'<br>
          <b>Libra:</b> 16°40'–20°00' · 23°20'–26°40'<br>
          <b>Aquarius:</b> 16°40'–20°00' · 23°20'–26°40'
        </div>
      </div>

      <div style="background:#16202e;border-radius:6px;padding:8px">
        <div style="font-weight:600;color:#76e4f7;margin-bottom:5px;font-size:0.78rem">💧 Water Signs</div>
        <div style="color:#e2e8f0;font-size:0.75rem;line-height:1.8">
          <b>Cancer:</b> 0°00'–3°20' · 6°40'–10°00'<br>
          <b>Scorpio:</b> 0°00'–3°20' · 6°40'–10°00'<br>
          <b>Pisces:</b> 0°00'–3°20' · 6°40'–10°00'
        </div>
      </div>

    </div>
    <div style="margin-top:8px;padding:6px 8px;background:#1a1a2e;
                border-left:3px solid #ffd700;border-radius:4px;font-size:0.78rem;color:#a0aec0">
      <b style="color:#ffd700">Example:</b> Jupiter at 22° Leo = 20°–23°20' in Leo (Fire sign zone 1)
      → Purva Phalguni Pada 3 — Pushkara. If combust by Sun, shows
      <span style="color:#ffd700">🕉️ Divine Protection</span> instead of plain 🔥 Deep Combust.
    </div>
  </div>

</div>
</details>
"""


_PLANET_ICONS = {
    "Ascendant": "⬆️", "Sun": "☀️", "Moon": "🌙", "Mars": "♂️",
    "Mercury": "☿", "Jupiter": "♃", "Venus": "♀️", "Saturn": "♄",
    "Rahu": "☊", "Ketu": "☋",
}

def _comparison_table_html(natal: dict, transit: dict,
                            transit_date_label: str = "") -> str:
    """
    Build a side-by-side Natal vs Transit comparison table.
    Covers: Ascendant, 7 planets, Rahu, Ketu.
    Rahu/Ketu show 'N/A' for combustion (shadow planets).
    Ascendant transit column is blank (changes every ~2h).
    transit_date_label: shown in the Transit column header.
    """
    TD   = "style='padding:6px 9px;border-bottom:1px solid #2d3748;vertical-align:top'"
    TD_L = ("style='padding:6px 9px;border-bottom:1px solid #2d3748;"
            "vertical-align:top;border-left:2px solid #4a5568'")

    def _nak_cell(nak, pad, lord):
        return (f"<span style='font-weight:500'>{nak}</span>"
                f"<br><span style='color:#718096;font-size:0.76rem'>Pada {pad} · {lord}</span>")

    def _flags(data, is_node=False, is_asc=False):
        parts = []
        c  = data.get("combust", {})
        g  = data.get("gandanta", {})
        pk = data.get("pushkara", {})
        _o = c.get("orb", 0)

        is_hard_afflicted = c.get("deep") or g.get("gandanta")
        is_divine = pk.get("pushkara") and is_hard_afflicted and not is_asc

        # ── Divine Protection (highest priority badge) ────────────────────────
        if is_divine:
            zone = pk.get("zone", "")
            parts.append(
                '<span style="color:#ffd700;font-weight:700" '
                f'title="Pushkara Navamsa ({zone}). '
                'Planet is Hard Combust or Gandanta — but Pushkara energy neutralises '
                'the Visha Gati (poisonous movement). Initial loss/struggle transforms '
                'into unexpected divine recovery. Protection Score +5.">'
                '🕉️ Divine Protection (Pushkara)</span>'
            )
            # Still show the underlying affliction at smaller size for reference
            if c.get("deep") and not is_node and not is_asc:
                parts.append(
                    f'<span style="color:#fc8181;font-size:0.78rem">'
                    f'(🔥 burnt {_o:.1f}° — neutralised)</span>'
                )
            if g.get("gandanta"):
                jct = g.get("junction", "")
                parts.append(
                    f'<span style="color:#b794f4;font-size:0.78rem">'
                    f'(⚡ Gandanta {jct} — neutralised)</span>'
                )

        elif not is_node and not is_asc:
            # ── Hidden Strength: combust D1 + Vargottama D9 ──────────────────
            if (c.get("deep") or c.get("combust")) and data.get("vargottama"):
                parts.append(
                    '<span style="color:#f6e05e;font-weight:600" '
                    'title="Combust in D1 (rasi) but Vargottama in D9 (navamsa). '
                    'Surface struggle exists — inner protection active. '
                    'Temporary setback followed by deep success. '
                    '(per Parashara tradition)">'
                    '🌟 Hidden Strength (Combust + Vargottama)</span>'
                )
            else:
                # Regular combustion flags
                if c.get("deep"):
                    parts.append(
                        f'<span style="color:#fc8181;font-weight:600">'
                        f'🔥 Deep Combust ({_o:.1f}°)</span>'
                    )
                elif c.get("combust"):
                    parts.append(
                        f'<span style="color:#f6ad55">🔥 Combust ({_o:.1f}°)</span>'
                    )
                elif c.get("cross_sign") and c.get("would_combust"):
                    if not g.get("gandanta"):
                        parts.append(
                            f'<span style="color:#718096;font-size:0.8rem" '
                            f'title="Within {_o:.1f} deg orb but Sun is in a different sign — '
                            f'classical sign-wall exception applies">'
                            f'↔ Near ({_o:.1f}°) cross-sign</span>'
                        )
        elif is_node:
            parts.append(
                '<span style="color:#4a5568;font-size:0.78rem">☽☋ No combustion</span>'
            )

        # ── Gandanta (skip if Divine Protection already absorbed it) ─────────
        if g.get("gandanta") and not is_divine:
            jct  = g.get("junction", "")
            gorb = g.get("orb", 0)
            overrides = (
                not is_node and not is_asc
                and c.get("cross_sign") and c.get("would_combust")
            )
            label = f"Gandanta ({jct}, {gorb:.1f}°)"
            if overrides:
                label += " — overrides sign-wall"
            parts.append(f'<span style="color:#b794f4">⚡ {label}</span>')

        # ── Vargottama (standalone only) ──────────────────────────────────────
        already_merged = (
            not is_node and not is_asc
            and (c.get("deep") or c.get("combust")) and data.get("vargottama")
        )
        if data.get("vargottama") and not already_merged:
            parts.append('<span style="color:#68d391">✨ Vargottama</span>')

        # ── Standalone Pushkara (no hard affliction — just divine grace) ──────
        if pk.get("pushkara") and not is_divine and not is_asc:
            zone = pk.get("zone", "")
            parts.append(
                f'<span style="color:#90cdf4" '
                f'title="Pushkara Navamsa: {zone}. '
                f'Divine grace — planet\'s significations are naturally uplifted.">'
                f'🕉️ Pushkara</span>'
            )

        return " ".join(parts) if parts else '<span style="color:#4a5568">—</span>'

    _TRANSIT_NONE = (
        "<td colspan='5' "
        "style='padding:6px 9px;border-bottom:1px solid #2d3748;"
        "border-left:2px solid #4a5568;color:#4a5568;font-style:italic;"
        "text-align:center'>N/A — changes every 2 h</td>"
    )

    rows = []
    for planet in ALL_DISPLAY_PLANETS:
        n = natal.get(planet)
        if not n:
            continue

        icon     = _PLANET_ICONS.get(planet, "")
        is_node  = n.get("is_node", False)
        is_asc   = n.get("is_ascendant", False)
        retro_n  = (" <span style='color:#f6ad55;font-size:0.78rem'>℞</span>"
                    if n.get("retrograde") else "")

        n_nak_cell = _nak_cell(n.get("nakshatra","—"),
                               n.get("pada","—"),
                               n.get("nakshatra_lord","—"))
        n_flag_str = _flags(n, is_node=is_node, is_asc=is_asc)

        # row background alternation
        bg = "background:#16202e" if ALL_DISPLAY_PLANETS.index(planet) % 2 == 0 else ""

        natal_cells = (
            f"<td {TD} style='font-weight:700;color:#e2e8f0;{bg}'>"
            f"{icon} {planet}</td>"
            f"<td {TD}>{n['longitude']:.2f}°{retro_n}</td>"
            f"<td {TD}>{n['sign']}</td>"
            f"<td {TD}>{n_nak_cell}</td>"
            f"<td {TD}><span style='font-size:0.82rem'>{n.get('state','—')}</span></td>"
            f"<td {TD} style='border-right:2px solid #4a5568'>{n_flag_str}</td>"
        )

        if is_asc:
            transit_cells = _TRANSIT_NONE
        else:
            t = transit.get(planet)
            if not t:
                transit_cells = _TRANSIT_NONE
            else:
                retro_t = (" <span style='color:#f6ad55;font-size:0.78rem'>℞</span>"
                           if t.get("retrograde") else "")
                t_nak_cell = _nak_cell(t.get("nakshatra","—"),
                                       t.get("pada","—"),
                                       t.get("nakshatra_lord","—"))
                t_flag_str = _flags(t, is_node=is_node)
                transit_cells = (
                    f"<td {TD_L}>{t['longitude']:.2f}°{retro_t}</td>"
                    f"<td {TD}>{t['sign']}</td>"
                    f"<td {TD}>{t_nak_cell}</td>"
                    f"<td {TD}><span style='font-size:0.82rem'>{t.get('state','—')}</span></td>"
                    f"<td {TD}>{t_flag_str}</td>"
                )

        rows.append(f"<tr>{natal_cells}{transit_cells}</tr>")

    header = (
        "<thead>"
        "<tr style='background:#0f172a;color:#fff'>"
        "<th style='padding:10px 9px;text-align:left'>Planet</th>"
        "<th colspan='5' style='text-align:center;padding:10px;background:#1e3a5f;"
        "border-right:2px solid #4a5568'>🌟 Natal — Birth Chart</th>"
        "<th colspan='5' style='text-align:center;padding:10px;background:#14352a'>"
        f"🔭 Gocharam — Transit{(' · ' + transit_date_label) if transit_date_label else ''}</th>"
        "</tr>"
        "<tr style='background:#1e2535;color:#718096;font-size:0.78rem'>"
        "<th style='padding:5px 9px'></th>"
        "<th style='padding:5px 9px'>Longitude</th>"
        "<th style='padding:5px 9px'>Sign</th>"
        "<th style='padding:5px 9px'>Nakshatra · Pada · Lord</th>"
        "<th style='padding:5px 9px'>State</th>"
        "<th style='padding:5px 9px;border-right:2px solid #4a5568'>Flags</th>"
        "<th style='padding:5px 9px;border-left:2px solid #4a5568'>Longitude</th>"
        "<th style='padding:5px 9px'>Sign</th>"
        "<th style='padding:5px 9px'>Nakshatra · Pada · Lord</th>"
        "<th style='padding:5px 9px'>State</th>"
        "<th style='padding:5px 9px'>Flags</th>"
        "</tr></thead>"
    )
    body = "<tbody>" + "".join(rows) + "</tbody>"
    return (
        "<div style='overflow-x:auto;border-radius:8px;border:1px solid #2d3748;margin-top:8px'>"
        "<table style='width:100%;border-collapse:collapse;font-size:0.87rem;"
        "background:#1a202c;color:#e2e8f0'>"
        + header + body +
        "</table></div>"
    )


_CONCEPT_GUIDE_HTML = """
<div style="background:#1a202c;border:1px solid #2d3748;border-radius:10px;padding:20px;color:#e2e8f0;font-size:0.92rem;line-height:1.7">

  <h3 style="color:#90cdf4;margin-top:0">🪐 How to Read This Chart — Vedic Concepts Explained</h3>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:12px">

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#fbd38d;margin-bottom:6px">🌙 Nakshatra (Lunar Mansion)</div>
      The sky is divided into <b>27 Nakshatras</b>, each spanning <b>13°20'</b>.
      Every planet "sits" in one of these mansions at birth and in transit.
      Each Nakshatra has a ruling planet (its <em>lord</em>) that colours the planet's energy —
      e.g., Moon in Rohini (ruled by Moon) gives nurturing, creative energy.
      Nakshatras are finer than signs and reveal the <em>texture</em> of a planet's expression.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#fbd38d;margin-bottom:6px">🔢 Pada (Quarter)</div>
      Each Nakshatra is split into <b>4 Padas</b> (quarters) of <b>3°20'</b> each.
      The Pada maps to a Navamsa sign (D9 chart), adding another layer of detail.
      <b>Pada 1</b> = Aries energy, <b>Pada 2</b> = Taurus energy, etc., cycling through
      the signs in order. Knowing the Pada helps understand <em>which aspect</em> of the
      Nakshatra is activated.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#fc8181;margin-bottom:6px">🔥 Combustion (Astangata)</div>
      A planet that comes too close to the <b>Sun</b> gets "burned" and loses strength.
      Each planet has its own safe distance — e.g., Jupiter needs to stay beyond 11°,
      Venus beyond 10°. Within <b>3°</b> is <em>deep combustion</em> (severe).
      A combust planet struggles to deliver its significations: combust Venus can
      affect wealth/relationships; combust Mercury can affect communication.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#b794f4;margin-bottom:6px">⚡ Gandanta (Karmic Knot)</div>
      Gandanta zones sit at the <b>Water–Fire sign junctions</b>:
      Pisces/Aries (0°), Cancer/Leo (120°), Scorpio/Sagittarius (240°).
      A planet within <b>±3°20'</b> of these points is in a Gandanta zone —
      considered a "knot" between worlds. It indicates karmic intensity and
      unresolved soul-level themes that require conscious healing.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#68d391;margin-bottom:6px">✨ Vargottama (Amplified Strength)</div>
      A planet is Vargottama when its <b>D1 (Rasi/birth chart) sign equals its D9 (Navamsa) sign</b>.
      This happens at the beginning and middle of each sign. It is considered
      <em>very auspicious</em> — the planet's qualities are amplified and more reliably expressed.
      A Vargottama Venus, for example, strongly blesses love, beauty, and abundance.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#63b3ed;margin-bottom:6px">🔄 Transit / Gocharam (Live Positions)</div>
      While your <em>natal chart</em> is fixed at birth, planets keep moving.
      <b>Gocharam</b> (transit) compares <em>where planets are today</em> against your natal positions.
      When a transit planet activates a natal weak point (e.g., transit Sun conjuncts your natal
      combust Venus), that theme is triggered. When a transit planet moves <em>away</em> from
      combustion, it opens an "action window" — a window to act on that planet's themes.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#f6ad55;margin-bottom:6px">🛡️ Protection Score (1–10)</div>
      A composite score based on your natal planet conditions:<br>
      <span style="color:#fc8181">−2 Deep Combustion</span> · <span style="color:#f6ad55">−1 Combustion</span> ·
      <span style="color:#b794f4">−2 Gandanta</span> · <span style="color:#68d391">+2 Vargottama</span> ·
      <span style="color:#ffd700">+5 Divine Protection (Pushkara overrides Visha Gati)</span><br>
      Baseline: <b>5</b>. Score 1–4 = Low · 5–6 = Moderate · 7–10 = Strong.
      This is <em>not</em> a fatalistic number — it highlights areas to be aware of and work with.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#ffd700;margin-bottom:6px">🕉️ Pushkara Navamsa (Divine Grace)</div>
      Pushkara Navamsas are <b>24 specific 3°20' zones</b> across the zodiac whose Navamsa (D9)
      sign falls in a <em>Jupiter- or Venus-ruled sign</em> — conferring divine grace and upliftment.
      <br><br>
      <b style="color:#ffd700">Visha Gati Neutralised:</b> If a planet is <em>deeply combust</em>
      or in <em>Gandanta</em> (Visha Gati — poisonous movement), but also sits in a Pushkara
      Navamsa, the affliction is overridden. The native faces <em>initial struggle</em> but
      experiences <em>unexpected divine recovery</em>.
      <br><br>
      The score modifier is <b style="color:#ffd700">+5</b>, reflecting the exceptional protective
      power. Each of the 12 signs has exactly 2 Pushkara zones (2 per sign × 12 = 24 total).
      See the reference table below the chart for all 24 exact degree ranges.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#f687b3;margin-bottom:6px">☊☋ Rahu &amp; Ketu (Shadow Planets)</div>
      Rahu (North Node) and Ketu (South Node) are <b>mathematical points</b> — the intersections of
      the Moon's orbit with the ecliptic. They are <em>always</em> exactly opposite (180° apart)
      and always retrograde. They carry karmic significance:<br>
      <b>Rahu</b> = desires, ambition, future-directed karma.<br>
      <b>Ketu</b> = detachment, past-life wisdom, spiritual liberation.<br>
      Because they are shadow points (not physical bodies), <b>combustion does not apply</b>.
      Gandanta and Vargottama <em>do</em> apply — nodes at a Water-Fire junction indicate
      especially intense karmic knots.
    </div>

    <div style="background:#2d3748;border-radius:8px;padding:14px">
      <div style="font-weight:700;color:#76e4f7;margin-bottom:6px">⬆️ Ascendant (Lagna)</div>
      The Ascendant is the degree of the zodiac <b>rising on the eastern horizon</b> at the exact
      moment of birth. It is the most personal point in the chart — it defines your body, personality,
      and how the world sees you. The Ascendant changes sign every ~2 hours, so an accurate birth
      time is critical. Gandanta Lagna (Ascendant at a Water-Fire junction) at birth is considered
      a very significant karmic marker. No transit Ascendant is shown since it would not be
      meaningful for comparison.
    </div>

  </div>
</div>
"""


def _natal_status_badge(planet: str, natal_data: dict) -> str:
    """Return a compact HTML badge for a planet's natal protection status."""
    if planet not in natal_data:
        return '<span style="color:#718096">—</span>'
    d   = natal_data[planet]
    c   = d.get("combust", {})
    g   = d.get("gandanta", {})
    pk  = d.get("pushkara", {})
    is_node = d.get("is_node", False)

    is_hard  = c.get("deep") or g.get("gandanta")
    pk_zone  = pk.get("zone", "")
    # Divine Protection takes highest priority
    if pk.get("pushkara") and is_hard and not is_node:
        return (
            '<span style="color:#ffd700;font-weight:700" '
            f'title="{pk_zone}">'
            '🕉️ Divine Protection</span>'
        )
    # Hidden Strength: combust + vargottama
    if not is_node and (c.get("deep") or c.get("combust")) and d.get("vargottama"):
        return '<span style="color:#f6e05e;font-weight:600">🌟 Hidden Strength</span>'
    if not is_node and c.get("deep"):
        return f'<span style="color:#fc8181">🔥 Deep Combust ({c["orb"]:.1f}°)</span>'
    if not is_node and c.get("combust"):
        return f'<span style="color:#f6ad55">🔥 Combust ({c["orb"]:.1f}°)</span>'
    if g.get("gandanta"):
        jct = g.get("junction", "")
        return f'<span style="color:#b794f4">⚡ Gandanta ({jct})</span>'
    if pk.get("pushkara"):
        return '<span style="color:#90cdf4">🕉️ Pushkara</span>'
    if d.get("vargottama"):
        return '<span style="color:#68d391">✨ Vargottama</span>'
    return '<span style="color:#68d391">🟢 Clear</span>'


def _transit_alert_badge(scan: dict) -> str:
    """Return a compact HTML transit alert badge from scan_transit_affliction result."""
    if not scan:
        return '<span style="color:#718096">—</span>'
    if scan["currently_afflicted"]:
        aff   = scan["affliction_type"]
        exits = scan["exits_in_days"]
        col   = "#fc8181" if "Deep" in aff or "Gandanta" in aff else "#f6ad55"
        badge = f'<span style="color:{col}">⚠️ {aff} now</span>'
        if exits is not None:
            badge += f'<br><span style="color:#718096;font-size:0.78rem">exits in ~{exits} days</span>'
        else:
            badge += '<br><span style="color:#718096;font-size:0.78rem">active beyond 12-month horizon</span>'
        # Next event after exit
        if scan.get("next_entry_date"):
            badge += (f'<br><span style="color:#718096;font-size:0.78rem">'
                      f'next: {scan["next_entry_type"]} ~{scan["next_entry_date"]}</span>')
    else:
        if scan.get("next_entry_days"):
            nd   = scan["next_entry_days"]
            ndt  = scan["next_entry_date"]
            ntyp = scan["next_entry_type"]
            col  = "#f6ad55" if nd < 60 else "#a0aec0"
            badge = (f'<span style="color:#68d391">🟢 Clear now</span>'
                     f'<br><span style="color:{col};font-size:0.78rem">'
                     f'📅 next {ntyp} in {nd}d (~{ndt})</span>')
        else:
            badge = '<span style="color:#68d391">🟢 Clear — 12 months</span>'
    return badge


# Planet-specific precautions when a Dasha/Bhukti lord is natally afflicted
_PLANET_PRECAUTIONS = {
    "Sun":     "Avoid confrontations with authority. Strengthen self-confidence through service.",
    "Moon":    "Guard emotional stability. Avoid impulsive decisions; nurture mental peace.",
    "Mars":    "Control aggression. Avoid legal disputes and risky physical activities.",
    "Mercury": "Verify contracts and communications carefully. Avoid speculation.",
    "Jupiter": "Don't over-commit or be overly generous. Seek wise counsel before expanding.",
    "Venus":   "Avoid major financial decisions or luxury purchases. Relationships need patience.",
    "Saturn":  "Expect delays — plan for them. Discipline and consistency are your shield.",
    "Rahu":    "Guard against obsession and shortcuts. Clarity of purpose is protection.",
    "Ketu":    "Avoid detachment becoming avoidance. Stay grounded in practical duties.",
}


def _dasha_panel_html(db: dict, natal_data: dict,
                       scan_maha: dict, scan_bhukti: dict,
                       transit_date_str: str) -> str:
    """
    Render the Dasha/Bhukti panel showing:
     - Active Maha Dasha and Bhukti with countdown
     - Natal protection status of both lords
     - Transit affliction scan alerts for both lords
     - Precautions if either lord is natally afflicted
    """
    if not db:
        return ""

    maha   = db["maha"]
    bhukti = db["bhukti"]

    def _fmt_date(dt):
        return dt.strftime("%d %b %Y") if isinstance(dt, datetime.datetime) else str(dt)

    def _days_badge(days):
        if days <= 90:
            col = "#fc8181"
        elif days <= 365:
            col = "#f6ad55"
        else:
            col = "#68d391"
        return f'<span style="color:{col};font-weight:600">⏳ {days:,} days remaining</span>'

    maha_natal   = _natal_status_badge(maha["lord"],   natal_data)
    bhukti_natal = _natal_status_badge(bhukti["lord"], natal_data)
    maha_transit = _transit_alert_badge(scan_maha)
    bhukti_transit = _transit_alert_badge(scan_bhukti)

    # Collect affliction warnings for precaution section
    warnings = []
    for role, lord, scan in [("Maha Dasha", maha["lord"], scan_maha),
                              ("Bhukti",     bhukti["lord"], scan_bhukti)]:
        nd = natal_data.get(lord, {})
        c  = nd.get("combust", {})
        aff_natal = (c.get("combust") or c.get("deep")) and not nd.get("is_node")
        aff_gand  = nd.get("gandanta", {}).get("gandanta")
        if aff_natal or aff_gand:
            kind = "Deep Combust" if c.get("deep") else ("Combust" if aff_natal else "Gandanta")
            prec = _PLANET_PRECAUTIONS.get(lord, "Exercise caution in all major decisions.")
            warnings.append((role, lord, kind, prec))
        if scan and scan["currently_afflicted"]:
            transit_prec = _PLANET_PRECAUTIONS.get(lord, "Exercise caution.")
            warnings.append((f"Transit {lord}", lord, scan["affliction_type"], transit_prec))

    # ── HTML ──────────────────────────────────────────────────────────────────
    transit_note = (f"Transit date: <b>{transit_date_str}</b>. "
                    "Transit scan always runs from <b>today</b>.")

    html = f"""
<div style="margin-top:16px;background:#0f172a;border:1px solid #2d3748;
            border-radius:8px;padding:16px;color:#cbd5e0;font-size:0.85rem">

  <div style="font-size:1rem;font-weight:700;color:#90cdf4;margin-bottom:12px">
    🕐 Active Vimshottari Dasha &amp; Bhukti
    <span style="font-size:0.75rem;font-weight:400;color:#718096;margin-left:8px">
      ({transit_note})
    </span>
  </div>

  <!-- Two-column Maha Dasha / Bhukti cards -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px">

    <!-- Maha Dasha card -->
    <div style="background:#16202e;border:1px solid #2d3748;border-radius:6px;padding:12px">
      <div style="color:#718096;font-size:0.72rem;text-transform:uppercase;
                  letter-spacing:.05em;margin-bottom:4px">Maha Dasha</div>
      <div style="font-size:1.2rem;font-weight:700;color:#e2e8f0">
        {maha["lord"].upper()}
        <span style="font-size:0.75rem;color:#718096;font-weight:400">
          ({VIMSHOTTARI_YEARS[maha["lord"]]} yrs)
        </span>
      </div>
      <div style="color:#718096;font-size:0.78rem;margin-top:2px">
        Ends: {_fmt_date(maha["end"])}
      </div>
      <div style="margin-top:6px">{_days_badge(maha["days_remaining"])}</div>
      <div style="margin-top:8px;border-top:1px solid #2d3748;padding-top:8px">
        <span style="color:#718096;font-size:0.75rem">Natal: </span>
        {maha_natal}
      </div>
      <div style="margin-top:6px">
        <span style="color:#718096;font-size:0.75rem">Transit: </span>
        {maha_transit}
      </div>
    </div>

    <!-- Bhukti card -->
    <div style="background:#16202e;border:1px solid #4a5568;border-left:3px solid #805ad5;
                border-radius:6px;padding:12px">
      <div style="color:#718096;font-size:0.72rem;text-transform:uppercase;
                  letter-spacing:.05em;margin-bottom:4px">Current Bhukti (sub-period)</div>
      <div style="font-size:1.2rem;font-weight:700;color:#e2e8f0">
        {bhukti["lord"].upper()}
        <span style="font-size:0.75rem;color:#718096;font-weight:400">
          ({bhukti["years"]:.1f} yrs)
        </span>
      </div>
      <div style="color:#718096;font-size:0.78rem;margin-top:2px">
        Ends: {_fmt_date(bhukti["end"])}
      </div>
      <div style="margin-top:6px">{_days_badge(bhukti["days_remaining"])}</div>
      <div style="margin-top:8px;border-top:1px solid #2d3748;padding-top:8px">
        <span style="color:#718096;font-size:0.75rem">Natal: </span>
        {bhukti_natal}
      </div>
      <div style="margin-top:6px">
        <span style="color:#718096;font-size:0.75rem">Transit: </span>
        {bhukti_transit}
      </div>
    </div>

  </div>

  <!-- Interpretation -->
  <div style="background:#16202e;border-radius:6px;padding:10px 12px;
              font-size:0.82rem;color:#a0aec0;margin-bottom:{ '12px' if warnings else '0' }">
    <b style="color:#90cdf4">📖 Reading:</b>&nbsp;
    You are in the <b style="color:#e2e8f0">{maha["lord"]} Maha Dasha</b> — the overarching
    life-theme for {maha["years"]} years. The active sub-period
    (<b style="color:#e2e8f0">{maha["lord"]}/{bhukti["lord"]} Bhukti</b>) delivers
    day-to-day events through the lens of <b>{bhukti["lord"]}</b>'s significations.
    The <b>natal status</b> above shows how strongly or weakly each lord operates in your chart.
    The <b>transit status</b> shows if that planet is under additional stress <i>right now</i>
    in the sky — a double affliction (natal + transit) signals a demanding window.
  </div>
"""

    # ── Warnings / Precautions ────────────────────────────────────────────────
    if warnings:
        seen = set()
        html += """
  <div style="margin-top:0;border-top:1px solid #2d3748;padding-top:12px">
    <div style="color:#f6ad55;font-weight:600;margin-bottom:8px">⚠️ Precautions</div>
"""
        for role, lord, kind, prec in warnings:
            key = (lord, kind)
            if key in seen:
                continue
            seen.add(key)
            col = "#fc8181" if "Deep" in kind or "Gandanta" in kind else "#f6ad55"
            html += f"""
    <div style="background:#1a1a1a;border-left:3px solid {col};border-radius:4px;
                padding:8px 10px;margin-bottom:6px;font-size:0.81rem">
      <b style="color:{col}">{role} — {lord} ({kind}):</b>&nbsp;
      <span style="color:#a0aec0">{prec}</span>
    </div>
"""
        html += "  </div>\n"

    html += "</div>\n"
    return html


_PK_SCAN_PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
]


def _pushkara_forecast_card_html(scans: dict, ref_date_str: str = "") -> str:
    """
    Render upcoming Pushkara Navamsa transit card.
    scans: {planet_name: scan_pushkara_transit result dict}
    """
    if not scans:
        return ""

    now_in   = [(p, s) for p, s in scans.items() if s.get("currently_pushkara")]
    upcoming = [(p, s) for p, s in scans.items()
                if not s.get("currently_pushkara") and s.get("next_entry_days") is not None]
    upcoming.sort(key=lambda x: x[1]["next_entry_days"])

    if not now_in and not upcoming:
        return ""

    def _exit_str(s):
        e = s.get("exits_in_days")
        return f"exits in ~{e} days" if e is not None else "active beyond 6-month horizon"

    # ── Currently in Pushkara rows ────────────────────────────────────────────
    now_rows = ""
    for planet, s in now_in:
        zone = s.get("current_zone", "")
        now_rows += f"""
      <tr style="background:#16202e">
        <td style="padding:5px 8px">{_PLANET_ICONS.get(planet,'☿')} {planet}</td>
        <td style="padding:5px 8px;color:#ffd700">{zone}</td>
        <td style="padding:5px 8px;color:#a0aec0;font-size:0.78rem">{_exit_str(s)}</td>
      </tr>"""

    # ── Upcoming entries (max 8 rows) ─────────────────────────────────────────
    up_rows = ""
    for planet, s in upcoming[:8]:
        nd   = s["next_entry_days"]
        ndt  = s["next_entry_date"]
        zone = s.get("next_entry_zone", "")
        col  = "#ffd700" if nd <= 30 else ("#90cdf4" if nd <= 60 else "#a0aec0")
        up_rows += f"""
      <tr>
        <td style="padding:5px 8px">{_PLANET_ICONS.get(planet,'☿')} {planet}</td>
        <td style="padding:5px 8px;color:{col}">{zone}</td>
        <td style="padding:5px 8px;color:{col};font-weight:600">in {nd} days
          <br><span style="color:#718096;font-size:0.76rem">~{ndt}</span></td>
      </tr>"""

    now_section = ""
    if now_rows:
        now_section = f"""
  <div style="font-weight:600;color:#ffd700;margin-bottom:6px">✨ Currently in Pushkara</div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:12px">
    <thead><tr style="color:#718096;font-size:0.76rem;border-bottom:1px solid #2d3748">
      <th style="text-align:left;padding:3px 8px">Planet</th>
      <th style="text-align:left;padding:3px 8px">Zone</th>
      <th style="text-align:left;padding:3px 8px">Status</th>
    </tr></thead>
    <tbody>{now_rows}</tbody>
  </table>"""

    up_section = ""
    if up_rows:
        up_section = f"""
  <div style="font-weight:600;color:#90cdf4;margin-bottom:6px">📅 Upcoming entries (next 6 months)</div>
  <table style="width:100%;border-collapse:collapse">
    <thead><tr style="color:#718096;font-size:0.76rem;border-bottom:1px solid #2d3748">
      <th style="text-align:left;padding:3px 8px">Planet</th>
      <th style="text-align:left;padding:3px 8px">Zone</th>
      <th style="text-align:left;padding:3px 8px">When</th>
    </tr></thead>
    <tbody>{up_rows}</tbody>
  </table>"""

    ref_note = f'<br><span style="color:#718096;font-size:0.76rem">Computed from: {ref_date_str}</span>' if ref_date_str else ""

    return f"""
<div style="margin-top:16px;background:#0f172a;border:1px solid #2d3748;
            border-radius:8px;padding:16px;color:#cbd5e0;font-size:0.85rem">

  <div style="font-size:1rem;font-weight:700;color:#ffd700;margin-bottom:4px">
    🕉️ Pushkara Navamsa — Transit Forecast
  </div>
  <div style="font-size:0.78rem;color:#a0aec0;margin-bottom:12px">
    When a transiting planet occupies a Pushkara zone its significations receive
    <b style="color:#ffd700">divine grace</b>. If it is simultaneously afflicted
    (combust or Gandanta), the <b>Visha Gati is neutralised</b> — initial setbacks
    are unexpectedly restored.{ref_note}
  </div>
  {now_section}
  {up_section}

</div>
"""


def run_protection_analysis(dob: str, tob: str, lat, lon, transit_date: str = None):
    """
    Tab 7 main compute function.
    Returns (score_html, table_html, dasha_html, ai_markdown, pushkara_html).
    """
    _blank5 = ("", "", "", "", "")
    try:
        # ── Input validation ───────────────────────────────────────────────
        if not dob or not tob:
            msg = "⚠️ Please enter Date of Birth and Time of Birth."
            return msg, msg, msg, msg, ""
        dob = str(dob).strip()
        tob = str(tob).strip()
        try:
            datetime.datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
        except ValueError:
            err = (
                "⚠️ **Invalid date or time format.**  \n"
                "- Date must be **YYYY-MM-DD** (e.g. `1978-09-18`)  \n"
                "- Time must be **HH:MM** in 24-hour format (e.g. `17:35`)"
            )
            return err, err, err, err, ""
        if lat is None or lon is None:
            msg2 = "⚠️ Click 'Resolve Location' or enter Latitude/Longitude manually."
            return "⚠️ Location required.", msg2, "", "", ""

        # Resolve transit date (default today)
        td_str = (transit_date or "").strip() or datetime.datetime.utcnow().strftime("%Y-%m-%d")
        try:
            datetime.datetime.strptime(td_str, "%Y-%m-%d")
        except ValueError:
            td_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

        # ── Core calculation ───────────────────────────────────────────────
        ap         = AstrologyProtection(dob, tob, float(lat), float(lon),
                                         transit_date=td_str)
        score_html = _protection_score_html(ap.protection_score)
        table_html = _comparison_table_html(ap.natal_data, ap.transit_data,
                                             transit_date_label=td_str)

        # ── Vimshottari Dasha / Bhukti ─────────────────────────────────────
        moon_lon   = ap.natal_data["Moon"]["longitude"]
        birth_utc  = ap._birth_utc   # stored in __init__
        now_utc    = datetime.datetime.utcnow()
        dasha_list = calculate_vimshottari_dasha(moon_lon, birth_utc)
        db         = get_current_dasha_bhukti(dasha_list, now_utc)

        dasha_html = ""
        if db:
            scan_maha   = scan_transit_affliction(db["maha"]["lord"],   now_utc)
            scan_bhukti = scan_transit_affliction(db["bhukti"]["lord"], now_utc)
            dasha_html  = _dasha_panel_html(db, ap.natal_data,
                                             scan_maha, scan_bhukti, td_str)
        else:
            dasha_html = (
                '<div style="padding:1rem;color:#f6ad55">'
                '⚠️ Dasha period not found: the reference date falls outside '
                'the 120-year Vimshottari cycle computed from this birth date. '
                'Check that the birth date and time are correct.'
                '</div>'
            )

        # ── Pushkara transit forecast ──────────────────────────────────────
        pk_scans = {p: scan_pushkara_transit(p, now_utc, days_ahead=180)
                    for p in _PK_SCAN_PLANETS}
        pushkara_html = _pushkara_forecast_card_html(pk_scans, td_str)

        ai_text = ap.get_protection_analysis(openai_api_key=OPENAI_API_KEY)
        return score_html, table_html, dasha_html, ai_text, pushkara_html

    except Exception as exc:
        import traceback
        err = f"⚠️ Error: {exc}"
        return err, err, "", err, ""


# ─────────────────────────────────────────────────────────────────────────────
# Gradio UI
# ─────────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="Mundane Astrology Dashboard",
               theme=gr.themes.Soft(),
               css=_GRADIO_CSS) as demo:

    gr.Markdown(
        "# 🪐 Mundane Astrology Dashboard\n"
        "**Vedic Gocharam (Transit) Analysis for Nations** — "
        "India · USA · China · EU"
    )

    # Shared inputs
    with gr.Row(elem_classes=["top-inputs-row"]):
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
                "🔴 Diagonal slash = Country Lagna (ASC). "
                "**ᴰ** = Mahadasha Lord · **ᴮ** = Bhukti Lord"
            )
            country_dd5 = gr.Dropdown(
                choices=COUNTRIES, value="India", label="Select Country"
            )
            # Row 1: both charts side by side (stacks vertically on mobile)
            with gr.Row(elem_classes=["charts-row"]):
                natal_chart_out   = gr.HTML(label="📜 National Natal Chart (Fixed)")
                transit_chart_out = gr.HTML(label="🌐 Live Transit Chart (Gocharam)")
            # Row 2: Quick Summary Pulse + Daily Pulse (stacks vertically on mobile)
            with gr.Row(elem_classes=["pulse-row"]):
                with gr.Column(scale=3):
                    quick_pulse_out = gr.HTML(label="⚡ Quick Summary Pulse")
                with gr.Column(scale=2):
                    daily_pulse_out = gr.HTML(label="📊 Daily Pulse")

        # ── Tab 6: Dasha Timeline ──────────────────────────────────────────
        with gr.Tab("📅 Dasha Timeline"):
            gr.Markdown(
                "**Vimshottari Dasha & Bhukti** — National period analysis. "
                "Shows current Mahadasha (major cycle) + Bhukti (sub-period trigger), "
                "their relationship, a Double Trigger alert cross-referencing transit stress, "
                "and the full dasha timeline."
            )
            country_dd6 = gr.Dropdown(
                choices=COUNTRIES, value="India", label="Select Country"
            )
            dasha_out = gr.HTML(label="📅 Dasha & Bhukti Timeline")

        # ── Tab 7: Natal Protection Analysis ──────────────────────────────────
        with gr.Tab("🛡️ Natal Protection"):
            gr.Markdown(
                "Enter your birth details to calculate your **Vedic Protection Score** (1–10). "
                "Shows Nakshatra, Pada, Combustion, Gandanta, and Vargottama for all 7 natal planets "
                "alongside live transit (Gocharam) positions. AI generates personalised alerts and action windows."
            )

            with gr.Accordion("📚 What do these terms mean? (Concept Guide)", open=False):
                gr.HTML(_CONCEPT_GUIDE_HTML)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Birth Details")
                    np_dob  = gr.Textbox(label="Date of Birth (YYYY-MM-DD)",
                                         placeholder="e.g. 1978-09-18")
                    np_tob  = gr.Textbox(label="Time of Birth (HH:MM, 24h)",
                                         placeholder="e.g. 17:35")
                    np_place = gr.Textbox(label="Place of Birth",
                                          placeholder="e.g. Chennai, India")
                    np_resolve_btn = gr.Button("📍 Resolve Location", variant="secondary")
                    np_location_md = gr.Markdown("_Enter a place name and click Resolve._")
                    np_lat = gr.Number(label="Latitude", precision=5)
                    np_lon = gr.Number(label="Longitude", precision=5)
                    gr.Markdown("### Transit Date")
                    with gr.Row():
                        np_transit_date = gr.Textbox(
                            label="Transit Date (YYYY-MM-DD)",
                            value=datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                            placeholder="e.g. 2025-06-15",
                            scale=3,
                        )
                        np_today_btn = gr.Button("📅 Today", scale=1, variant="secondary")
                    np_analyse_btn = gr.Button("🔍 Analyse Protection", variant="primary")

                with gr.Column(scale=2):
                    np_score_out = gr.HTML(label="Protection Score")
                    np_table_out = gr.HTML(label="Natal vs Transit Comparison")
                    gr.HTML(_REFERENCE_HTML)

            np_dasha_out    = gr.HTML()
            np_pushkara_out = gr.HTML()
            gr.Markdown("### 🤖 AI Analysis")
            np_ai_out = gr.Markdown("_Click 'Analyse Protection' to generate the report._")

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
    calc_btn.click(
        fn=dasha_timeline,
        inputs=[date_input, country_dd6],
        outputs=[dasha_out],
    )
    country_dd6.change(
        fn=dasha_timeline,
        inputs=[date_input, country_dd6],
        outputs=[dasha_out],
    )

    # ── Tab 7: Natal Protection wiring ────────────────────────────────────
    np_resolve_btn.click(
        fn=resolve_location,
        inputs=[np_place],
        outputs=[np_lat, np_lon, np_location_md],
    )
    np_today_btn.click(
        fn=lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        inputs=[],
        outputs=[np_transit_date],
    )
    np_analyse_btn.click(
        fn=run_protection_analysis,
        inputs=[np_dob, np_tob, np_lat, np_lon, np_transit_date],
        outputs=[np_score_out, np_table_out, np_dasha_out, np_ai_out, np_pushkara_out],
    )

    # ── Auto-load on page open ─────────────────────────────────────────────
    # Pre-populate every tab so users see content immediately without
    # having to click "Calculate Transits" first.
    demo.load(
        fn=dasha_timeline,
        inputs=[date_input, country_dd6],
        outputs=[dasha_out],
    )
    demo.load(
        fn=visual_astro_charts,
        inputs=[date_input, country_dd5],
        outputs=[natal_chart_out, transit_chart_out, quick_pulse_out, daily_pulse_out],
    )
    demo.load(
        fn=regional_analysis,
        inputs=[date_input, country_dd],
        outputs=[gauge_out, pulse_out, analysis_out, natal_out],
    )
    demo.load(
        fn=run_calculations,
        inputs=[date_input],
        outputs=[heatmap_html_out, raw_ephe_out],
    )
    demo.load(
        fn=weekly_watch,
        inputs=[date_input],
        outputs=[retro_html_out, ingress_html_out, lunation_html_out, watch_html_out],
    )
    demo.load(
        fn=mundane_analysis,
        inputs=[date_input, country_dd2],
        outputs=[mundane_html_out, raw_ephe_out2],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )
