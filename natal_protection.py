"""
Natal Protection Analysis — AstrologyProtection class.

Calculates natal planet positions, checks combustion/gandanta/vargottama,
computes a 1-10 Protection Score, and generates an AI explanation comparing
natal states to live transit positions.
"""

import datetime
import os
import swisseph as swe
import pytz

from calculators.transit_calculator import (
    RASIS, RASIS_ENGLISH, PLANETARY_STATES,
    NAKSHATRAS, NAKSHATRA_TO_LORD,
)
from astrology_engine import get_transit_data, _EPHE_CANDIDATES

# ── Swiss Ephemeris path (reuse auto-detection from astrology_engine) ─────────
for _p in _EPHE_CANDIDATES:
    if _p and os.path.isdir(_p):
        swe.set_ephe_path(_p)
        break

_FLAGS = swe.FLG_SIDEREAL | swe.FLG_SPEED

# ── Planet IDs ────────────────────────────────────────────────────────────────
_PLANET_IDS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
}

NATAL_PLANETS = list(_PLANET_IDS.keys())

# ── Combustion orbs (Vedic standard, degrees) ─────────────────────────────────
# Sun itself cannot be combust; Mercury has tighter orb when retrograde.
COMBUSTION_ORB = {
    "Moon":    12.0,
    "Mars":    17.0,
    "Mercury": 14.0,   # 12° when retrograde
    "Jupiter": 11.0,
    "Venus":   10.0,
    "Saturn":  15.0,
}

# ── Gandanta junctions (degrees along ecliptic) ───────────────────────────────
# Water-Fire boundaries: Pisces/Aries (0°), Cancer/Leo (120°), Scorpio/Sagittarius (240°)
_GANDANTA_JUNCTIONS = [
    (0.0,   "Pisces/Aries"),
    (120.0, "Cancer/Leo"),
    (240.0, "Scorpio/Sagittarius"),
]
_GANDANTA_ORB = 10.0 / 3.0   # 3°20' = 3.333°

# ── Nakshatra / Pada constants ─────────────────────────────────────────────
_NAK_SPAN  = 360.0 / 27       # 13.333...° per nakshatra
_PADA_SPAN = _NAK_SPAN / 4    # 3.333...°  per pada (quarter)


def _get_nakshatra_pada(longitude: float) -> tuple:
    """
    Return (nakshatra_name, pada_1_to_4, nakshatra_lord) for a sidereal longitude.

    Each of the 27 nakshatras spans 13°20' (13.333°).
    Each nakshatra has 4 padas (quarters), each spanning 3°20' (3.333°).
    """
    nak_idx = min(int((longitude % 360) / _NAK_SPAN), 26)
    nak_name = NAKSHATRAS[nak_idx]
    pada = min(int((longitude % _NAK_SPAN) / _PADA_SPAN) + 1, 4)
    return nak_name, pada, NAKSHATRA_TO_LORD[nak_name]


def _angular_distance(a: float, b: float) -> float:
    """Shortest angular distance between two ecliptic longitudes (0-180°)."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


def check_combustion(sun_deg: float, planet_deg: float,
                     planet_name: str, is_retrograde: bool) -> dict:
    """
    Check if a planet is combust (too close to the Sun in Vedic terms).

    Returns:
        combust (bool): within combustion orb
        deep    (bool): within 3° (deep/exact combustion)
        orb     (float): angular distance to Sun
    """
    if planet_name == "Sun":
        return {"combust": False, "deep": False, "orb": 0.0}

    orb = COMBUSTION_ORB.get(planet_name, 14.0)
    if planet_name == "Mercury" and is_retrograde:
        orb = 12.0

    dist = _angular_distance(sun_deg, planet_deg)
    return {
        "combust": dist <= orb,
        "deep":    dist <= 3.0,
        "orb":     round(dist, 2),
    }


def check_gandanta(planet_deg: float) -> dict:
    """
    Check if a planet is in a Gandanta zone (last/first 3°20' of Water/Fire signs).

    Returns:
        gandanta  (bool): within ±3.333° of a Water-Fire junction
        junction  (str):  junction name, e.g. "Cancer/Leo"
        orb       (float): distance to nearest junction
    """
    lon = planet_deg % 360
    best_orb = 999.0
    best_jct = ""

    for jct_deg, jct_name in _GANDANTA_JUNCTIONS:
        # Handle Pisces/Aries wrap-around (0°/360°)
        dist = min(
            abs(lon - jct_deg),
            abs(lon - jct_deg + 360),
            abs(lon - jct_deg - 360),
        )
        if dist < best_orb:
            best_orb = dist
            best_jct = jct_name

    return {
        "gandanta": best_orb <= _GANDANTA_ORB,
        "junction": best_jct,
        "orb":      round(best_orb, 2),
    }


def _get_navamsa_sign(longitude: float) -> int:
    """
    Navamsa (D9) sign index for a given sidereal longitude.
    Formula: floor(longitude × 9 / 30) % 12
    """
    return int(longitude * 9 / 30) % 12


def check_vargottama(natal_longitude: float) -> bool:
    """
    A planet is Vargottama when its D1 (rasi) sign equals its D9 (navamsa) sign.
    Adds 2 points to the Protection Score — very auspicious.
    """
    d1_sign = int(natal_longitude / 30) % 12
    d9_sign = _get_navamsa_sign(natal_longitude)
    return d1_sign == d9_sign


def _get_planet_state(planet_name: str, rasi_tamil: str) -> str:
    """Return Exalted / Debilitated / Own / Neutral for a planet in a given rasi."""
    states = PLANETARY_STATES.get(planet_name, {})
    if rasi_tamil == states.get("exalted"):
        return "Exalted"
    if rasi_tamil == states.get("debilitated"):
        return "Debilitated"
    if rasi_tamil in states.get("own", []):
        return "Own Sign"
    return "Neutral"


# ── Geocoding & timezone helpers ─────────────────────────────────────────────

def geocode_place(place_name: str):
    """
    Convert a place name to (lat, lon, display_name) using Nominatim (free).
    Returns (None, None, error_message) on failure.
    """
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="mundane-astrology-app")
        location = geolocator.geocode(place_name, timeout=10)
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, f"Location '{place_name}' not found. Enter lat/lon manually."
    except ImportError:
        return None, None, "geopy not installed. Enter lat/lon manually."
    except Exception as exc:
        return None, None, f"Geocoding error: {exc}"


def _get_utc_offset_hours(lat: float, lon: float) -> float:
    """
    Get UTC offset in hours for a given (lat, lon) using timezonefinder + pytz.
    Falls back to 0.0 (UTC) if unavailable.
    """
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lon)
        if not tz_name:
            return 0.0
        tz = pytz.timezone(tz_name)
        # Use a reference datetime to get the offset (handles DST)
        ref = datetime.datetime.now(tz)
        return ref.utcoffset().total_seconds() / 3600.0
    except Exception:
        return 0.0


def local_to_utc(birth_date: str, birth_time: str, lat: float, lon: float) -> datetime.datetime:
    """
    Convert local birth date+time to UTC using the timezone auto-detected from lat/lon.
    birth_date: "YYYY-MM-DD"
    birth_time: "HH:MM"
    Returns a UTC datetime.
    """
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lon) or "UTC"
        tz = pytz.timezone(tz_name)
        year, month, day = [int(x) for x in birth_date.split("-")]
        hour, minute = [int(x) for x in birth_time.split(":")]
        local_dt = datetime.datetime(year, month, day, hour, minute)
        local_dt_aware = tz.localize(local_dt)
        return local_dt_aware.astimezone(pytz.utc).replace(tzinfo=None)
    except Exception:
        # Fallback: treat as UTC
        year, month, day = [int(x) for x in birth_date.split("-")]
        hour, minute = [int(x) for x in birth_time.split(":")]
        return datetime.datetime(year, month, day, hour, minute)


# ── Core AstrologyProtection class ───────────────────────────────────────────

class AstrologyProtection:
    """
    Computes Vedic protection indicators for a natal chart and compares
    them to live transit positions.

    Usage:
        ap = AstrologyProtection("1978-09-18", "17:35", 13.0827, 80.2707)
        natal  = ap.natal_data
        score  = ap.protection_score
        report = ap.get_protection_analysis()
    """

    def __init__(self, birth_date: str, birth_time: str, lat: float, lon: float):
        """
        birth_date : "YYYY-MM-DD"
        birth_time : "HH:MM"  (24-hour, local time at birth location)
        lat, lon   : birth location coordinates (auto-detected or manual)
        """
        self.birth_date = birth_date
        self.birth_time = birth_time
        self.lat = lat
        self.lon = lon

        swe.set_sid_mode(swe.SIDM_LAHIRI)

        self.natal_data   = self._calculate_natal()
        self.transit_data = self._calculate_transit()
        self.protection_score = self._calculate_protection_score()

    # ── Natal calculation ─────────────────────────────────────────────────────

    def _calculate_natal(self) -> dict:
        """
        Calculate natal planet positions for all 7 Vedic planets.
        Returns a dict keyed by planet name with full Vedic analysis.
        """
        utc_dt = local_to_utc(self.birth_date, self.birth_time, self.lat, self.lon)
        hour_dec = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_dec)

        # Get Sun longitude first (needed for combustion checks)
        sun_xx = swe.calc_ut(jd, swe.SUN, _FLAGS)[0]
        sun_lon = sun_xx[0]

        result = {}
        for planet_name, pid in _PLANET_IDS.items():
            xx = swe.calc_ut(jd, pid, _FLAGS)[0]
            lon_raw = xx[0]
            speed   = xx[3]
            retro   = speed < 0

            sign_index = int(lon_raw / 30) % 12
            rasi_tamil  = RASIS[sign_index]
            sign_eng    = RASIS_ENGLISH[sign_index]
            deg_in_sign = lon_raw % 30

            combust_info   = check_combustion(sun_lon, lon_raw, planet_name, retro)
            gandanta_info  = check_gandanta(lon_raw)
            is_vargottama  = check_vargottama(lon_raw)
            planet_state   = _get_planet_state(planet_name, rasi_tamil)
            navamsa_idx    = _get_navamsa_sign(lon_raw)
            nak_name, pada, nak_lord = _get_nakshatra_pada(lon_raw)

            result[planet_name] = {
                "longitude":       round(lon_raw, 4),
                "deg_in_sign":     round(deg_in_sign, 2),
                "sign_index":      sign_index,
                "rasi":            rasi_tamil,
                "sign":            sign_eng,
                "navamsa_sign":    RASIS_ENGLISH[navamsa_idx],
                "retrograde":      retro,
                "speed":           round(speed, 4),
                "state":           planet_state,
                "combust":         combust_info,
                "gandanta":        gandanta_info,
                "vargottama":      is_vargottama,
                "nakshatra":       nak_name,
                "pada":            pada,
                "nakshatra_lord":  nak_lord,
            }

        return result

    # ── Transit calculation ───────────────────────────────────────────────────

    def _calculate_transit(self) -> dict:
        """
        Get current (live) transit positions for the 7 natal planets.
        Augments astrology_engine.get_transit_data() with combustion/gandanta checks.
        """
        now_utc = datetime.datetime.utcnow()
        raw = get_transit_data(now_utc)

        # get live Sun longitude for combustion checks
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd_now = swe.julday(now_utc.year, now_utc.month, now_utc.day,
                            now_utc.hour + now_utc.minute / 60.0)
        sun_lon = swe.calc_ut(jd_now, swe.SUN, _FLAGS)[0][0]

        result = {}
        for planet_name in NATAL_PLANETS:
            data = raw.get(planet_name)
            if not data:
                continue
            lon_raw = data["longitude"]
            retro   = data["retrograde"]

            combust_info  = check_combustion(sun_lon, lon_raw, planet_name, retro)
            gandanta_info = check_gandanta(lon_raw)
            planet_state  = _get_planet_state(planet_name, RASIS[data["sign_index"]])
            nak_name, pada, nak_lord = _get_nakshatra_pada(lon_raw)

            result[planet_name] = {
                "longitude":      lon_raw,
                "sign_index":     data["sign_index"],
                "sign":           data["sign"],
                "retrograde":     retro,
                "state":          planet_state,
                "combust":        combust_info,
                "gandanta":       gandanta_info,
                "nakshatra":      nak_name,
                "pada":           pada,
                "nakshatra_lord": nak_lord,
            }

        return result

    # ── Protection Score ─────────────────────────────────────────────────────

    def _calculate_protection_score(self) -> int:
        """
        1-10 Protection Score based on natal planet states.
          -2  deep combustion (within 3°)
          -1  regular combustion
          -2  gandanta placement
          +2  vargottama (D1 = D9 sign)
        Baseline: 5
        """
        score = 5
        for planet_name, data in self.natal_data.items():
            if planet_name == "Sun":
                continue
            c = data["combust"]
            if c["deep"]:
                score -= 2
            elif c["combust"]:
                score -= 1
            if data["gandanta"]["gandanta"]:
                score -= 2
            if data["vargottama"]:
                score += 2
        return max(1, min(10, score))

    # ── AI Analysis ──────────────────────────────────────────────────────────

    def get_protection_analysis(self, openai_api_key: str = "") -> str:
        """
        Generate an AI explanation covering natal protection states,
        live transit alerts, and action windows.

        Returns Markdown text with sections:
          ## Natal Analysis
          ## Live Transit Alerts
          ## Action Windows
        """
        if not openai_api_key:
            return _build_fallback_analysis(self.natal_data, self.transit_data,
                                            self.protection_score)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            prompt = _build_protection_prompt(self.natal_data, self.transit_data,
                                              self.protection_score,
                                              self.birth_date, self.birth_time,
                                              self.lat, self.lon)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1800,
            )
            return response.choices[0].message.content
        except Exception as exc:
            return (f"_AI analysis unavailable: {exc}_\n\n"
                    + _build_fallback_analysis(self.natal_data, self.transit_data,
                                               self.protection_score))


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_protection_prompt(natal: dict, transit: dict, score: int,
                              birth_date: str, birth_time: str,
                              lat: float, lon: float) -> str:
    lines = [
        "Act as a Vedic astrology expert specializing in planetary protection and transit analysis.",
        f"Birth: {birth_date} {birth_time}, lat={lat:.2f}, lon={lon:.2f}",
        f"Overall Protection Score: {score}/10",
        "",
        "## Natal Planet Analysis:",
    ]
    for planet, data in natal.items():
        flags = []
        if planet != "Sun":
            if data["combust"]["deep"]:
                flags.append(f"DEEP COMBUST ({data['combust']['orb']:.1f}°)")
            elif data["combust"]["combust"]:
                flags.append(f"Combust ({data['combust']['orb']:.1f}°)")
        if data["gandanta"]["gandanta"]:
            flags.append(f"Gandanta ({data['gandanta']['junction']}, {data['gandanta']['orb']:.1f}°)")
        if data["vargottama"]:
            flags.append("Vargottama ✨")
        flag_str = ", ".join(flags) if flags else "Clear"
        nak_str  = f"{data.get('nakshatra','?')} Pada {data.get('pada','?')} (lord: {data.get('nakshatra_lord','?')})"
        lines.append(
            f"  {planet}: {data['sign']} {data['deg_in_sign']:.1f}° "
            f"[{data['state']}] {'℞' if data['retrograde'] else ''} "
            f"| Nakshatra: {nak_str} — {flag_str}"
        )

    lines += ["", "## Live Transit Positions (today):"]
    for planet, data in transit.items():
        flags = []
        if planet != "Sun":
            if data["combust"]["deep"]:
                flags.append(f"DEEP COMBUST ({data['combust']['orb']:.1f}°)")
            elif data["combust"]["combust"]:
                flags.append(f"Combust ({data['combust']['orb']:.1f}°)")
        if data["gandanta"]["gandanta"]:
            flags.append(f"Gandanta ({data['gandanta']['junction']})")
        flag_str = ", ".join(flags) if flags else "Clear"
        nak_str  = f"{data.get('nakshatra','?')} Pada {data.get('pada','?')} (lord: {data.get('nakshatra_lord','?')})"
        lines.append(
            f"  {planet}: {data['sign']} [{data['state']}] "
            f"{'℞' if data['retrograde'] else ''} "
            f"| Nakshatra: {nak_str} — {flag_str}"
        )

    lines += [
        "",
        "Instructions:",
        "1. Write ## Natal Analysis — explain the natal protection score. "
        "Highlight which planets are weakened (combust/gandanta) and which are empowered (vargottama). "
        "Explain the life domains affected using Vedic house significations.",
        "2. Write ## Live Transit Alerts — identify where current transits are "
        "triggering or releasing natal weak points. Flag any transit planet "
        "just exiting combustion (Udayam/rising window) as an ACTION opportunity.",
        "3. Write ## Action Windows — give 2-3 specific, practical action windows "
        "the native should use right now based on transit + natal interaction. "
        "For example: 'Venus is emerging from combustion in transit — "
        "this is a 15-day window to finalize financial decisions or luxury purchases.'",
        "Keep each section to 3-5 concise bullet points. Use plain, empathetic language.",
    ]
    return "\n".join(lines)


def _build_fallback_analysis(natal: dict, transit: dict, score: int) -> str:
    """Rule-based fallback when no OpenAI key is set."""
    lines = ["## Natal Analysis\n"]
    combust_list = [p for p, d in natal.items()
                    if p != "Sun" and d["combust"]["combust"]]
    gandanta_list = [p for p, d in natal.items() if d["gandanta"]["gandanta"]]
    vargottama_list = [p for p, d in natal.items() if d["vargottama"]]

    if combust_list:
        lines.append(f"- **Combust planets** (weakened): {', '.join(combust_list)}")
    if gandanta_list:
        lines.append(f"- **Gandanta planets** (karmic knots): {', '.join(gandanta_list)}")
    if vargottama_list:
        lines.append(f"- **Vargottama planets** (amplified strength): {', '.join(vargottama_list)}")
    if not combust_list and not gandanta_list:
        lines.append("- No major natal afflictions detected. Protection score is solid.")
    lines.append(f"- Overall Protection Score: **{score}/10**")

    lines += ["\n## Live Transit Alerts\n"]
    transit_combust = [p for p, d in transit.items()
                       if p != "Sun" and d["combust"]["combust"]]
    transit_gandanta = [p for p, d in transit.items() if d["gandanta"]["gandanta"]]
    if transit_combust:
        lines.append(f"- Transit planets currently combust: {', '.join(transit_combust)}")
    if transit_gandanta:
        lines.append(f"- Transit planets in Gandanta: {', '.join(transit_gandanta)}")
    if not transit_combust and not transit_gandanta:
        lines.append("- No major transit afflictions active today.")

    lines += ["\n## Action Windows\n",
              "- _Set OPENAI_API_KEY to get personalised action window recommendations._"]
    return "\n".join(lines)
