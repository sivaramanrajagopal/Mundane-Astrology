"""
Predictor — Mundane Astrology categorization and OpenAI LLM analysis.
"""

import os
import pandas as pd
from astrology_engine import COUNTRY_LAGNAS, get_lagna_sign

# ---------------------------------------------------------------------------
# Legacy flat categorization (used for heatmap summary)
# ---------------------------------------------------------------------------
POSITIVE_PLANETS = {"Jupiter", "Venus"}
POSITIVE_HOUSES  = {2, 5, 9, 11}
VOLATILE_PLANETS = {"Mars", "Rahu", "Saturn"}
VOLATILE_HOUSES  = {1, 7, 8, 12}
HIGH_RISK_THRESHOLD   = 3
HIGH_GROWTH_THRESHOLD = 2


def categorize_transits(house_positions: dict) -> dict:
    result = {}
    for planet, house in house_positions.items():
        if planet in POSITIVE_PLANETS and house in POSITIVE_HOUSES:
            result[planet] = "Positive/Growth"
        elif planet in VOLATILE_PLANETS and house in VOLATILE_HOUSES:
            result[planet] = "Volatility/Crisis"
        else:
            result[planet] = "Neutral"
    return result


def get_country_summary(categories: dict) -> str:
    volatile = sum(1 for v in categories.values() if v == "Volatility/Crisis")
    positive = sum(1 for v in categories.values() if v == "Positive/Growth")
    if volatile >= HIGH_RISK_THRESHOLD:
        return "High Risk"
    if positive >= HIGH_GROWTH_THRESHOLD:
        return "High Growth"
    return "Mixed"


# ---------------------------------------------------------------------------
# Domain-level categorization (Categorical Pulse)
# ---------------------------------------------------------------------------
DOMAIN_CATEGORIES = {
    "Share Market & Economy": {
        "houses":           {2, 5, 8, 11},
        "positive_planets": {"Jupiter", "Venus"},
        "positive_label":   "Bullish/Growth",
        "risk_planets":     {"Saturn", "Rahu", "Mars"},
        "risk_label":       "Volatility/Market Stress",
        "icon":             "💰",
    },
    "National Security & Risk": {
        "houses":           {1, 6, 7, 8, 12},
        "positive_planets": {"Jupiter", "Sun"},
        "positive_label":   "Strong Diplomacy",
        "risk_planets":     {"Mars", "Rahu", "Ketu"},
        "risk_label":       "Security Alert/Conflict Risk",
        "icon":             "🛡️",
    },
    "Governance & Infrastructure": {
        "houses":           {4, 10},
        "positive_planets": {"Sun", "Mercury"},
        "positive_label":   "Policy Breakthrough",
        "risk_planets":     {"Saturn", "Rahu"},
        "risk_label":       "Bureaucratic Delay/Political Tension",
        "icon":             "🏛️",
    },
    "Tech & Media": {
        "houses":           {3, 9, 11},
        "positive_planets": {"Mercury", "Jupiter"},
        "positive_label":   "Innovation Surge",
        "risk_planets":     {"Rahu", "Saturn", "Mars"},
        "risk_label":       "Tech Disruption/Censorship",
        "icon":             "🚀",
    },
}

# House → icon mapping for the Global Heatmap
HOUSE_ICON_MAP = {
    2: "💰", 5: "💰", 11: "💰",          # Economy (H8 shared — prioritise Security)
    1: "🛡️", 6: "🛡️", 7: "🛡️", 8: "🛡️", 12: "🛡️",  # Security
    4: "🏛️", 10: "🏛️",                    # Governance
    3: "🚀", 9: "🚀",                     # Tech/Media
}


def map_house_to_category(planet: str, house_number: int) -> dict | None:
    """
    Return the first matching domain category for a planet + house pair.
    Returns {domain, status, label, score} or None if no domain matches.
    """
    for domain, cfg in DOMAIN_CATEGORIES.items():
        if house_number not in cfg["houses"]:
            continue
        if planet in cfg["positive_planets"]:
            return {"domain": domain, "status": "Positive",
                    "label": cfg["positive_label"], "score": 78}
        if planet in cfg["risk_planets"]:
            return {"domain": domain, "status": "Risk",
                    "label": cfg["risk_label"], "score": 22}
        return {"domain": domain, "status": "Neutral",
                "label": "Stable", "score": 50}
    return None


def get_market_tip(transit_data: dict, house_positions: dict) -> str:
    """Rule-based one-liner market tip for the Economy domain card."""
    tips = []
    merc = transit_data.get("Mercury", {})
    if merc.get("retrograde"):
        tips.append("⚠️ Mercury Retrograde — expect contract delays & flash volatility")
    saturn_h = house_positions.get("Saturn")
    if saturn_h in {2, 8, 11}:
        tips.append("⚠️ Saturn compresses earnings; favour defensive sectors")
    jupiter_h = house_positions.get("Jupiter")
    if jupiter_h in {2, 5, 11}:
        tips.append("✨ Jupiter supports long-term growth investments")
    venus_h = house_positions.get("Venus")
    if venus_h in {2, 11}:
        tips.append("✨ Venus in wealth house: luxury & FMCG sectors favoured")
    mars_h = house_positions.get("Mars")
    if mars_h == 8:
        tips.append("⚠️ Mars-H8: watch for sudden sharp corrections")
    return tips[0] if tips else "📊 Markets reflect balanced planetary energies"


def build_categorical_pulse(transit_data: dict, house_positions: dict) -> dict:
    """
    Build per-domain sentiment scores and triggers.

    Returns:
        {domain_name: {icon, status, sentiment_emoji, sentiment_label,
                       score, positive_triggers, risk_triggers, market_tip}}
    """
    result = {}
    for domain, cfg in DOMAIN_CATEGORIES.items():
        pos_triggers = []
        risk_triggers = []
        neutral_count = 0
        score = 50  # start balanced

        for planet, house in house_positions.items():
            if house not in cfg["houses"]:
                continue
            if planet in cfg["positive_planets"]:
                pos_triggers.append(f"{planet} (H{house})")
                score = min(100, score + 18)
            elif planet in cfg["risk_planets"]:
                risk_triggers.append(f"{planet} (H{house})")
                score = max(0, score - 18)
            else:
                neutral_count += 1

        # Determine status tier
        if score >= 68:
            status = "High Growth"
            emoji  = "🟢"
            label  = cfg["positive_label"]
        elif score <= 32:
            status = "High Risk"
            emoji  = "🔴"
            label  = cfg["risk_label"]
        else:
            status = "Stable"
            emoji  = "🟡"
            label  = "Mixed/Neutral"

        entry = {
            "icon":              cfg["icon"],
            "status":            status,
            "sentiment_emoji":   emoji,
            "sentiment_label":   label,
            "score":             score,
            "positive_triggers": pos_triggers,
            "risk_triggers":     risk_triggers,
        }
        if domain == "Share Market & Economy":
            entry["market_tip"] = get_market_tip(transit_data, house_positions)
        result[domain] = entry

    return result


# ---------------------------------------------------------------------------
# Heatmap DataFrame (icons instead of house labels)
# ---------------------------------------------------------------------------
PLANET_ORDER = ["Jupiter", "Venus", "Mars", "Rahu", "Saturn",
                "Sun", "Moon", "Mercury", "Ketu"]


def build_heatmap_data(transit_data: dict, all_data: dict) -> list[dict]:
    """
    Return list of dicts — one per country — for HTML heatmap rendering.
    Planet cells carry icon + house number instead of plain "H5 (Growth)".
    """
    rows = []
    for country, data in all_data.items():
        hp      = data["house_positions"]
        cats    = data["categories"]
        summary = data["summary"]
        pulse   = data.get("pulse", {})

        row = {
            "country":  country,
            "lagna":    get_lagna_sign(country),
            "summary":  summary,
            "planets":  {},
            "pulse":    pulse,
        }
        for planet in PLANET_ORDER:
            house = hp.get(planet, "?")
            cat   = cats.get(planet, "Neutral")
            icon  = HOUSE_ICON_MAP.get(house, "")
            if cat == "Positive/Growth":
                color = "#22c55e"
            elif cat == "Volatility/Crisis":
                color = "#ef4444"
            else:
                color = "#eab308"
            row["planets"][planet] = {
                "house": house, "icon": icon, "color": color, "cat": cat
            }
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# "What to Watch" AI Summary
# ---------------------------------------------------------------------------
def generate_watch_summary(all_country_data: dict, ingresses: list,
                            retro_status: dict, lunations: list,
                            openai_api_key: str) -> str:
    """
    Generate a global 4-bullet "What to Watch This Week" briefing.
    Returns raw bullet-point text (may be empty if no API key).
    """
    if not openai_api_key:
        return "• Set OPENAI_API_KEY to enable the weekly watch summary."

    # Build compact context
    country_snap = "  ".join(
        f"{c}: {d['summary']}"
        for c, d in all_country_data.items()
    )
    retro_now = ", ".join(retro_status.get("currently_retrograde", [])) or "None"
    next_stations = "  ".join(
        f"{s['planet']} {s['event']} in {s['days_away']}d"
        for s in retro_status.get("upcoming_stations", [])[:3]
    ) or "None"
    next_ingress = "  ".join(
        f"{i['planet']} → {i['to_sign']} in {i['days_away']}d"
        for i in ingresses[:3]
    ) or "None"
    next_lunation = (
        f"{lunations[0]['type']} in {lunations[0]['sign']} "
        f"({lunations[0]['days_away']}d, {lunations[0]['date']})"
        if lunations else "None in range"
    )

    prompt = f"""You are a senior Vedic mundane astrologer. Write a "What to Watch This Week" briefing.

Global Snapshot:
- Country Risk: {country_snap}
- Currently Retrograde: {retro_now}
- Upcoming Stations: {next_stations}
- Next Ingresses: {next_ingress}
- Next Lunation: {next_lunation}

Write EXACTLY 4 bullet points (start each with "• "). Max 28 words per bullet.
Cover: markets/economy, geopolitics/security, governance/policy, wildcards/eclipse risks.
Be specific — name the planet, sign, and country impact."""

    try:
        from openai import OpenAI
        client   = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"• Watch summary unavailable: {e}"


# ---------------------------------------------------------------------------
# LLM prompt builder (bullet-point format)
# ---------------------------------------------------------------------------
def _build_llm_prompt(country: str, transit_data: dict,
                       house_positions: dict, categories: dict) -> str:
    import datetime
    today = datetime.date.today().isoformat()
    lagna = get_lagna_sign(country)

    lines = [
        "You are a Vedic astrologer specializing in Mundane Astrology (Gocharam).",
        "",
        f"Country: {country}",
        f"Natal Lagna: {lagna}",
        f"Analysis Date: {today}",
        "",
        "Current Planetary Transits (Sidereal / Lahiri ayanamsa):",
    ]
    for planet, data in transit_data.items():
        house  = house_positions.get(planet, "?")
        retro  = " (Retrograde)" if data.get("retrograde") else ""
        lines.append(
            f"  - {planet}: {data['sign']}, House {house}, "
            f"{data['nakshatra']} Pada {data['pada']}{retro}"
        )
    lines += ["", "Astrological Signals:"]
    for planet, cat in categories.items():
        lines.append(f"  - {planet} H{house_positions.get(planet,'?')}: {cat}")

    lines += [
        "",
        f"Provide a structured analysis for {country}. Use EXACTLY these section headers.",
        "Each section must use bullet points starting with '• '.",
        "",
        "## The Bright Side",
        "[4-5 bullet points on positive prospects and growth areas]",
        "",
        "## Strategic Risks",
        "[4-5 bullet points on challenges, tensions and cautions]",
        "",
        "## Mundane Events Context",
        "[3-4 bullet points connecting current world events to these planetary positions]",
    ]
    return "\n".join(lines)


def _parse_llm_response(raw_text: str) -> dict:
    sections = {"bright_side": "", "strategic_risks": "", "mundane_context": ""}
    parts = raw_text.split("## ")
    for part in parts:
        s = part.strip()
        if s.startswith("The Bright Side"):
            sections["bright_side"] = s[len("The Bright Side"):].strip()
        elif s.startswith("Strategic Risks"):
            sections["strategic_risks"] = s[len("Strategic Risks"):].strip()
        elif s.startswith("Mundane Events Context"):
            sections["mundane_context"] = s[len("Mundane Events Context"):].strip()
    if not any(sections.values()):
        sections["bright_side"] = raw_text.strip()
    return sections


def _text_to_bullets(text: str) -> list[str]:
    """
    Split LLM text into a list of bullet strings.
    Handles '• ' prefix bullets or plain paragraph sentences.
    """
    if "• " in text:
        return [b.strip() for b in text.split("• ") if b.strip()]
    # Fall back: split on newlines or ". "
    lines = [l.strip() for l in text.replace(". ", ".\n").splitlines() if l.strip()]
    return lines


# ---------------------------------------------------------------------------
# OpenAI LLM analysis
# ---------------------------------------------------------------------------
def generate_llm_analysis(country: str, transit_data: dict,
                           house_positions: dict, categories: dict,
                           openai_api_key: str) -> dict:
    """
    Call OpenAI (gpt-4o-mini) to generate narrative analysis.
    Returns {bright_side, strategic_risks, mundane_context} as raw text.
    Falls back gracefully if no API key is set.
    """
    if not openai_api_key:
        return {
            "bright_side": "• Configure OPENAI_API_KEY to enable AI analysis.",
            "strategic_risks": "• Set the environment variable OPENAI_API_KEY and reload.",
            "mundane_context": "",
        }

    try:
        from openai import OpenAI
        client   = OpenAI(api_key=openai_api_key)
        prompt   = _build_llm_prompt(country, transit_data, house_positions, categories)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1400,
        )
        raw_text = response.choices[0].message.content
        return _parse_llm_response(raw_text)
    except Exception as e:
        return {
            "bright_side":    f"• Analysis unavailable: {e}",
            "strategic_risks": "",
            "mundane_context": "",
        }
