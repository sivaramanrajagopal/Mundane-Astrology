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

# ── Vimshottari Dasha constants ───────────────────────────────────────────────
# Standard 120-year cycle used in South Indian Vedic tradition.
VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}
_DASHA_SEQUENCE    = ["Ketu", "Venus", "Sun", "Moon", "Mars",
                      "Rahu", "Jupiter", "Saturn", "Mercury"]
_TOTAL_DASHA_YEARS = 120      # sum of all dasha years in one cycle
_DAYS_PER_YEAR     = 365.25   # Julian year (consistent with pyswisseph)


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

    Classical same-sign exception (BPHS / South Indian tradition):
      Combustion does NOT apply when the Sun and the planet are in different
      zodiac signs, even if the degree distance is within the orb.
      A sign boundary acts as a protective wall.

    Returns:
        combust      (bool):  True if combust in the same sign
        deep         (bool):  True if within 3° (deep/exact combustion)
        orb          (float): angular distance to Sun
        cross_sign   (bool):  True if in different signs (exception applies)
        would_combust(bool):  True if orb is within range but cross-sign exempts it
    """
    if planet_name == "Sun":
        return {"combust": False, "deep": False, "orb": 0.0,
                "cross_sign": False, "would_combust": False}

    orb = COMBUSTION_ORB.get(planet_name, 14.0)
    if planet_name == "Mercury" and is_retrograde:
        orb = 12.0

    dist = _angular_distance(sun_deg, planet_deg)

    # ── Same-sign exception ───────────────────────────────────────────────────
    # Combustion is only valid when Sun and planet share the same rasi.
    sun_sign    = int(sun_deg    / 30) % 12
    planet_sign = int(planet_deg / 30) % 12
    cross_sign  = (sun_sign != planet_sign)

    if cross_sign:
        return {
            "combust":       False,           # exception: different sign
            "deep":          False,
            "orb":           round(dist, 2),
            "cross_sign":    True,
            "would_combust": dist <= orb,     # informational: would be combust same-sign
        }

    return {
        "combust":       dist <= orb,
        "deep":          dist <= 3.0,
        "orb":           round(dist, 2),
        "cross_sign":    False,
        "would_combust": False,
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


# ── Nodal (Rahu/Ketu) states — most widely used South Indian system ───────────
# Rahu: exalted Taurus, debilitated Scorpio; Ketu: mirror
_NODAL_STATES = {
    "Rahu": {"exalted": "Rishaba",   "debilitated": "Vrischika"},
    "Ketu": {"exalted": "Vrischika", "debilitated": "Rishaba"},
}


def _get_nodal_state(node_name: str, rasi_tamil: str) -> str:
    """Return Exalted / Debilitated / Neutral for Rahu or Ketu."""
    s = _NODAL_STATES.get(node_name, {})
    if rasi_tamil == s.get("exalted"):
        return "Exalted"
    if rasi_tamil == s.get("debilitated"):
        return "Debilitated"
    return "Neutral"


# ── Display order for the comparison table ────────────────────────────────────
# Ascendant first (fixed point), then 7 planets, then shadow planets last.
ALL_DISPLAY_PLANETS = [
    "Ascendant",
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
]


# ── Vimshottari Dasha calculation ────────────────────────────────────────────

def calculate_vimshottari_dasha(moon_longitude: float,
                                 birth_utc: datetime.datetime) -> list:
    """
    Build the full Vimshottari Dasha timeline anchored to birth_utc.

    The Moon's nakshatra lord at birth determines the starting Maha Dasha.
    The fraction of the nakshatra already traversed tells us how much of
    that first Dasha had already elapsed at birth (the Dasha may have
    started before birth).

    Returns a list of 9 dicts — one per Maha Dasha from the TRUE start
    of the first period through the end of the 120-year cycle:
        {lord (str), start (datetime), end (datetime), years (float)}
    """
    nak_idx    = min(int((moon_longitude % 360) / _NAK_SPAN), 26)
    start_lord = NAKSHATRA_TO_LORD[NAKSHATRAS[nak_idx]]

    # Fraction of the birth nakshatra already elapsed → dasha fraction elapsed
    frac_elapsed = (moon_longitude % _NAK_SPAN) / _NAK_SPAN
    full_years   = VIMSHOTTARI_YEARS[start_lord]

    # The TRUE start of the first Maha Dasha (may be before birth)
    elapsed_days  = frac_elapsed * full_years * _DAYS_PER_YEAR
    true_start    = birth_utc - datetime.timedelta(days=elapsed_days)

    start_idx = _DASHA_SEQUENCE.index(start_lord)

    dashas = []
    cursor = true_start
    for i in range(9):
        lord  = _DASHA_SEQUENCE[(start_idx + i) % 9]
        years = VIMSHOTTARI_YEARS[lord]
        end   = cursor + datetime.timedelta(days=years * _DAYS_PER_YEAR)
        dashas.append({"lord": lord, "start": cursor, "end": end, "years": years})
        cursor = end

    return dashas


def _calculate_bhukti(maha: dict) -> list:
    """
    Calculate all 9 Bhukti (Antardasa) periods within a Maha Dasha.

    Proportions: Bhukti_years = (Maha_years × Bhukti_lord_years) / 120.
    The sequence starts from the Maha Dasha lord itself.
    Uses the TRUE start of the Maha Dasha so partial first periods are handled.

    Returns a list of 9 dicts: {lord, start, end, years}
    """
    maha_lord  = maha["lord"]
    maha_years = VIMSHOTTARI_YEARS[maha_lord]   # full period years (for ratio)
    start_idx  = _DASHA_SEQUENCE.index(maha_lord)

    bhukti_list = []
    cursor = maha["start"]
    for i in range(9):
        b_lord  = _DASHA_SEQUENCE[(start_idx + i) % 9]
        b_years = (maha_years * VIMSHOTTARI_YEARS[b_lord]) / _TOTAL_DASHA_YEARS
        b_end   = cursor + datetime.timedelta(days=b_years * _DAYS_PER_YEAR)
        bhukti_list.append({
            "lord":  b_lord,
            "start": cursor,
            "end":   b_end,
            "years": round(b_years, 4),
        })
        cursor = b_end
    return bhukti_list


def get_current_dasha_bhukti(dasha_list: list,
                               reference_dt: datetime.datetime = None) -> dict:
    """
    Return the active Maha Dasha and Bhukti for reference_dt (default: now UTC).

    Returns:
        {
          "maha":   {lord, start, end, years, days_remaining},
          "bhukti": {lord, start, end, years, days_remaining},
        }
    Returns None if reference_dt falls outside all computed periods.
    """
    if reference_dt is None:
        reference_dt = datetime.datetime.utcnow()

    # Find the Maha Dasha containing reference_dt
    maha = None
    for d in dasha_list:
        if d["start"] <= reference_dt <= d["end"]:
            maha = d
            break
    if maha is None:
        return None

    maha_result = {**maha, "days_remaining": max(0, (maha["end"] - reference_dt).days)}

    # Find the Bhukti within the Maha Dasha
    bhukti_list = _calculate_bhukti(maha)
    bhukti = next(
        (b for b in bhukti_list if b["start"] <= reference_dt <= b["end"]),
        bhukti_list[-1],    # edge case: floating-point rounding
    )
    bhukti_result = {**bhukti, "days_remaining": max(0, (bhukti["end"] - reference_dt).days)}

    return {"maha": maha_result, "bhukti": bhukti_result}


def scan_transit_affliction(planet_name: str,
                             reference_dt: datetime.datetime = None,
                             days_ahead: int = 365) -> dict:
    """
    Scan the next `days_ahead` days to find when the transit planet
    enters or exits a Combustion / Gandanta zone.

    Nodes (Rahu/Ketu): only Gandanta checked (no combustion).
    Scans day by day — ~365 SWE calls, runs in < 5 ms.

    Returns:
        currently_afflicted (bool)
        affliction_type     (str)   "Combust" | "Deep Combust" | "Gandanta" | "Clear"
        exits_in_days       (int)   days until current affliction ends (0 if clear)
        next_entry_days     (int)   days to next affliction after exit (None if none found)
        next_entry_date     (str)   "YYYY-MM-DD" of next entry (None if none found)
        next_entry_type     (str)   type of next affliction (None if none found)
    """
    if reference_dt is None:
        reference_dt = datetime.datetime.utcnow()

    is_node  = planet_name in ("Rahu", "Ketu")
    pid      = _PLANET_IDS.get(planet_name)     # None for Rahu/Ketu (handled separately)

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ref_jd = swe.julday(reference_dt.year, reference_dt.month, reference_dt.day,
                         reference_dt.hour + reference_dt.minute / 60.0)

    def _affliction_at(jd: float) -> str:
        """Return worst affliction type at Julian Day jd, or 'Clear'."""
        if planet_name == "Rahu":
            p_lon = swe.calc_ut(jd, swe.TRUE_NODE, _FLAGS)[0][0]
        elif planet_name == "Ketu":
            p_lon = (swe.calc_ut(jd, swe.TRUE_NODE, _FLAGS)[0][0] + 180.0) % 360.0
        else:
            p_xx  = swe.calc_ut(jd, pid, _FLAGS)[0]
            p_lon = p_xx[0]

        # Gandanta always takes priority (applies to all planets including nodes)
        if check_gandanta(p_lon)["gandanta"]:
            return "Gandanta"

        # Combustion — only for physical planets (not nodes, not Sun)
        if not is_node and planet_name != "Sun":
            sun_lon = swe.calc_ut(jd, swe.SUN, _FLAGS)[0][0]
            p_retro = swe.calc_ut(jd, pid, _FLAGS)[0][3] < 0
            c = check_combustion(sun_lon, p_lon, planet_name, p_retro)
            if c.get("deep"):
                return "Deep Combust"
            if c.get("combust"):
                return "Combust"

        return "Clear"

    current_aff = _affliction_at(ref_jd)
    currently_afflicted = current_aff != "Clear"

    if currently_afflicted:
        # Find when current affliction ends
        exits_in_days = days_ahead   # fallback: still active at horizon
        for d in range(1, days_ahead + 1):
            if _affliction_at(ref_jd + d) == "Clear":
                exits_in_days = d
                break

        # Find next entry after exit
        next_entry_days = next_entry_date = next_entry_type = None
        for d in range(exits_in_days + 1, days_ahead + 1):
            aff = _affliction_at(ref_jd + d)
            if aff != "Clear":
                next_entry_days = d
                next_entry_date = (reference_dt + datetime.timedelta(days=d)).strftime("%Y-%m-%d")
                next_entry_type = aff
                break

        return {
            "currently_afflicted": True,
            "affliction_type":     current_aff,
            "exits_in_days":       exits_in_days,
            "next_entry_days":     next_entry_days,
            "next_entry_date":     next_entry_date,
            "next_entry_type":     next_entry_type,
        }

    else:
        # Clear now — find next entry
        for d in range(1, days_ahead + 1):
            aff = _affliction_at(ref_jd + d)
            if aff != "Clear":
                return {
                    "currently_afflicted": False,
                    "affliction_type":     "Clear",
                    "exits_in_days":       0,
                    "next_entry_days":     d,
                    "next_entry_date":     (reference_dt + datetime.timedelta(days=d)).strftime("%Y-%m-%d"),
                    "next_entry_type":     aff,
                }
        return {
            "currently_afflicted": False,
            "affliction_type":     "Clear",
            "exits_in_days":       0,
            "next_entry_days":     None,
            "next_entry_date":     None,
            "next_entry_type":     None,
        }


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
    birth_date: "YYYY-MM-DD"   (strictly validated — raises ValueError on bad format)
    birth_time: "HH:MM"
    Returns a UTC datetime (naive, UTC).
    """
    # Parse strictly — raises ValueError propagated to caller for clean error messages
    local_dt = datetime.datetime.strptime(
        f"{birth_date.strip()} {birth_time.strip()}", "%Y-%m-%d %H:%M"
    )
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=lat, lng=lon) or "UTC"
        tz = pytz.timezone(tz_name)
        local_dt_aware = tz.localize(local_dt)
        return local_dt_aware.astimezone(pytz.utc).replace(tzinfo=None)
    except Exception:
        return local_dt   # fallback: treat birth time as UTC


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

    def __init__(self, birth_date: str, birth_time: str, lat: float, lon: float,
                 transit_date: str = None):
        """
        birth_date   : "YYYY-MM-DD"
        birth_time   : "HH:MM"  (24-hour, local time at birth location)
        lat, lon     : birth location coordinates (auto-detected or manual)
        transit_date : "YYYY-MM-DD" — date for transit comparison (default: today)
        """
        self.birth_date   = birth_date
        self.birth_time   = birth_time
        self.lat          = lat
        self.lon          = lon
        self.transit_date = transit_date   # None → use today in _calculate_transit

        swe.set_sid_mode(swe.SIDM_LAHIRI)

        # Store birth UTC for Dasha calculation (accessible by run_protection_analysis)
        self._birth_utc = local_to_utc(birth_date, birth_time, lat, lon)

        self.natal_data       = self._calculate_natal()
        self.transit_data     = self._calculate_transit()
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

        # ── Rahu (True Node) and Ketu (always 180° opposite) ──────────────────
        _NO_COMBUST = {"combust": False, "deep": False, "orb": 0.0, "na": True}
        rahu_xx   = swe.calc_ut(jd, swe.TRUE_NODE, _FLAGS)[0]
        rahu_lon  = rahu_xx[0]
        rahu_spd  = rahu_xx[3]
        ketu_lon  = (rahu_lon + 180.0) % 360.0

        for node_name, node_lon in (("Rahu", rahu_lon), ("Ketu", ketu_lon)):
            n_si   = int(node_lon / 30) % 12
            n_rasi = RASIS[n_si]
            n_sign = RASIS_ENGLISH[n_si]
            n_d9   = _get_navamsa_sign(node_lon)
            n_nak, n_pada, n_lord = _get_nakshatra_pada(node_lon)
            result[node_name] = {
                "longitude":      round(node_lon, 4),
                "deg_in_sign":    round(node_lon % 30, 2),
                "sign_index":     n_si,
                "rasi":           n_rasi,
                "sign":           n_sign,
                "navamsa_sign":   RASIS_ENGLISH[n_d9],
                "retrograde":     True,    # nodes are always retrograde
                "speed":          round(rahu_spd, 4),
                "state":          _get_nodal_state(node_name, n_rasi),
                "combust":        _NO_COMBUST,
                "gandanta":       check_gandanta(node_lon),
                "vargottama":     check_vargottama(node_lon),
                "nakshatra":      n_nak,
                "pada":           n_pada,
                "nakshatra_lord": n_lord,
                "is_node":        True,    # flag: skip combust display
            }

        # ── Ascendant (Lagna) ──────────────────────────────────────────────────
        # houses_ex returns tropical cusps; subtract Lahiri ayanamsa for sidereal.
        _, ascmc   = swe.houses_ex(jd, self.lat, self.lon, b'W')
        ayanamsa   = swe.get_ayanamsa_ut(jd)
        asc_lon    = (ascmc[0] - ayanamsa) % 360.0
        a_si       = int(asc_lon / 30) % 12
        a_rasi     = RASIS[a_si]
        a_sign     = RASIS_ENGLISH[a_si]
        a_nak, a_pada, a_lord = _get_nakshatra_pada(asc_lon)
        result["Ascendant"] = {
            "longitude":      round(asc_lon, 4),
            "deg_in_sign":    round(asc_lon % 30, 2),
            "sign_index":     a_si,
            "rasi":           a_rasi,
            "sign":           a_sign,
            "navamsa_sign":   "",
            "retrograde":     False,
            "speed":          0.0,
            "state":          "Lagna",
            "combust":        _NO_COMBUST,
            "gandanta":       check_gandanta(asc_lon),
            "vargottama":     False,
            "nakshatra":      a_nak,
            "pada":           a_pada,
            "nakshatra_lord": a_lord,
            "is_ascendant":   True,   # flag: no transit equivalent
        }

        return result

    # ── Transit calculation ───────────────────────────────────────────────────

    def _calculate_transit(self) -> dict:
        """
        Get transit planet positions for the selected date (or today if not set).
        Augments astrology_engine.get_transit_data() with combustion/gandanta checks.
        """
        if self.transit_date:
            # User-selected date — default to noon UTC for that day
            try:
                td = datetime.datetime.strptime(self.transit_date.strip(), "%Y-%m-%d")
                now_utc = td.replace(hour=12, minute=0, second=0)
            except ValueError:
                now_utc = datetime.datetime.utcnow()
        else:
            now_utc = datetime.datetime.utcnow()

        raw = get_transit_data(now_utc)

        # Sun longitude for combustion checks on the transit date
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd_now  = swe.julday(now_utc.year, now_utc.month, now_utc.day,
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

        # ── Transit Rahu/Ketu ──────────────────────────────────────────────────
        _NO_COMBUST = {"combust": False, "deep": False, "orb": 0.0, "na": True}
        rahu_xx  = swe.calc_ut(jd_now, swe.TRUE_NODE, _FLAGS)[0]
        rahu_lon = rahu_xx[0]
        ketu_lon = (rahu_lon + 180.0) % 360.0

        for node_name, node_lon in (("Rahu", rahu_lon), ("Ketu", ketu_lon)):
            n_si   = int(node_lon / 30) % 12
            n_rasi = RASIS[n_si]
            n_sign = RASIS_ENGLISH[n_si]
            n_nak, n_pada, n_lord = _get_nakshatra_pada(node_lon)
            result[node_name] = {
                "longitude":      round(node_lon, 4),
                "sign_index":     n_si,
                "sign":           n_sign,
                "retrograde":     True,
                "state":          _get_nodal_state(node_name, n_rasi),
                "combust":        _NO_COMBUST,
                "gandanta":       check_gandanta(node_lon),
                "nakshatra":      n_nak,
                "pada":           n_pada,
                "nakshatra_lord": n_lord,
                "is_node":        True,
            }

        # Ascendant is NOT included in transit — it changes every ~2 h and
        # has no meaningful comparison with a natal Lagna over time.

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
            if planet_name in ("Sun", "Ascendant"):
                continue          # Sun cannot be combust; Ascendant is a point not a planet
            c = data.get("combust", {})
            # Combustion only penalises physical planets (not nodes — they are shadow)
            if not data.get("is_node"):
                if c.get("deep"):
                    score -= 2
                elif c.get("combust"):
                    score -= 1
            if data.get("gandanta", {}).get("gandanta"):
                score -= 2        # gandanta applies to planets AND nodes
            if data.get("vargottama"):
                score += 2        # vargottama applies to planets AND nodes
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
            c = data["combust"]
            is_hidden = (c.get("deep") or c.get("combust")) and data.get("vargottama")
            if is_hidden:
                # Combust D1 + Vargottama D9 — the most important combined signal
                flags.append(
                    "🌟 HIDDEN STRENGTH — Combust D1 but Vargottama D9: "
                    "temporary surface struggle, inner D9 protection active; "
                    "setback precedes deep success"
                )
            else:
                if c.get("deep"):
                    flags.append(f"DEEP COMBUST ({c['orb']:.1f}°)")
                elif c.get("combust"):
                    flags.append(f"Combust ({c['orb']:.1f}°)")
                if data.get("vargottama"):
                    flags.append("Vargottama ✨")
        if data["gandanta"]["gandanta"]:
            g = data["gandanta"]
            g_label = f"Gandanta ({g['junction']}, {g['orb']:.1f}°)"
            # Note if Gandanta overrides the sign-wall on a cross-sign planet
            if data["combust"].get("cross_sign") and data["combust"].get("would_combust"):
                g_label += " [overrides sign-wall]"
            flags.append(g_label)
        flag_str = ", ".join(flags) if flags else "Clear"
        nak_str  = f"{data.get('nakshatra','?')} Pada {data.get('pada','?')} (lord: {data.get('nakshatra_lord','?')})"
        lines.append(
            f"  {planet}: {data['sign']} {data['deg_in_sign']:.1f}° "
            f"[{data['state']}] {'℞' if data['retrograde'] else ''} "
            f"| Nakshatra: {nak_str} — {flag_str}"
        )

    lines += ["", "## Live Transit Positions (today):"]
    for planet, data in transit.items():
        if data is None:          # e.g. Ascendant has no transit equivalent
            continue
        flags = []
        is_node = data.get("is_node", False)
        if planet != "Sun" and not is_node:
            if data["combust"]["deep"]:
                flags.append(f"DEEP COMBUST ({data['combust']['orb']:.1f}°)")
            elif data["combust"]["combust"]:
                flags.append(f"Combust ({data['combust']['orb']:.1f}°)")
        if data["gandanta"]["gandanta"]:
            flags.append(f"Gandanta ({data['gandanta']['junction']})")
        flag_str = ", ".join(flags) if flags else "Clear"
        nak_str  = f"{data.get('nakshatra','?')} Pada {data.get('pada','?')} (lord: {data.get('nakshatra_lord','?')})"
        lines.append(
            f"  {planet}: {data['sign']} [{data.get('state','—')}] "
            f"{'℞' if data.get('retrograde') else ''} "
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

    # All combust planets (including hidden-strength candidates)
    all_combust = [p for p, d in natal.items()
                   if p != "Sun" and d["combust"]["combust"]]

    # Hidden Strength: combust D1 + Vargottama D9 — separate special category
    hidden_strength_list = [
        p for p in all_combust
        if natal[p].get("vargottama")
    ]
    # Plain combust (no D9 protection)
    plain_combust_list = [p for p in all_combust if p not in hidden_strength_list]

    gandanta_list    = [p for p, d in natal.items() if d["gandanta"]["gandanta"]]
    vargottama_list  = [p for p, d in natal.items()
                        if d["vargottama"] and p not in hidden_strength_list]

    if hidden_strength_list:
        lines.append(
            f"- 🌟 **Hidden Strength** (combust D1 but Vargottama D9 — inner protection active): "
            f"{', '.join(hidden_strength_list)}. "
            f"These planets cause visible struggle but carry concealed success in the D9."
        )
    if plain_combust_list:
        lines.append(f"- **Combust planets** (weakened, no D9 relief): {', '.join(plain_combust_list)}")
    if gandanta_list:
        lines.append(f"- **Gandanta planets** (karmic knots — stability compromised): "
                     f"{', '.join(gandanta_list)}")
    if vargottama_list:
        lines.append(f"- **Vargottama planets** (amplified strength): {', '.join(vargottama_list)}")
    if not all_combust and not gandanta_list:
        lines.append("- No major natal afflictions detected. Protection score is solid.")
    lines.append(f"- Overall Protection Score: **{score}/10**")

    lines += ["\n## Live Transit Alerts\n"]
    transit_combust = [p for p, d in transit.items()
                       if d and p != "Sun" and not d.get("is_node") and d["combust"]["combust"]]
    transit_gandanta = [p for p, d in transit.items()
                        if d and d["gandanta"]["gandanta"]]
    if transit_combust:
        lines.append(f"- Transit planets currently combust: {', '.join(transit_combust)}")
    if transit_gandanta:
        lines.append(f"- Transit planets in Gandanta: {', '.join(transit_gandanta)}")
    if not transit_combust and not transit_gandanta:
        lines.append("- No major transit afflictions active today.")

    lines += ["\n## Action Windows\n",
              "- _Set OPENAI_API_KEY to get personalised action window recommendations._"]
    return "\n".join(lines)
