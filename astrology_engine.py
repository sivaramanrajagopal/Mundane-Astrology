"""
Astrology Engine — Mundane Astrology adapter layer.
Wraps the Ashtavargam transit_calculator for country-level (mundane) analysis.
"""

import datetime
import os
import swisseph as swe
import pytz

from calculators.transit_calculator import get_planet_positions, RASIS_ENGLISH, RASIS

# ── Swiss Ephemeris path ───────────────────────────────────────────────────────
# Priority order:
#  1. SWE_EPHE_PATH env var (explicit override)
#  2. /app/ephe  — Docker / HF Spaces (files downloaded at build time)
#  3. JH local   — Jagannatha Hora files already on this Mac via CrossOver
#  4. node ephe  — swisseph npm package in sibling project
# Falls back to Moshier if none found (still works, ~1-2 arcmin less precise).
_EPHE_CANDIDATES = [
    os.environ.get("SWE_EPHE_PATH", ""),
    "/app/ephe",
    os.path.expanduser(
        "~/Library/Application Support/CrossOver/Bottles/JH"
        "/drive_c/Program Files (x86)/Jagannatha Hora/jhcore/ephe"
    ),
    os.path.expanduser(
        "~/Documents/Astrology-Projects/Basic-AI-Astro"
        "/ai-astro-app/node_modules/swisseph/ephe"
    ),
]
for _p in _EPHE_CANDIDATES:
    if _p and os.path.isdir(_p):
        swe.set_ephe_path(_p)
        break

# ---------------------------------------------------------------------------
# Country natal Lagnas — 0-based index into RASIS_ENGLISH (Aries=0…Pisces=11)
# ---------------------------------------------------------------------------
COUNTRY_LAGNAS = {
    "India": 1,    # Taurus / Rishaba
    "USA":   8,    # Sagittarius / Dhanus
    "China": 10,   # Aquarius / Kumbha
    "EU":    9,    # Capricorn / Makara
}

# Vedic planets to include — filter out Uranus, Neptune, Pluto, Ascendant
VEDIC_PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Rahu", "Ketu"
]

# swisseph planet IDs for direct calculations
_SWE_IDS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus":   swe.VENUS,
    "Mars":    swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn":  swe.SATURN,
    "Rahu":    swe.TRUE_NODE,
}
_SWE_FLAGS = swe.FLG_SIDEREAL | swe.FLG_SPEED

# ---------------------------------------------------------------------------
# Hardcoded Natal Charts for each country
# Source: traditional Vedic mundane charts (independence/founding dates)
# ---------------------------------------------------------------------------
NATAL_CHARTS = {
    "India": {
        "event": "Independence — 15 Aug 1947, 00:00 IST, New Delhi",
        "planets": {
            "Sun":     {"sign": "Cancer",      "sign_index": 3},
            "Moon":    {"sign": "Capricorn",   "sign_index": 9},
            "Mercury": {"sign": "Cancer",      "sign_index": 3},
            "Venus":   {"sign": "Gemini",      "sign_index": 2},
            "Mars":    {"sign": "Cancer",      "sign_index": 3},
            "Jupiter": {"sign": "Scorpio",     "sign_index": 7},
            "Saturn":  {"sign": "Cancer",      "sign_index": 3},
            "Rahu":    {"sign": "Taurus",      "sign_index": 1},
            "Ketu":    {"sign": "Scorpio",     "sign_index": 7},
        },
    },
    "USA": {
        "event": "Declaration of Independence — 4 Jul 1776, Philadelphia",
        "planets": {
            "Sun":     {"sign": "Gemini",      "sign_index": 2},
            "Moon":    {"sign": "Aquarius",    "sign_index": 10},
            "Mercury": {"sign": "Cancer",      "sign_index": 3},
            "Venus":   {"sign": "Cancer",      "sign_index": 3},
            "Mars":    {"sign": "Gemini",      "sign_index": 2},
            "Jupiter": {"sign": "Cancer",      "sign_index": 3},
            "Saturn":  {"sign": "Libra",       "sign_index": 6},
            "Rahu":    {"sign": "Leo",         "sign_index": 4},
            "Ketu":    {"sign": "Aquarius",    "sign_index": 10},
        },
    },
    "China": {
        "event": "PRC Founding — 1 Oct 1949, 15:01 CST, Beijing",
        "planets": {
            "Sun":     {"sign": "Virgo",       "sign_index": 5},
            "Moon":    {"sign": "Libra",       "sign_index": 6},
            "Mercury": {"sign": "Libra",       "sign_index": 6},
            "Venus":   {"sign": "Scorpio",     "sign_index": 7},
            "Mars":    {"sign": "Scorpio",     "sign_index": 7},
            "Jupiter": {"sign": "Capricorn",   "sign_index": 9},
            "Saturn":  {"sign": "Virgo",       "sign_index": 5},
            "Rahu":    {"sign": "Aries",       "sign_index": 0},
            "Ketu":    {"sign": "Libra",       "sign_index": 6},
        },
    },
    "EU": {
        "event": "Maastricht Treaty — 1 Nov 1993, Brussels",
        "planets": {
            "Sun":     {"sign": "Libra",       "sign_index": 6},
            "Moon":    {"sign": "Leo",         "sign_index": 4},
            "Mercury": {"sign": "Scorpio",     "sign_index": 7},
            "Venus":   {"sign": "Sagittarius", "sign_index": 8},
            "Mars":    {"sign": "Scorpio",     "sign_index": 7},
            "Jupiter": {"sign": "Libra",       "sign_index": 6},
            "Saturn":  {"sign": "Aquarius",    "sign_index": 10},
            "Rahu":    {"sign": "Sagittarius", "sign_index": 8},
            "Ketu":    {"sign": "Gemini",      "sign_index": 2},
        },
    },
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def _datetime_to_jd(dt: datetime.datetime) -> float:
    """Convert a datetime object (UTC or naive) to Julian Day number."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(pytz.utc).replace(tzinfo=None)
    hour_dec = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    return swe.julday(dt.year, dt.month, dt.day, hour_dec)


def _jd_to_datetime(jd: float) -> datetime.datetime:
    """Convert Julian Day to a UTC datetime."""
    year, month, day, hour_dec = swe.revjul(jd)
    hour  = int(hour_dec)
    minute = int((hour_dec - hour) * 60)
    return datetime.datetime(year, month, day, hour, minute)


def _sign_of(jd: float, planet_name: str) -> int:
    """Return 0-based sign index (Aries=0) for a planet at a given JD."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    pid = _SWE_IDS[planet_name]
    xx  = swe.calc_ut(jd, pid, _SWE_FLAGS)[0]
    return int(xx[0] / 30) % 12


def _speed_of(jd: float, planet_name: str) -> float:
    """Return speed (°/day) of a planet at given JD."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    pid = _SWE_IDS[planet_name]
    xx  = swe.calc_ut(jd, pid, _SWE_FLAGS)[0]
    return xx[3]


# ---------------------------------------------------------------------------
# Main transit data function
# ---------------------------------------------------------------------------
def get_transit_data(datetime_obj: datetime.datetime) -> dict:
    """
    Calculate current planetary positions for the given UTC datetime.
    Returns dict of 9 Vedic planets with sign, nakshatra, pada, retrograde, speed.
    """
    jd = _datetime_to_jd(datetime_obj)
    planet_dict, _, _ = get_planet_positions(jd, 0.0, 0.0)

    result = {}
    for planet in VEDIC_PLANETS:
        if planet not in planet_dict:
            continue
        data     = planet_dict[planet]
        sign_name = data["rasi"]
        tamil_idx = RASIS.index(sign_name) if sign_name in RASIS else 0

        result[planet] = {
            "longitude":  round(data["longitude"], 4),
            "rasi":       sign_name,
            "sign":       RASIS_ENGLISH[tamil_idx],
            "sign_index": tamil_idx,
            "nakshatra":  data["nakshatra"],
            "pada":       data["pada"],
            "retrograde": bool(data.get("retrograde", False)),
            "speed":      round(data.get("speed", 0.0), 4) if "speed" in data else None,
        }
    return result


# ---------------------------------------------------------------------------
# House position helpers
# ---------------------------------------------------------------------------
def get_house_positions(transit_data: dict, country: str) -> dict:
    lagna = COUNTRY_LAGNAS[country]
    return {
        planet: ((data["sign_index"] - lagna) % 12) + 1
        for planet, data in transit_data.items()
    }


def get_all_house_positions(transit_data: dict) -> dict:
    return {c: get_house_positions(transit_data, c) for c in COUNTRY_LAGNAS}


def get_lagna_sign(country: str) -> str:
    return RASIS_ENGLISH[COUNTRY_LAGNAS[country]]


# ---------------------------------------------------------------------------
# Natal Chart
# ---------------------------------------------------------------------------
def get_natal_chart(country: str) -> dict:
    """
    Return natal planet positions with house numbers calculated from lagna.
    {planet: {sign, sign_index, house, event}}
    """
    chart = NATAL_CHARTS.get(country, {})
    lagna = COUNTRY_LAGNAS.get(country, 0)
    result = {
        "_event": chart.get("event", "Unknown"),
        "_lagna": get_lagna_sign(country),
    }
    for planet, data in chart.get("planets", {}).items():
        house = ((data["sign_index"] - lagna) % 12) + 1
        result[planet] = {
            "sign":       data["sign"],
            "sign_index": data["sign_index"],
            "house":      house,
        }
    return result


# ---------------------------------------------------------------------------
# Planet Ingress Countdown
# ---------------------------------------------------------------------------
# Scan step per planet (days) — faster-moving planets need finer steps
_INGRESS_STEP = {
    "Moon":    0.10,
    "Sun":     0.50,
    "Mercury": 0.25,
    "Venus":   0.25,
    "Mars":    1.00,
    "Jupiter": 1.00,
    "Saturn":  1.00,
    "Rahu":    1.00,
}


def get_next_ingresses(datetime_obj: datetime.datetime,
                       max_days: int = 90, top_n: int = 6) -> list:
    """
    Scan forward to find the next sign change for each Vedic planet.
    Returns a list of dicts sorted by days_away, limited to top_n.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_start  = _datetime_to_jd(datetime_obj)
    ingresses = []

    for planet_name, step in _INGRESS_STEP.items():
        current_sign = _sign_of(jd_start, planet_name)
        max_steps    = int(max_days / step)
        found = False
        for i in range(1, max_steps):
            jd_check  = jd_start + i * step
            new_sign  = _sign_of(jd_check, planet_name)
            if new_sign != current_sign:
                days_away  = round(i * step)
                ingress_dt = datetime_obj + datetime.timedelta(days=i * step)
                # House impact per country
                house_str = "  ".join(
                    f"{c[0]}: H{((new_sign - COUNTRY_LAGNAS[c]) % 12) + 1}"
                    for c in COUNTRY_LAGNAS
                )
                ingresses.append({
                    "planet":     planet_name,
                    "from_sign":  RASIS_ENGLISH[current_sign],
                    "to_sign":    RASIS_ENGLISH[new_sign],
                    "days_away":  days_away,
                    "date":       ingress_dt.strftime("%d %b %Y"),
                    "house_impact": house_str,
                })
                found = True
                break

        # Add Ketu (always opposite Rahu)
        if planet_name == "Rahu" and found:
            rahu_entry = ingresses[-1]
            ketu_from  = (RASIS_ENGLISH.index(rahu_entry["from_sign"]) + 6) % 12
            ketu_to    = (RASIS_ENGLISH.index(rahu_entry["to_sign"])   + 6) % 12
            house_str  = "  ".join(
                f"{c[0]}: H{((ketu_to - COUNTRY_LAGNAS[c]) % 12) + 1}"
                for c in COUNTRY_LAGNAS
            )
            ingresses.append({
                "planet":       "Ketu",
                "from_sign":    RASIS_ENGLISH[ketu_from],
                "to_sign":      RASIS_ENGLISH[ketu_to],
                "days_away":    rahu_entry["days_away"],
                "date":         rahu_entry["date"],
                "house_impact": house_str,
            })

    ingresses.sort(key=lambda x: x["days_away"])
    return ingresses[:top_n]


# ---------------------------------------------------------------------------
# Retrograde Status
# ---------------------------------------------------------------------------
_RETRO_PLANETS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"]


def get_retrograde_status(transit_data: dict,
                           datetime_obj: datetime.datetime) -> dict:
    """
    Returns:
      currently_retrograde: list of planet names currently Rx
      upcoming_stations:    list of {planet, event, days_away, date} — next Rx/Direct change
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_start = _datetime_to_jd(datetime_obj)

    currently_retrograde = [
        p for p in VEDIC_PLANETS
        if transit_data.get(p, {}).get("retrograde", False)
    ]

    upcoming_stations = []
    for planet_name in _RETRO_PLANETS:
        current_retro = _speed_of(jd_start, planet_name) < 0
        for day in range(1, 181):
            jd_check  = jd_start + day
            new_retro = _speed_of(jd_check, planet_name) < 0
            if new_retro != current_retro:
                station_dt = datetime_obj + datetime.timedelta(days=day)
                upcoming_stations.append({
                    "planet":     planet_name,
                    "event":      "goes Retrograde ℞" if new_retro else "goes Direct ➡",
                    "days_away":  day,
                    "date":       station_dt.strftime("%d %b %Y"),
                })
                break

    upcoming_stations.sort(key=lambda x: x["days_away"])
    return {
        "currently_retrograde": currently_retrograde,
        "upcoming_stations":    upcoming_stations[:5],
    }


# ---------------------------------------------------------------------------
# Lunation & Eclipse Alerts
# ---------------------------------------------------------------------------
def get_next_lunations(datetime_obj: datetime.datetime, count: int = 4) -> list:
    """
    Scan forward (0.1-day steps) to find next New Moons, Full Moons, and Eclipses.
    Eclipse flag: lunation within 15° of Rahu/Ketu axis.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_start = _datetime_to_jd(datetime_obj)
    events   = []

    # Compute initial elongation (Moon longitude − Sun longitude)
    def _elongation(jd):
        sun  = swe.calc_ut(jd, swe.SUN,  _SWE_FLAGS)[0][0]
        moon = swe.calc_ut(jd, swe.MOON, _SWE_FLAGS)[0][0]
        return (moon - sun) % 360

    def _near_node(jd, moon_lon):
        rahu = swe.calc_ut(jd, swe.TRUE_NODE, _SWE_FLAGS)[0][0]
        ketu = (rahu + 180) % 360
        return min(
            abs(moon_lon - rahu) % 360,
            abs(moon_lon - ketu) % 360,
        ) < 15

    prev_elong = _elongation(jd_start)
    step       = 0.1   # 2.4-hour steps

    max_steps = int(count * 30 / step)
    for i in range(1, max_steps):
        if len(events) >= count:
            break
        jd_check   = jd_start + i * step
        elong      = _elongation(jd_check)
        moon_lon   = swe.calc_ut(jd_check, swe.MOON, _SWE_FLAGS)[0][0]
        moon_sign  = int(moon_lon / 30) % 12

        # New Moon: elongation wraps through 0° (prev >350, now <15)
        if prev_elong > 350 and elong < 15:
            eclipse   = _near_node(jd_check, moon_lon)
            event_dt  = datetime_obj + datetime.timedelta(days=i * step)
            event_type = "🌑 Solar Eclipse" if eclipse else "🌑 New Moon"
            house_str = "  ".join(
                f"{c[0]}: H{((moon_sign - COUNTRY_LAGNAS[c]) % 12) + 1}"
                for c in COUNTRY_LAGNAS
            )
            events.append({
                "type":         event_type,
                "sign":         RASIS_ENGLISH[moon_sign],
                "days_away":    round(i * step),
                "date":         event_dt.strftime("%d %b %Y"),
                "house_impact": house_str,
                "is_eclipse":   eclipse,
            })

        # Full Moon: elongation crosses 180° (prev <175, now >175 and <195)
        elif prev_elong < 175 and 175 <= elong <= 195:
            eclipse   = _near_node(jd_check, moon_lon)
            event_dt  = datetime_obj + datetime.timedelta(days=i * step)
            event_type = "🌕 Lunar Eclipse" if eclipse else "🌕 Full Moon"
            house_str = "  ".join(
                f"{c[0]}: H{((moon_sign - COUNTRY_LAGNAS[c]) % 12) + 1}"
                for c in COUNTRY_LAGNAS
            )
            events.append({
                "type":         event_type,
                "sign":         RASIS_ENGLISH[moon_sign],
                "days_away":    round(i * step),
                "date":         event_dt.strftime("%d %b %Y"),
                "house_impact": house_str,
                "is_eclipse":   eclipse,
            })

        prev_elong = elong

    return events
