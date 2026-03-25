"""
Vimshottari Dasha / Bhukti Engine — Mundane Astrology Dashboard
Adapted from: https://github.com/sivaramanrajagopal/Ashtavargam
              calculators/dasha_calculator.py  (MIT licence)

Standalone — no swisseph needed; uses hardcoded sidereal Moon longitudes
derived from national founding charts.
"""

import datetime
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# ─── Vimshottari constants ────────────────────────────────────────────────────
NAKSHATRAS: List[str] = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati",
]

# 9-lord cycle repeated 3× to cover all 27 nakshatras
NAKSHATRA_LORDS: List[str] = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
] * 3

# Vimshottari Dasha durations (total = 120 years)
DASA_DURATIONS: OrderedDict = OrderedDict([
    ("Ketu", 7), ("Venus", 20), ("Sun", 6),  ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
])

# ─── Mundane focus & trigger descriptions ────────────────────────────────────
DASHA_FOCUS: Dict[str, str] = {
    "Sun":     "Leadership, Authority & State Power",
    "Moon":    "Public Sentiment, Trade & Agriculture",
    "Mercury": "Commerce, Media & Negotiations",
    "Venus":   "Economy, Culture & Alliances",
    "Mars":    "Military Action, Energy & Borders",
    "Jupiter": "Expansion, Justice & Institutional Growth",
    "Saturn":  "Austerity, Reform & Structural Discipline",
    "Rahu":    "Foreign Affairs, Tech Disruption & Shadow Power",
    "Ketu":    "Dissolution, Isolation & Spiritual Shifts",
}

BHUKTI_TRIGGER: Dict[str, str] = {
    "Sun":     "Leadership reshuffle, policy announcements",
    "Moon":    "Public protests, market volatility, elections",
    "Mercury": "Trade negotiations, media storms, tech launches",
    "Venus":   "Diplomatic deals, economic stimulus packages",
    "Mars":    "Military escalation, territorial disputes, fires",
    "Jupiter": "Legal rulings, economic expansion, treaties",
    "Saturn":  "Austerity measures, labour unrest, structural reform",
    "Rahu":    "Sudden shocks, foreign interference, viral crises",
    "Ketu":    "Covert operations, internal splits, silent withdrawals",
}

# ─── Vedic planetary friendship table (traditional) ──────────────────────────
PLANET_FRIENDSHIPS: Dict[str, Dict[str, set]] = {
    "Sun":     {"friends": {"Moon","Mars","Jupiter"},          "enemies": {"Venus","Saturn","Rahu","Ketu"}},
    "Moon":    {"friends": {"Sun","Mercury"},                  "enemies": {"Rahu","Ketu"}},
    "Mercury": {"friends": {"Sun","Venus"},                    "enemies": {"Moon"}},
    "Venus":   {"friends": {"Mercury","Saturn"},               "enemies": {"Sun","Moon","Rahu","Ketu"}},
    "Mars":    {"friends": {"Sun","Moon","Jupiter"},           "enemies": {"Mercury","Rahu","Ketu"}},
    "Jupiter": {"friends": {"Sun","Moon","Mars"},              "enemies": {"Mercury","Venus","Rahu","Ketu"}},
    "Saturn":  {"friends": {"Mercury","Venus","Rahu","Ketu"},  "enemies": {"Sun","Moon","Mars"}},
    "Rahu":    {"friends": {"Venus","Saturn"},                 "enemies": {"Sun","Moon","Mars"}},
    "Ketu":    {"friends": {"Mars","Jupiter"},                 "enemies": {"Sun","Moon","Venus"}},
}

_MALEFICS = {"Mars", "Saturn", "Rahu", "Ketu"}
_BENEFICS = {"Jupiter", "Venus"}


def get_relationship(dasha_lord: str, bhukti_lord: str) -> str:
    """Return 'Same', 'Friend', 'Enemy', or 'Neutral' between two planetary lords."""
    if dasha_lord == bhukti_lord:
        return "Same"
    rel = PLANET_FRIENDSHIPS.get(dasha_lord, {})
    if bhukti_lord in rel.get("friends", set()):
        return "Friend"
    if bhukti_lord in rel.get("enemies", set()):
        return "Enemy"
    return "Neutral"


# ─── National founding Moon data (sidereal Lahiri) ───────────────────────────
COUNTRY_BIRTH_DATA: Dict[str, dict] = {
    "India": {
        "birth_date": "1947-08-15",
        "moon_long":  100.0,    # Pushya nakshatra (Cancer ~7°), Lord = Saturn
        "notes":      "Independence — 15 Aug 1947, 00:00 IST, New Delhi",
    },
    "USA": {
        "birth_date": "1776-07-04",
        "moon_long":  313.0,    # Shatabhisha (Aquarius ~7°), Lord = Rahu
        "notes":      "Declaration of Independence — 4 Jul 1776, Philadelphia",
    },
    "China": {
        "birth_date": "1949-10-01",
        "moon_long":  200.0,    # Vishakha (Libra ~20°), Lord = Jupiter
        "notes":      "PRC Founding — 1 Oct 1949, 15:01 CST, Beijing",
    },
    "EU": {
        "birth_date": "1993-11-01",
        "moon_long":  136.0,    # Purva Phalguni (Leo ~16°), Lord = Venus
        "notes":      "Maastricht Treaty — 1 Nov 1993, Brussels",
    },
}

_NAK_LEN = 360.0 / 27  # ≈ 13.333°


# ─── Core calculation helpers ─────────────────────────────────────────────────
def _get_nakshatra(longitude: float) -> Tuple[str, int, int]:
    """Return (nakshatra_name, pada 1-4, nakshatra_index 0-26)."""
    idx  = int((longitude % 360) / _NAK_LEN)
    pada = int(((longitude % _NAK_LEN) / (_NAK_LEN / 4)) + 1)
    return NAKSHATRAS[idx], min(pada, 4), idx


def _generate_dashas(moon_long: float, birth_date_str: str) -> List[dict]:
    """
    Build the full Vimshottari Mahadasha timeline from birth date.

    The Vimshottari order is always:
        Ketu→Venus→Sun→Moon→Mars→Rahu→Jupiter→Saturn→Mercury (120 years)
    We start at the nakshatra lord of the birth Moon, with the first period
    being partial (balance at birth).  The sequence then wraps continuously —
    we simply step through i = 0 … 3×9−1 without any 'restart', because
    (start_i + i) % 9 already gives the correct planet for each step.

    Covers ~330 years (3 × 9 = 27 steps of up to 20 years each), which is
    more than enough for any national chart analysis.
    """
    _, _, idx    = _get_nakshatra(moon_long)
    portion_done = (moon_long % _NAK_LEN) / _NAK_LEN
    start_lord   = NAKSHATRA_LORDS[idx]
    lords        = list(DASA_DURATIONS.keys())
    start_i      = lords.index(start_lord)

    birth_dt = datetime.datetime.strptime(birth_date_str, "%Y-%m-%d")
    dashas: List[dict] = []
    current = birth_dt

    # 27 steps = 3 full cycles of 9 lords ≈ 300+ years
    for i in range(3 * len(lords)):
        j      = (start_i + i) % len(lords)
        planet = lords[j]
        full   = float(DASA_DURATIONS[planet])
        # Only the very first step is partial (balance of dasha at birth)
        years  = full * (1.0 - portion_done) if i == 0 else full
        end    = current + datetime.timedelta(days=years * 365.25)
        dashas.append({"planet": planet, "start": current, "end": end, "years": round(years, 2)})
        current = end

    return dashas


def _generate_bhuktis(dasha: dict) -> List[dict]:
    """
    Generate all 9 Bhukti sub-periods for a given Mahadasha dict.
    Returns list of {planet, start, end, years}.
    """
    lords   = list(DASA_DURATIONS.keys())
    m_lord  = dasha["planet"]
    m_years = dasha["years"]
    start_i = lords.index(m_lord)
    current = dasha["start"]
    bhuktis: List[dict] = []

    for i in range(len(lords)):
        b_lord  = lords[(start_i + i) % len(lords)]
        b_years = (DASA_DURATIONS[b_lord] / 120.0) * m_years
        end     = current + datetime.timedelta(days=b_years * 365.25)
        bhuktis.append({"planet": b_lord, "start": current, "end": end, "years": round(b_years, 3)})
        current = end

    return bhuktis


# ─── Public API ───────────────────────────────────────────────────────────────
def get_country_dasha(country: str,
                       current_dt: Optional[datetime.datetime] = None) -> dict:
    """
    Compute current Mahadasha + Bhukti for a country chart.

    Returns a structured dict:
    {
      country, notes, nakshatra, pada,
      mahadasha: {planet, start, end, years, focus, remaining},
      bhukti:    {planet, start, end, trigger, remaining_months},
      relationship: "Friend"|"Enemy"|"Neutral",
      upcoming_bhuktis: [{planet,start,end}, ...] (next 3),
      next_dashas:     [{planet,start,end,years}, ...] (next 5),
    }
    """
    if current_dt is None:
        current_dt = datetime.datetime.utcnow()

    bd = COUNTRY_BIRTH_DATA.get(country)
    if not bd:
        return {}

    moon_long  = bd["moon_long"]
    birth_date = bd["birth_date"]

    nak, pada, _ = _get_nakshatra(moon_long)
    dashas       = _generate_dashas(moon_long, birth_date)

    # ── Current Mahadasha ────────────────────────────────────────────────────
    cur_dasha = next(
        (d for d in dashas if d["start"] <= current_dt < d["end"]),
        dashas[-1]
    )

    # ── Current Bhukti ───────────────────────────────────────────────────────
    bhuktis   = _generate_bhuktis(cur_dasha)
    cur_bhukti = next(
        (b for b in bhuktis if b["start"] <= current_dt < b["end"]),
        bhuktis[-1]
    )

    # ── Upcoming bhuktis (next 3 after current) ───────────────────────────
    upcoming: List[dict] = []
    in_current = False
    for b in bhuktis:
        if in_current:
            upcoming.append(b)
            if len(upcoming) == 3:
                break
        if b is cur_bhukti:
            in_current = True

    # ── Next dashas (next 5 after current) ───────────────────────────────
    next_dashas: List[dict] = []
    in_cur_d = False
    for d in dashas:
        if in_cur_d:
            next_dashas.append(d)
            if len(next_dashas) == 5:
                break
        if d is cur_dasha:
            in_cur_d = True

    remaining_dasha_y = round((cur_dasha["end"] - current_dt).days / 365.25, 1)
    remaining_bhukti_m = round((cur_bhukti["end"] - current_dt).days / 30.44, 1)

    return {
        "country":      country,
        "notes":        bd["notes"],
        "nakshatra":    nak,
        "pada":         pada,
        "mahadasha": {
            "planet":    cur_dasha["planet"],
            "start":     cur_dasha["start"].strftime("%b %Y"),
            "end":       cur_dasha["end"].strftime("%b %Y"),
            "years":     cur_dasha["years"],
            "focus":     DASHA_FOCUS.get(cur_dasha["planet"], ""),
            "remaining": remaining_dasha_y,
        },
        "bhukti": {
            "planet":           cur_bhukti["planet"],
            "start":            cur_bhukti["start"].strftime("%b %Y"),
            "end":              cur_bhukti["end"].strftime("%b %Y"),
            "trigger":          BHUKTI_TRIGGER.get(cur_bhukti["planet"], ""),
            "remaining_months": remaining_bhukti_m,
        },
        "relationship":     get_relationship(cur_dasha["planet"], cur_bhukti["planet"]),
        "upcoming_bhuktis": [
            {
                "planet": b["planet"],
                "start":  b["start"].strftime("%b %Y"),
                "end":    b["end"].strftime("%b %Y"),
            }
            for b in upcoming
        ],
        "next_dashas": [
            {
                "planet": d["planet"],
                "start":  d["start"].strftime("%b %Y"),
                "end":    d["end"].strftime("%b %Y"),
                "years":  d["years"],
            }
            for d in next_dashas
        ],
    }


def get_dasha_risk_level(dasha_info: dict) -> str:
    """
    Classify dasha+bhukti combination as 'high', 'medium', or 'low' risk.
    Used for the Double Trigger alert logic.
    """
    if not dasha_info:
        return "medium"
    md = dasha_info.get("mahadasha", {}).get("planet", "")
    bh = dasha_info.get("bhukti",    {}).get("planet", "")
    if md in _MALEFICS and bh in _MALEFICS:
        return "high"
    if md in _MALEFICS or bh in _MALEFICS:
        return "medium"
    return "low"
