"""
gemini_review.py — Ask Gemini to do a 3rd-eye code review of the natal
protection feature (Dasha/Bhukti, Pushkara Navamsa, combustion, gandanta,
Hidden Strength, transit forecast).

Usage:
    GEMINI_API_KEY=<your-key> python gemini_review.py

Get a free API key at: https://aistudio.google.com/app/apikey
(Free tier: 1500 req/day for Gemini 2.0 Flash, 50/day for 2.5 Pro)
"""

import os
import sys
import pathlib

# ── Install new SDK if needed ─────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Installing google-genai …")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "google-genai", "-q"])
    from google import genai
    from google.genai import types

# ── API key ───────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    print(
        "\n⚠️  No GEMINI_API_KEY found.\n"
        "   Get a free key at: https://aistudio.google.com/app/apikey\n"
        "\n   Then run:\n"
        "       GEMINI_API_KEY=your_key_here python gemini_review.py\n"
    )
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

# ── Load the files to review ──────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent
files = {
    "natal_protection.py": ROOT / "natal_protection.py",
    "app.py":              ROOT / "app.py",
}

code_blocks = []
for name, path in files.items():
    content = path.read_text(encoding="utf-8")
    code_blocks.append(f"### FILE: {name}\n```python\n{content}\n```")

code_section = "\n\n".join(code_blocks)

# ── Review prompt ─────────────────────────────────────────────────────────────
PROMPT = f"""
You are a senior Python architect and Vedic astrology domain expert providing
a thorough "3rd eye" code review. The developer used AI assistance to build
this feature — your job is to find anything the AI may have got wrong, missed,
or implemented sub-optimally.

Focus your review on these specific areas:

---

## 1. Vimshottari Dasha / Bhukti Engine
Functions: `calculate_vimshottari_dasha`, `_calculate_bhukti`, `get_current_dasha_bhukti`

- Is anchoring the timeline to the TRUE start (before birth) correct?
- Is the bhukti duration formula `(maha_years × bhukti_lord_years) / 120` accurate per classical texts?
- Does the bhukti sequence starting from the Maha Dasha lord follow classical Vimshottari rules?
- Are there edge cases at nakshatra boundaries (Moon at exactly 0° or 360° of a nakshatra)?
- What happens if today's date is beyond all 9 computed dashas?
- Floating-point precision: are `timedelta` days accurate enough for decade-long periods?

## 2. Transit Affliction Scanner
Function: `scan_transit_affliction`

- Is day-by-day scanning robust, or could it miss a brief (<1 day) affliction?
- For NODES (Rahu/Ketu): is it correct to only check Gandanta and skip combustion entirely?
- Does the exit/next-entry detection handle the case where affliction lasts beyond `days_ahead`?
- Is the Julian Day conversion (`swe.julday`) handling UTC correctly for the scan loop?
- Any risk of incorrect Ketu longitude at the 0°/360° wrap-around?

## 3. Pushkara Navamsa Engine
Functions: `check_pushkara`, `scan_pushkara_transit`

- Are the 24 `_PUSHKARA_ZONES` degree ranges correct per classical Jyotish texts
  (BPHS / Brihat Jataka)? Cross-check especially the Water-sign zones
  (Cancer 0°–3°20', Cancer 6°40'–10°) and Air-sign zones.
- The zones use sidereal longitudes (0–360°). Is the input to `check_pushkara`
  always guaranteed to be the sidereal longitude from pyswisseph? Could there
  be an ayanamsa-not-set edge case?
- `scan_pushkara_transit` scans day-by-day: could a fast planet (Moon) spend
  less than 1 day in a 3°20' Pushkara zone and be missed entirely?
- For Ketu: longitude = `(TRUE_NODE + 180) % 360`. Is `% 360` sufficient to
  prevent the zone check receiving a value outside 0–360?
- Divine Protection rule: `is_pushkara AND (deep_combust OR gandanta)`.
  Should REGULAR combustion (not deep) also qualify for Divine Protection?
  The current code only grants +5 for deep combust or gandanta. Verify this
  against the classical source.
- Score delta: +5 for Divine Protection. Is this additive on top of the -2
  deep-combust penalty, or does it replace it? Trace through `_protection_score()`
  to confirm the net effect is +3 (not +5 ignoring the penalty).

## 4. Combustion Logic
Function: `check_combustion`

- Is the same-sign classical exception (`cross_sign`) applied correctly?
- Should Mercury retrograde EVER be considered for combustion (some texts say
  retrograde Mercury near Sun is STRONGER, not combust)?
- Does `would_combust` give misleading information in any scenario?

## 5. Gandanta Override in UI
Function: `_flags` in `_comparison_table_html` (app.py)

- When `cross_sign=True` AND `gandanta=True`, does suppressing the cross-sign
  note make astrological sense?
- Is "overrides sign-wall" accurate — or do some classical texts treat them
  independently?

## 6. Hidden Strength Label
Logic: combust D1 + Vargottama D9 → "Hidden Strength"

- Is this combination universally agreed upon in Jyotish, or is it
  school-dependent?
- Should the Vargottama check use D1 == D9 sign, or the actual Navamsa chart
  degree comparison?
- Any scenario where the label fires incorrectly?

## 7. AI Prompt Quality (`_build_protection_prompt`)
- Does the prompt pass enough context for the AI to correctly interpret
  Pushkara Navamsa? Specifically: does it pass the zone name, the house
  number, and the affliction type together so the AI can construct the
  "surface struggle → divine recovery" narrative?
- The prompt includes house numbers. Are there any cases where the house
  number could be 0 or 13 (off-by-one in `_house_num()`)?
- Is the instruction to "never skip Pushkara interpretation" strong enough,
  or will the LLM still ignore it for minor planets?

## 8. General Code Quality
- Performance: `scan_pushkara_transit` runs 180 SWE calls per planet × 9 planets
  = 1620 calls per analysis click. `scan_transit_affliction` adds 365 × 2 = 730
  more. Total ~2350 SWE calls. Is this acceptable latency for a web UI?
  Would caching the Sun's position across the day-loop help?
- Mobile responsiveness: the HTML cards use inline `display:grid` and
  `display:flex`. Are `min-width` values set in a way that will cause
  horizontal overflow on 360px phone screens?
- Thread safety: is `swe.set_sid_mode(swe.SIDM_LAHIRI)` safe to call in
  concurrent Gradio requests?
- Any import or dependency issues for Hugging Face Spaces deployment?

---

For each issue found:
1. State the **function name** and **nature of the problem**
2. Rate severity: 🔴 Critical / 🟡 Minor / 🟢 Suggestion
3. Provide a **concrete fix** (code snippet preferred)

Here are the files:

{code_section}
"""

# ── Call Gemini with fallback ─────────────────────────────────────────────────
MODELS = [
    "gemini-2.5-pro-exp-03-25",   # best reasoning
    "gemini-2.0-flash",           # fallback: fast + free
]

for model_id in MODELS:
    try:
        print(f"🤖 Sending code to Gemini ({model_id}) for review …\n")
        print("─" * 70)

        for chunk in client.models.generate_content_stream(
            model=model_id,
            contents=PROMPT,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,
            ),
        ):
            if chunk.text:
                print(chunk.text, end="", flush=True)

        print("\n" + "─" * 70)
        print(f"\n✅ Review complete (model: {model_id}).")
        break

    except Exception as exc:
        msg = str(exc).lower()
        if any(x in msg for x in ("quota", "429", "resource_exhausted", "not found", "invalid")):
            print(f"⚠️  {model_id} unavailable ({exc}), trying next model …\n")
            continue
        raise
