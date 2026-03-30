"""
obstruction_dosha.py — Tamil/Sanskrit Obstruction Dosha Engine

Implements the classical "karmic road blocked?" layer that complements
Tab 7's natal-strength analysis:

  1. Thithi Soonya     — Void (empty) signs for the birth Tithi
  2. Vadhai / Vainasikam — 7th & 22nd Nakshatras from Janma Moon (Red Zones)
  3. Chandrashtama     — 8th sign from natal Moon; transit Moon here = stress
  4. Mudakku Rasi      — 22nd Drekkana (Khara) from Lagna = blocked sign
  5. Critical Obstruction — (Deep Combust / Gandanta) + Soonya Rasi
  6. Divine Protection  — Pushkara Navamsa neutralises the above

All calculations use Swiss Ephemeris with Lahiri ayanamsa.
"""

from __future__ import annotations

import datetime
import math
import os

import swisseph as swe

# ── Reuse utilities from natal_protection (already sets up SWE path) ─────────
from natal_protection import (
    _FLAGS,
    _NAK_SPAN,
    NATAL_PLANETS,
    NAKSHATRAS,
    NAKSHATRA_TO_LORD,
    _get_nakshatra_pada,
    check_combustion,
    check_gandanta,
    check_pushkara,
    geocode_place,
    local_to_utc,
)
from calculators.transit_calculator import RASIS, RASIS_ENGLISH
from astrology_engine import _EPHE_CANDIDATES

# Re-ensure ephemeris path and sidereal mode (idempotent)
for _p in _EPHE_CANDIDATES:
    if os.path.isdir(_p):
        swe.set_ephe_path(_p)
        break
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ── SWE planet IDs ─────────────────────────────────────────────────────────────
_PLANET_IDS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
}
_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# ── Tithi → Soonya Rasi mapping (0-based sign indices) ────────────────────────
# Source: Classical Tamil Jyotish / Daghda Rasi tradition.
# Soonya = "void/empty" sign for that Tithi — planets here deliver weakened results.
TITHI_SOONYA_MAP: dict[int, list[int]] = {
    0:  [6, 9],          # Pratipada   → Thula (7), Makara (10)
    1:  [8, 11],         # Dwitiya     → Dhanus (9), Meena (12)
    2:  [2, 5],          # Tritiya     → Mithuna (3), Kanya (6)
    3:  [7, 5],          # Chaturthi   → Vrishchika (8), Kanya (6)
    4:  [2, 5],          # Panchami    → Mithuna (3), Kanya (6)
    5:  [4, 11],         # Shasti      → Simha (5), Meena (12)
    6:  [2, 5],          # Saptami     → Mithuna (3), Kanya (6)
    7:  [2, 5],          # Ashtami     → Mithuna (3), Kanya (6)
    8:  [4, 7],          # Navami      → Simha (5), Vrishchika (8)
    9:  [4, 7],          # Dashami     → Simha (5), Vrishchika (8)
    10: [8, 11],         # Ekadashi    → Dhanus (9), Meena (12)
    11: [6, 9],          # Dwadashi    → Thula (7), Makara (10)
    12: [7, 5],          # Trayodashi  → Vrishchika (8), Kanya (6)
    13: [2, 5, 8, 11],   # Chaturdashi → all dual signs (3,6,9,12)
    14: [],              # Purnima / Amavasya → no soonya rasis
}

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shasti", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya",
]

# ── No-dosha sentinel (matches check_critical_obstruction schema) ──────────────
_NO_DOSHA = {
    "critical": False, "mild": False, "severity": "none",
    "has_divine_protection": False, "in_soonya": False, "visha_gati_note": "",
}


# ═════════════════════════════════════════════════════════════════════════════
# Core Vedic Calculation Functions
# ═════════════════════════════════════════════════════════════════════════════

def get_tithi(moon_lon: float, sun_lon: float) -> tuple[int, str, str]:
    """
    Return (tithi_index 0-14, tithi_name, paksha).
    tithi_index wraps across the 30-tithi cycle into the 15-tithi Soonya map.
    """
    angle_diff = (moon_lon - sun_lon) % 360
    tithi_number = math.ceil(angle_diff / 12.0)  # 1–30
    if tithi_number == 0:
        tithi_number = 30
    paksha = "Shukla" if tithi_number <= 15 else "Krishna"
    tithi_idx = (tithi_number - 1) % 15          # 0–14 for Soonya lookup
    return tithi_idx, TITHI_NAMES[tithi_idx], paksha


def get_soonya_rasis(tithi_index: int) -> list[int]:
    """Return list of soonya rasi sign indices (0-based) for the given tithi."""
    return TITHI_SOONYA_MAP.get(tithi_index, [])


def get_vadhai_vainasikam(janma_nak_idx: int) -> dict:
    """
    Return Vadhai (7th) and Vainasikam (22nd) nakshatra from natal Moon nakshatra.
    Both are classical "Red Zone" nakshatras — malefic transits here bring danger.
    """
    vadhai_idx      = (janma_nak_idx + 6)  % 27   # 7th  = index + 6
    vainasikam_idx  = (janma_nak_idx + 21) % 27   # 22nd = index + 21
    return {
        "vadhai_idx":       vadhai_idx,
        "vadhai_name":      NAKSHATRAS[vadhai_idx],
        "vainasikam_idx":   vainasikam_idx,
        "vainasikam_name":  NAKSHATRAS[vainasikam_idx],
    }


def get_chandrashtama_sign(natal_moon_sign_idx: int) -> int:
    """8th sign from natal Moon (0-based). Transit Moon here = Chandrashtama."""
    return (natal_moon_sign_idx + 7) % 12


def get_mudakku_rasi(lagna_longitude: float) -> dict:
    """
    22nd Drekkana (Khara) from the Ascendant = Mudakku (blocked) Rasi.
    Each sign is split into 3 Drekkanas of 10° each; there are 36 total.
    Count forward 21 positions from the Lagna's Drekkana position.
    """
    lagna_sign     = int(lagna_longitude / 30) % 12
    lagna_deg      = lagna_longitude % 30
    lagna_drek     = int(lagna_deg / 10)         # 0, 1, 2

    total_drek     = (lagna_sign * 3) + lagna_drek   # 0–35
    khara_pos      = (total_drek + 21) % 36           # 22nd = +21

    sign_idx       = khara_pos // 3
    drek_within    = khara_pos % 3                    # 0→0-10°, 1→10-20°, 2→20-30°
    degree_lo      = drek_within * 10
    degree_hi      = degree_lo + 10

    return {
        "sign_idx":     sign_idx,
        "sign_name":    RASIS[sign_idx],
        "sign_english": RASIS_ENGLISH[sign_idx],
        "degree_lo":    degree_lo,
        "degree_hi":    degree_hi,
        "drekkana_num": drek_within + 1,
    }


def check_critical_obstruction(planet_data: dict, soonya_rasis: list[int]) -> dict:
    """
    Evaluate the critical obstruction level for a planet.

    Severity ladder:
      critical        — (Deep Combust OR Gandanta) + Soonya Rasi, no Pushkara
      critical_divine — Same but Pushkara Navamsa active → Visha Gati neutralised
      mild            — Regular combust (not deep) + Soonya Rasi
      mild_divine     — Same but Pushkara active
      none            — No obstruction
    """
    combust  = planet_data.get("combust",  {})
    gandanta = planet_data.get("gandanta", {})
    pushkara = planet_data.get("pushkara", {})

    has_deep    = combust.get("deep", False)
    has_combust = combust.get("combust", False)
    has_gandanta = gandanta.get("gandanta", False)
    in_soonya   = planet_data.get("sign_idx", -1) in soonya_rasis
    has_pushkara = pushkara.get("pushkara", False)

    is_hard    = has_deep or has_gandanta
    is_critical = is_hard and in_soonya
    is_mild     = has_combust and (not has_deep) and in_soonya

    severity = "none"
    visha_gati_note = ""
    has_divine = False

    if is_critical:
        if has_pushkara:
            severity = "critical_divine"
            has_divine = True
            visha_gati_note = (
                "Visha Gati (poisonous movement) — but Pushkara Navamsa is active. "
                "Expect initial struggle; divine grace restores unexpectedly."
            )
        else:
            severity = "critical"
            visha_gati_note = (
                "Visha Gati (poisonous movement) — no active protection. "
                "Karmic obstruction is strong; proceed with caution."
            )
    elif is_mild:
        if has_pushkara:
            severity = "mild_divine"
            has_divine = True
            visha_gati_note = (
                "Mild obstruction partially relieved by Pushkara Navamsa energy."
            )
        else:
            severity = "mild"
            visha_gati_note = (
                "Mild obstruction — Soonya Rasi reduces planet's delivery of results."
            )

    return {
        "critical":              is_critical,
        "mild":                  is_mild,
        "severity":              severity,
        "has_divine_protection": has_divine,
        "in_soonya":             in_soonya,
        "visha_gati_note":       visha_gati_note,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Combined 90-Day Scanner (single day-loop, all dosha types)
# ═════════════════════════════════════════════════════════════════════════════

def scan_all_dosha_transits(
    chandrashtama_sign_idx: int,
    vadhai_nak_idx: int,
    vainasikam_nak_idx: int,
    soonya_rasis: list[int],
    ref_dt: datetime.datetime,
    days_ahead: int = 90,
) -> dict:
    """
    Single-pass 90-day forward scan returning:
      chandrashtama_windows — grouped Moon transit windows
      red_zone_entries      — planet entries into Vadhai/Vainasikam nakshatras
      critical_windows      — malefic planet entering Soonya Rasi while hard-afflicted

    Optimised: all planets fetched once per day (not once per scan type).
    """
    ref_jd = swe.julday(
        ref_dt.year, ref_dt.month, ref_dt.day,
        ref_dt.hour + ref_dt.minute / 60.0 + ref_dt.second / 3600.0,
    )

    # ── Seed previous-day nakshatra positions ─────────────────────────────────
    prev_nak: dict[str, int] = {}
    _seed_jd = ref_jd - 1
    for p_name, p_id in _PLANET_IDS.items():
        xx, _ = swe.calc_ut(_seed_jd, p_id, _FLAGS)
        prev_nak[p_name] = int(xx[0] / _NAK_SPAN) % 27
    rahu_seed, _ = swe.calc_ut(_seed_jd, swe.TRUE_NODE, _FLAGS)
    prev_nak["Rahu"] = int(rahu_seed[0] / _NAK_SPAN) % 27
    prev_nak["Ketu"] = int(((rahu_seed[0] + 180) % 360) / _NAK_SPAN) % 27

    # ── Output containers ─────────────────────────────────────────────────────
    chandrashtama_windows: list[dict] = []
    red_zone_entries:      list[dict] = []
    critical_windows:      list[dict] = []

    # ── Chandrashtama window tracking ─────────────────────────────────────────
    in_chandra = False
    chandra_start_day = 0

    # ── Main day-loop ─────────────────────────────────────────────────────────
    for d in range(days_ahead + 1):
        jd       = ref_jd + d
        day_date = ref_dt + datetime.timedelta(days=d)

        # Fetch Sun once (needed for combustion in Soonya check)
        sun_xx, _ = swe.calc_ut(jd, swe.SUN, _FLAGS)
        sun_lon   = sun_xx[0]

        for p_name, p_id in _PLANET_IDS.items():
            if p_name == "Sun":
                p_lon   = sun_lon
                p_retro = False
            else:
                p_xx, _  = swe.calc_ut(jd, p_id, _FLAGS)
                p_lon    = p_xx[0]
                p_retro  = p_xx[3] < 0

            curr_nak  = int(p_lon / _NAK_SPAN) % 27
            curr_sign = int(p_lon / 30)

            # ── Chandrashtama (Moon only) ─────────────────────────────────────
            if p_name == "Moon":
                if curr_sign == chandrashtama_sign_idx:
                    if not in_chandra:
                        in_chandra = True
                        chandra_start_day = d
                else:
                    if in_chandra:
                        in_chandra = False
                        chandrashtama_windows.append({
                            "start_date":   ref_dt + datetime.timedelta(days=chandra_start_day),
                            "end_date":     day_date,
                            "days_away":    chandra_start_day,
                            "duration_days": d - chandra_start_day,
                        })

            # ── Red Zone: planet enters Vadhai / Vainasikam nakshatra ─────────
            if curr_nak != prev_nak[p_name]:
                for nak_idx, nak_type in [
                    (vadhai_nak_idx,     "Vadhai"),
                    (vainasikam_nak_idx, "Vainasikam"),
                ]:
                    if curr_nak == nak_idx:
                        red_zone_entries.append({
                            "planet":      p_name,
                            "type":        nak_type,
                            "nak_name":    NAKSHATRAS[nak_idx],
                            "entry_date":  day_date,
                            "days_away":   d,
                            "severity":    "CRITICAL" if nak_type == "Vainasikam" else "WARNING",
                        })

            prev_nak[p_name] = curr_nak

            # ── Soonya Critical: malefic enters Soonya Rasi while hard-afflicted
            if p_name in _MALEFICS and curr_sign in soonya_rasis:
                combust  = check_combustion(sun_lon, p_lon, p_name, p_retro)
                gandanta = check_gandanta(p_lon)
                pushkara = check_pushkara(p_lon)
                is_hard  = combust.get("deep") or gandanta.get("gandanta")
                if is_hard:
                    aff_type = (
                        "Deep Combust + Gandanta" if (combust.get("deep") and gandanta.get("gandanta"))
                        else ("Gandanta" if gandanta.get("gandanta") else "Deep Combust")
                    )
                    has_divine = pushkara.get("pushkara", False)
                    # Deduplicate: only record the entry day (sign transition)
                    if d == 0 or int(
                        (swe.calc_ut(ref_jd + d - 1, p_id, _FLAGS)[0][0]) / 30
                    ) != curr_sign:
                        critical_windows.append({
                            "planet":          p_name,
                            "soonya_sign":     RASIS[curr_sign],
                            "affliction_type": aff_type,
                            "has_divine":      has_divine,
                            "date":            day_date,
                            "days_away":       d,
                        })

        # ── Rahu / Ketu ───────────────────────────────────────────────────────
        rahu_xx, _ = swe.calc_ut(jd, swe.TRUE_NODE, _FLAGS)
        rahu_lon   = rahu_xx[0]
        ketu_lon   = (rahu_lon + 180) % 360

        for node_name, node_lon in [("Rahu", rahu_lon), ("Ketu", ketu_lon)]:
            curr_nak  = int(node_lon / _NAK_SPAN) % 27
            curr_sign = int(node_lon / 30)

            if curr_nak != prev_nak[node_name]:
                for nak_idx, nak_type in [
                    (vadhai_nak_idx,     "Vadhai"),
                    (vainasikam_nak_idx, "Vainasikam"),
                ]:
                    if curr_nak == nak_idx:
                        red_zone_entries.append({
                            "planet":     node_name,
                            "type":       nak_type,
                            "nak_name":   NAKSHATRAS[nak_idx],
                            "entry_date": day_date,
                            "days_away":  d,
                            "severity":   "CRITICAL",   # nodes at Red Zones are always critical
                        })

            prev_nak[node_name] = curr_nak

    # ── Close any open Chandrashtama window at horizon ───────────────────────
    if in_chandra:
        chandrashtama_windows.append({
            "start_date":    ref_dt + datetime.timedelta(days=chandra_start_day),
            "end_date":      ref_dt + datetime.timedelta(days=days_ahead),
            "days_away":     chandra_start_day,
            "duration_days": days_ahead - chandra_start_day,
        })

    red_zone_entries.sort(key=lambda x: x["days_away"])
    critical_windows.sort(key=lambda x: x["days_away"])

    return {
        "chandrashtama_windows": chandrashtama_windows,
        "red_zone_entries":      red_zone_entries,
        "critical_windows":      critical_windows,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Orchestrator Class
# ═════════════════════════════════════════════════════════════════════════════

class ObstructionDosha:
    """
    Compute the full Tamil/Sanskrit Obstruction Dosha profile for a native.

    Usage:
        od = ObstructionDosha("1985-06-15", "08:30", 13.08, 80.27)
        profile  = od.natal_profile    # fixed dosha blueprint
        transit  = od.transit_status   # live planet check vs dosha map
        forecast = od.forecast         # 90-day upcoming windows
        reading  = od.get_ai_reading(openai_api_key="...")
    """

    def __init__(
        self,
        birth_date:   str,
        birth_time:   str,
        lat:          float,
        lon:          float,
        transit_date: str | None = None,
    ):
        self._birth_utc = local_to_utc(birth_date, birth_time, lat, lon)
        self._lat = lat
        self._lon = lon

        # Transit reference datetime (noon UTC)
        if transit_date:
            try:
                td = datetime.datetime.strptime(transit_date, "%Y-%m-%d")
                self._transit_dt = td.replace(hour=12, tzinfo=datetime.timezone.utc)
            except ValueError:
                self._transit_dt = datetime.datetime.now(datetime.timezone.utc)
        else:
            self._transit_dt = datetime.datetime.now(datetime.timezone.utc)

        # Compute all layers once
        self._natal_profile  = self._compute_natal_profile()
        self._transit_status = self._compute_transit_status()
        self._forecast       = self._compute_forecast()

    # ── Public properties ────────────────────────────────────────────────────

    @property
    def natal_profile(self) -> dict:
        return self._natal_profile

    @property
    def transit_status(self) -> dict:
        return self._transit_status

    @property
    def forecast(self) -> dict:
        return self._forecast

    # ── Internal computation ─────────────────────────────────────────────────

    def _jd(self, dt: datetime.datetime) -> float:
        return swe.julday(
            dt.year, dt.month, dt.day,
            dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
        )

    def _compute_natal_profile(self) -> dict:
        jd_birth = self._jd(self._birth_utc)

        # Sun / Moon
        sun_xx,  _ = swe.calc_ut(jd_birth, swe.SUN,  _FLAGS)
        moon_xx, _ = swe.calc_ut(jd_birth, swe.MOON, _FLAGS)
        sun_lon  = sun_xx[0]
        moon_lon = moon_xx[0]

        # Tithi
        tithi_idx, tithi_name, paksha = get_tithi(moon_lon, sun_lon)
        soonya_rasis = get_soonya_rasis(tithi_idx)

        # Janma Nakshatra → Vadhai + Vainasikam
        moon_nak_name, moon_pada, moon_nak_lord = _get_nakshatra_pada(moon_lon)
        moon_nak_idx = NAKSHATRAS.index(moon_nak_name)
        vv = get_vadhai_vainasikam(moon_nak_idx)

        # Chandrashtama
        natal_moon_sign       = int(moon_lon / 30)
        chandrashtama_sign    = get_chandrashtama_sign(natal_moon_sign)

        # Lagna → Mudakku Rasi
        houses, ascmc = swe.houses_ex(
            jd_birth, self._lat, self._lon, b"P", _FLAGS
        )
        lagna_lon = ascmc[0]
        mudakku   = get_mudakku_rasi(lagna_lon)

        # Natal planet Soonya check
        natal_planets: dict[str, dict] = {}
        for p_name, p_id in _PLANET_IDS.items():
            p_xx, _ = swe.calc_ut(jd_birth, p_id, _FLAGS)
            p_lon   = p_xx[0]
            p_sign  = int(p_lon / 30)
            natal_planets[p_name] = {
                "longitude": p_lon,
                "sign_idx":  p_sign,
                "sign":      RASIS[p_sign],
                "in_soonya": p_sign in soonya_rasis,
            }

        # Rahu / Ketu
        rahu_xx, _ = swe.calc_ut(jd_birth, swe.TRUE_NODE, _FLAGS)
        rahu_lon   = rahu_xx[0]
        ketu_lon   = (rahu_lon + 180) % 360
        for node_name, node_lon in [("Rahu", rahu_lon), ("Ketu", ketu_lon)]:
            node_sign = int(node_lon / 30)
            natal_planets[node_name] = {
                "longitude": node_lon,
                "sign_idx":  node_sign,
                "sign":      RASIS[node_sign],
                "in_soonya": node_sign in soonya_rasis,
            }

        return {
            # Tithi layer
            "tithi_idx":           tithi_idx,
            "tithi_name":          tithi_name,
            "paksha":              paksha,
            "soonya_rasis":        soonya_rasis,
            "soonya_signs":        [RASIS[i] for i in soonya_rasis],
            "soonya_signs_english":[RASIS_ENGLISH[i] for i in soonya_rasis],
            # Red Zone layer
            "moon_nak_name":       moon_nak_name,
            "moon_nak_idx":        moon_nak_idx,
            "moon_pada":           moon_pada,
            "vadhai_nak_idx":      vv["vadhai_idx"],
            "vadhai_nak_name":     vv["vadhai_name"],
            "vainasikam_nak_idx":  vv["vainasikam_idx"],
            "vainasikam_nak_name": vv["vainasikam_name"],
            # Chandrashtama layer
            "natal_moon_sign_idx":    natal_moon_sign,
            "natal_moon_sign":        RASIS[natal_moon_sign],
            "chandrashtama_sign_idx": chandrashtama_sign,
            "chandrashtama_sign":     RASIS[chandrashtama_sign],
            "chandrashtama_english":  RASIS_ENGLISH[chandrashtama_sign],
            # Mudakku layer
            "mudakku":             mudakku,
            "lagna_longitude":     lagna_lon,
            "lagna_sign":          RASIS[int(lagna_lon / 30)],
            "lagna_english":       RASIS_ENGLISH[int(lagna_lon / 30)],
            # Planet-level Soonya map
            "natal_planets":       natal_planets,
        }

    def _compute_transit_status(self) -> dict:
        jd = self._jd(self._transit_dt)

        profile              = self._natal_profile
        soonya_rasis         = profile["soonya_rasis"]
        chandrashtama_idx    = profile["chandrashtama_sign_idx"]
        mudakku_sign_idx     = profile["mudakku"]["sign_idx"]
        vadhai_nak_idx       = profile["vadhai_nak_idx"]
        vainasikam_nak_idx   = profile["vainasikam_nak_idx"]

        sun_xx, _ = swe.calc_ut(jd, swe.SUN, _FLAGS)
        sun_lon   = sun_xx[0]

        status: dict[str, dict] = {}

        for p_name, p_id in _PLANET_IDS.items():
            if p_name == "Sun":
                p_lon, p_retro = sun_lon, False
            else:
                p_xx, _ = swe.calc_ut(jd, p_id, _FLAGS)
                p_lon   = p_xx[0]
                p_retro = p_xx[3] < 0

            p_sign   = int(p_lon / 30)
            p_nak    = int(p_lon / _NAK_SPAN) % 27

            _c = {"combust": False, "deep": False, "orb": 0.0,
                  "cross_sign": False, "would_combust": False, "na": True}
            combust  = check_combustion(sun_lon, p_lon, p_name, p_retro) if p_name != "Sun" else _c
            gandanta = check_gandanta(p_lon)
            pushkara = check_pushkara(p_lon)

            in_soonya      = p_sign in soonya_rasis
            in_chandrashtama = (p_name == "Moon" and p_sign == chandrashtama_idx)
            in_mudakku     = (p_sign == mudakku_sign_idx)

            red_zone = None
            if p_nak == vainasikam_nak_idx:
                red_zone = "Vainasikam"
            elif p_nak == vadhai_nak_idx:
                red_zone = "Vadhai"

            crit = check_critical_obstruction(
                {"sign_idx": p_sign, "combust": combust,
                 "gandanta": gandanta, "pushkara": pushkara},
                soonya_rasis,
            )

            status[p_name] = {
                "longitude":        p_lon,
                "sign_idx":         p_sign,
                "sign":             RASIS[p_sign],
                "nak_name":         NAKSHATRAS[p_nak],
                "in_soonya":        in_soonya,
                "in_chandrashtama": in_chandrashtama,
                "in_mudakku":       in_mudakku,
                "red_zone":         red_zone,
                "combust":          combust,
                "gandanta":         gandanta,
                "pushkara":         pushkara,
                "critical_obstruction": crit,
            }

        # Nodes
        rahu_xx, _ = swe.calc_ut(jd, swe.TRUE_NODE, _FLAGS)
        rahu_lon   = rahu_xx[0]
        ketu_lon   = (rahu_lon + 180) % 360

        _node_c = {"combust": False, "deep": False, "orb": 0.0,
                   "cross_sign": False, "would_combust": False, "na": True}
        for node_name, node_lon in [("Rahu", rahu_lon), ("Ketu", ketu_lon)]:
            n_sign = int(node_lon / 30)
            n_nak  = int(node_lon / _NAK_SPAN) % 27
            g      = check_gandanta(node_lon)
            pk     = check_pushkara(node_lon)

            in_soonya  = n_sign in soonya_rasis
            in_mudakku = (n_sign == mudakku_sign_idx)
            red_zone   = (
                "Vainasikam" if n_nak == vainasikam_nak_idx
                else ("Vadhai" if n_nak == vadhai_nak_idx else None)
            )

            status[node_name] = {
                "longitude":        node_lon,
                "sign_idx":         n_sign,
                "sign":             RASIS[n_sign],
                "nak_name":         NAKSHATRAS[n_nak],
                "in_soonya":        in_soonya,
                "in_chandrashtama": False,
                "in_mudakku":       in_mudakku,
                "red_zone":         red_zone,
                "combust":          _node_c,
                "gandanta":         g,
                "pushkara":         pk,
                "critical_obstruction": _NO_DOSHA.copy(),
            }

        return status

    def _compute_forecast(self) -> dict:
        p = self._natal_profile
        return scan_all_dosha_transits(
            chandrashtama_sign_idx = p["chandrashtama_sign_idx"],
            vadhai_nak_idx         = p["vadhai_nak_idx"],
            vainasikam_nak_idx     = p["vainasikam_nak_idx"],
            soonya_rasis           = p["soonya_rasis"],
            ref_dt                 = self._transit_dt,
            days_ahead             = 90,
        )

    # ── AI Reading ────────────────────────────────────────────────────────────

    def get_ai_reading(self, openai_api_key: str = "") -> str:
        prompt = _build_dosha_prompt(
            self._natal_profile, self._transit_status, self._forecast
        )
        if openai_api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_api_key)
                resp   = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert Vedic astrologer specialising in Tamil Jyotish "
                                "and classical Obstruction Doshas. Give concise, practical, and "
                                "compassionate guidance. Use exact planet and sign names from the "
                                "data provided. Always mention Pushkara Navamsa protection when "
                                "present. Use the terms 'Visha Gati' for afflicted planets and "
                                "'Divine Protection' for Pushkara-shielded ones."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=700,
                    temperature=0.5,
                )
                return resp.choices[0].message.content.strip()
            except Exception:
                pass
        return _build_dosha_fallback_reading(
            self._natal_profile, self._transit_status, self._forecast
        )


# ═════════════════════════════════════════════════════════════════════════════
# AI Prompt Builder
# ═════════════════════════════════════════════════════════════════════════════

def _build_dosha_prompt(
    profile:  dict,
    transit:  dict,
    forecast: dict,
) -> str:
    soonya_str = ", ".join(profile["soonya_signs"]) or "None"
    c_win      = forecast["chandrashtama_windows"][:3]
    rz_entries = forecast["red_zone_entries"][:5]
    crit_wins  = forecast["critical_windows"][:3]

    # ── Natal planets permanently in Soonya Rasi (key birth-level finding) ──
    natal_soonya = [
        f"{p} in {d['sign']}"
        for p, d in profile.get("natal_planets", {}).items()
        if d.get("in_soonya")
    ]
    natal_soonya_str = (
        ", ".join(natal_soonya)
        + " — these planets are PERMANENTLY in Soonya Rasi from birth. "
          "This is a significant birth-level weakness that MUST be mentioned first."
    ) if natal_soonya else "None"

    # ── Active transit doshas ────────────────────────────────────────────────
    active = []
    for p_name, d in transit.items():
        crit = d["critical_obstruction"]
        sev  = crit.get("severity", "none")
        if sev in ("critical", "critical_divine"):
            divine_note = " — DIVINE PROTECTION (Pushkara) active" if crit.get("has_divine_protection") else ""
            active.append(
                f"- {p_name}: CRITICAL OBSTRUCTION{divine_note}. {crit['visha_gati_note']}"
            )
        elif sev in ("mild", "mild_divine"):
            divine_note = " — Pushkara partially protects" if crit.get("has_divine_protection") else ""
            active.append(f"- {p_name}: Mild obstruction in Soonya Rasi ({d['sign']}){divine_note}")
        if d.get("in_chandrashtama"):
            active.append(f"- Moon: Chandrashtama active RIGHT NOW (in {profile['chandrashtama_sign']})")
        if d.get("red_zone"):
            active.append(
                f"- {p_name}: in {d['red_zone']} nakshatra ({d['nak_name']}) — RED ZONE transit"
            )
        if d.get("in_mudakku"):
            active.append(
                f"- {p_name}: in Mudakku Rasi ({profile['mudakku']['sign_name']}) — BLOCKED SIGN"
            )
        # Also flag Soonya-only without obstruction
        if d.get("in_soonya") and sev == "none" and not d.get("red_zone"):
            active.append(
                f"- {p_name}: transiting Soonya Rasi ({d['sign']}) — results weakened or erratic"
            )

    active_str = "\n".join(active) if active else "No critical obstructions active right now."

    # ── Upcoming windows ─────────────────────────────────────────────────────
    upcoming = []
    for w in c_win:
        upcoming.append(
            f"- Chandrashtama: {w['start_date'].strftime('%Y-%m-%d')} "
            f"(~{w['duration_days']} days in {profile['chandrashtama_english']})"
        )
    for e in rz_entries[:3]:
        zone_type = "Vainasikam (Annihilation — most severe)" if e["type"] == "Vainasikam" else "Vadhai (Destruction)"
        upcoming.append(
            f"- {e['planet']} enters {zone_type} ({e['nak_name']}) "
            f"on {e['entry_date'].strftime('%Y-%m-%d')}"
        )
    for cw in crit_wins[:2]:
        div = " — DIVINE PROTECTION (Pushkara) is confirmed active" if cw["has_divine"] else " — NO protection active"
        upcoming.append(
            f"- {cw['planet']} in Soonya Rasi ({cw['soonya_sign']}) + {cw['affliction_type']} "
            f"on {cw['date'].strftime('%Y-%m-%d')}{div}"
        )
    upcoming_str = "\n".join(upcoming) if upcoming else "No major obstruction windows in the next 90 days."

    return f"""
Natal Obstruction Dosha Profile:
- Birth Tithi: {profile['tithi_name']} ({profile['paksha']} Paksha)
- Thithi Soonya Rasis (void signs for this native): {soonya_str}
- NATAL PLANETS PERMANENTLY IN SOONYA: {natal_soonya_str}
- Janma Nakshatra: {profile['moon_nak_name']}
- Vadhai Nakshatra (7th — Destruction): {profile['vadhai_nak_name']}
- Vainasikam Nakshatra (22nd — Annihilation): {profile['vainasikam_nak_name']}
- Chandrashtama Sign (8th from natal Moon): {profile['chandrashtama_english']} ({profile['chandrashtama_sign']})
- Mudakku Rasi (Blocked, 22nd Drekkana from Lagna): {profile['mudakku']['sign_english']} {profile['mudakku']['degree_lo']}–{profile['mudakku']['degree_hi']}°

Current Transit Status:
{active_str}

Upcoming 90-Day Obstruction Windows:
{upcoming_str}

Instructions:
1. FIRST — state which natal planets are permanently in Soonya Rasi and explain the lifelong
   significance (e.g. Moon in Soonya = emotional instability, erratic mental results from birth).
2. For each ACTIVE transit obstruction: state the planet, say it has "Visha Gati" (poisonous
   movement), describe the life area affected. Only mention Pushkara Divine Protection if the
   data explicitly confirms it is active — do NOT speculate.
3. For upcoming windows: describe each concisely. Only call a window "critical" if the data
   labels it as Critical Obstruction. Red Zone transits should be called "Red Zone window".
4. Give 2-3 practical action tips for the most urgent upcoming window.
5. End with one grounding sentence about overall karmic picture.
6. Keep the total response under 450 words. Use plain language — avoid excessive Sanskrit jargon.
"""


def _build_dosha_fallback_reading(
    profile:  dict,
    transit:  dict,
    forecast: dict,
) -> str:
    """Analytical fallback when no OpenAI key is set."""
    lines = ["**Obstruction Dosha Analysis**\n"]

    # Blueprint
    soonya_str = ", ".join(profile["soonya_signs"]) or "None (Purnima/Amavasya birth — no void signs)"
    lines.append(f"**Birth Tithi**: {profile['tithi_name']} ({profile['paksha']} Paksha)  ")
    lines.append(f"**Thithi Soonya Rasis**: {soonya_str}  ")
    lines.append(
        f"**Red Zone Nakshatras**: Vadhai = *{profile['vadhai_nak_name']}* (Destruction) | "
        f"Vainasikam = *{profile['vainasikam_nak_name']}* (Annihilation)  "
    )
    lines.append(
        f"**Chandrashtama**: Transit Moon in *{profile['chandrashtama_english']}* "
        f"({profile['chandrashtama_sign']}) creates a ~2.5-day stress window each month.  "
    )
    lines.append(
        f"**Mudakku Rasi**: *{profile['mudakku']['sign_english']}* "
        f"({profile['mudakku']['degree_lo']}–{profile['mudakku']['degree_hi']}°) — "
        f"malefic transits here amplify karmic delays.  \n"
    )

    # Active obstructions
    active_found = False
    for p_name, d in transit.items():
        crit = d["critical_obstruction"]
        if crit["severity"] == "critical":
            active_found = True
            lines.append(
                f"🚨 **{p_name}** — *Visha Gati* active. {crit['visha_gati_note']} "
                f"Planet is in Soonya Rasi ({d['sign']}) + {_affliction_label(d)}.  "
            )
        elif crit["severity"] == "critical_divine":
            active_found = True
            lines.append(
                f"⭐ **{p_name}** — *Visha Gati neutralised by Pushkara Navamsa*. "
                f"{crit['visha_gati_note']}  "
            )
        elif crit["severity"] in ("mild", "mild_divine"):
            active_found = True
            lines.append(
                f"🟠 **{p_name}** — Mild obstruction in Soonya Rasi ({d['sign']}). "
                f"{crit['visha_gati_note']}  "
            )
        if d.get("in_chandrashtama"):
            active_found = True
            lines.append(
                f"🌑 **Moon** — Chandrashtama active now in {profile['chandrashtama_sign']}. "
                f"Avoid major decisions; guard emotional health.  "
            )
        if d.get("red_zone"):
            active_found = True
            lines.append(
                f"🔴 **{p_name}** — in *{d['red_zone']}* nakshatra ({d['nak_name']}). "
                f"{'CRITICAL' if d['red_zone'] == 'Vainasikam' else 'WARNING'}: "
                f"transit through this Red Zone nakshatra may bring challenges.  "
            )

    if not active_found:
        lines.append("✅ No critical obstruction doshas are active right now.\n")

    # Forecast
    c_wins = forecast["chandrashtama_windows"][:4]
    rz     = forecast["red_zone_entries"][:5]
    cw     = forecast["critical_windows"][:3]

    if c_wins or rz or cw:
        lines.append("\n**Upcoming 90-Day Obstruction Forecast**\n")
        for w in c_wins:
            lines.append(
                f"🌑 Chandrashtama: **{w['start_date'].strftime('%d %b %Y')}** "
                f"(~{w['duration_days']} days) — guard emotional decisions.  "
            )
        for e in rz:
            badge = "🔴 Red Zone (Vainasikam)" if e["severity"] == "CRITICAL" else "⚠️ Red Zone (Vadhai)"
            lines.append(
                f"{badge} {e['planet']} enters *{e['type']}* ({e['nak_name']}) "
                f"on **{e['entry_date'].strftime('%d %b %Y')}**.  "
            )
        for w in cw:
            div = " — ⭐ Divine Protection (Pushkara) active" if w["has_divine"] else ""
            lines.append(
                f"🚨 {w['planet']} in Soonya ({w['soonya_sign']}) + {w['affliction_type']} "
                f"on **{w['date'].strftime('%d %b %Y')}**{div}.  "
            )

    lines.append(
        "\n*Set OPENAI_API_KEY for a personalised narrative interpretation of these doshas.*"
    )
    return "\n".join(lines)


def _affliction_label(d: dict) -> str:
    c, g = d.get("combust", {}), d.get("gandanta", {})
    parts = []
    if c.get("deep"):
        parts.append("Deep Combust")
    if g.get("gandanta"):
        parts.append("Gandanta")
    return " + ".join(parts) if parts else "afflicted"
