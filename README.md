---
title: Mundane Astrology Dashboard
emoji: 🪐
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🪐 Mundane Astrology Dashboard

**Vedic Gocharam (Transit) Analysis for Nations** — India · USA · China · EU

A Vedic Mundane Astrology dashboard that calculates real-time planetary transits (using Swiss Ephemeris / Lahiri ayanamsa) and interprets their impact on nations across four domains: Economy, Security, Governance, and Technology.

## Features

| Tab | What it does |
|-----|-------------|
| 🌍 Global Heatmap | Icon-coded planetary status across all 4 nations at a glance |
| 🔍 Regional Analysis | Risk/Reward gauge, Categorical Pulse, AI Bright Side vs Strategic Risks |
| 📰 Mundane News Alerts | AI-generated world events interpretation through Gocharam lens |
| 🌟 Weekly Watch | Retrograde tracker, planet ingress countdown, lunation & eclipse alerts |
| 🗺️ Visual Astro Charts | South Indian square charts (natal + live transit), Quick Pulse & Daily Pulse tables |

## Setup

### Required Secret

In **Space Settings → Variables and secrets**, add:

```
OPENAI_API_KEY = sk-...your key...
```

The app works without it (rule-based analysis still runs), but the AI narrative sections will be disabled.

## Technical Stack

- **Ephemeris:** [pyswisseph](https://github.com/astrorigin/pyswisseph) — Swiss Ephemeris, Lahiri ayanamsa, Moshier fallback (no ephemeris files needed)
- **UI:** [Gradio](https://gradio.app) 4.x — dark theme, mobile/iPad responsive
- **AI:** OpenAI `gpt-4o-mini` — structured Vedic analysis prompts
- **Charts:** Pure HTML/CSS South Indian square chart renderer

## Astrological Methodology

- Sidereal zodiac (Lahiri ayanamsa)
- Country natal lagnas: India=Taurus · USA=Sagittarius · China=Aquarius · EU=Capricorn
- Vedic planets: Sun Moon Mercury Venus Mars Jupiter Saturn Rahu Ketu
- Categorical domains: Economy (H2/5/8/11) · Security (H1/6/7/8/12) · Governance (H4/10) · Tech (H3/9/11)
