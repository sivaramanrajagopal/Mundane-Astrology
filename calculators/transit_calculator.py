"""
Transit/Gochara Calculator
Extracted and adapted from cosmicconnection/houseconnections.py
Removed Flask/Gradio dependencies, kept only calculation logic for FastAPI integration
"""

import swisseph as swe
import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Set

# ============================================================================
# VEDIC ASTROLOGY CONSTANTS
# ============================================================================

RASIS = ["Mesha", "Rishaba", "Mithuna", "Kataka", "Simha", "Kanni",
         "Thula", "Vrischika", "Dhanus", "Makara", "Kumbha", "Meena"]

RASIS_ENGLISH = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
              "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
              "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
              "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

SIGN_LORDS = {"Mesha": "Mars", "Rishaba": "Venus", "Mithuna": "Mercury",
              "Kataka": "Moon", "Simha": "Sun", "Kanni": "Mercury",
              "Thula": "Venus", "Vrischika": "Mars", "Dhanus": "Jupiter",
              "Makara": "Saturn", "Kumbha": "Saturn", "Meena": "Jupiter"}

NAKSHATRA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"] * 3
NAKSHATRA_TO_LORD = {nak: NAKSHATRA_LORDS[i] for i, nak in enumerate(NAKSHATRAS)}

PLANETARY_STATES = {
    'Sun': {'exalted': 'Mesha', 'debilitated': 'Thula', 'own': ['Simha']},
    'Moon': {'exalted': 'Rishaba', 'debilitated': 'Vrischika', 'own': ['Kataka']},
    'Mars': {'exalted': 'Makara', 'debilitated': 'Kataka', 'own': ['Mesha', 'Vrischika']},
    'Mercury': {'exalted': 'Kanni', 'debilitated': 'Meena', 'own': ['Mithuna', 'Kanni']},
    'Jupiter': {'exalted': 'Kataka', 'debilitated': 'Makara', 'own': ['Dhanus', 'Meena']},
    'Venus': {'exalted': 'Meena', 'debilitated': 'Kanni', 'own': ['Rishaba', 'Thula']},
    'Saturn': {'exalted': 'Thula', 'debilitated': 'Mesha', 'own': ['Makara', 'Kumbha']}
}

HOUSE_SIGNIFICATIONS = {
    1: {"area": "Self & Personality", "themes": ["health", "appearance", "vitality", "overall well-being"]},
    2: {"area": "Wealth & Family", "themes": ["finances", "family", "speech", "food", "assets"]},
    3: {"area": "Courage & Siblings", "themes": ["communication", "short travels", "siblings", "skills", "courage"]},
    4: {"area": "Home & Mother", "themes": ["property", "vehicles", "mother", "happiness", "education"]},
    5: {"area": "Intelligence & Children", "themes": ["creativity", "children", "romance", "speculation", "intellect"]},
    6: {"area": "Health & Enemies", "themes": ["disease", "debts", "enemies", "competition", "service"]},
    7: {"area": "Partnership & Marriage", "themes": ["spouse", "business partnerships", "public relations"]},
    8: {"area": "Transformation & Longevity", "themes": ["sudden events", "inheritance", "occult", "research", "longevity"]},
    9: {"area": "Fortune & Higher Learning", "themes": ["luck", "father", "dharma", "long travels", "spirituality"]},
    10: {"area": "Career & Status", "themes": ["profession", "reputation", "authority", "government", "karma"]},
    11: {"area": "Gains & Networks", "themes": ["income", "friends", "aspirations", "elder siblings", "profits"]},
    12: {"area": "Loss & Liberation", "themes": ["expenses", "foreign lands", "isolation", "spirituality", "losses"]}
}

PLANETARY_NATURE = {
    'Sun': {'type': 'malefic', 'strength': 'strong', 'tempo': 'hot'},
    'Moon': {'type': 'benefic', 'strength': 'changeable', 'tempo': 'cool'},
    'Mars': {'type': 'malefic', 'strength': 'strong', 'tempo': 'hot'},
    'Mercury': {'type': 'neutral', 'strength': 'adaptable', 'tempo': 'neutral'},
    'Jupiter': {'type': 'benefic', 'strength': 'very_strong', 'tempo': 'warm'},
    'Venus': {'type': 'benefic', 'strength': 'strong', 'tempo': 'cool'},
    'Saturn': {'type': 'malefic', 'strength': 'slow', 'tempo': 'cold'},
    'Rahu': {'type': 'malefic', 'strength': 'intense', 'tempo': 'hot'},
    'Ketu': {'type': 'malefic', 'strength': 'spiritual', 'tempo': 'neutral'}
}

HOUSE_CLASSIFICATIONS = {
    'kendra': [1, 4, 7, 10],  # Angular - most powerful
    'trikona': [1, 5, 9],  # Trine - most auspicious
    'upachaya': [3, 6, 10, 11],  # Growing houses
    'dusthana': [6, 8, 12],  # Difficult houses
    'maraka': [2, 7],  # Death-inflicting
    'kama': [3, 7, 11],  # Desire
    'artha': [2, 6, 10],  # Wealth
    'dharma': [1, 5, 9],  # Righteousness
    'moksha': [4, 8, 12]  # Liberation
}

# Initialize Swiss Ephemeris
swe.set_sid_mode(swe.SIDM_LAHIRI)


# ============================================================================
# CORE CALCULATION FUNCTIONS
# ============================================================================

def get_chart_info(longitude: float, speed: float = None) -> Dict:
    """Get sign, nakshatra, and pada from longitude"""
    pada = int(((longitude % (360 / 27)) / (360 / 27 / 4)) + 1)
    return {
        'longitude': longitude,
        'retrograde': speed < 0 if speed is not None else None,
        'rasi': RASIS[int(longitude // 30)],
        'nakshatra': NAKSHATRAS[int((longitude % 360) // (360 / 27))],
        'pada': pada
    }


def get_planet_positions(jd: float, lat: float, lon: float) -> Tuple[Dict, float, List]:
    """Calculate planetary positions for given Julian Day"""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    FLAGS = swe.FLG_SIDEREAL | swe.FLG_SPEED
    results = {}
    swe.set_topo(lon, lat, 0)
    
    # Calculate main planets
    for pid in range(0, 10):
        name = swe.get_planet_name(pid)
        lonlat = swe.calc_ut(jd, pid, FLAGS)[0]
        results[name] = get_chart_info(lonlat[0], lonlat[3])
    
    # Rahu (North Node)
    rahu = swe.calc_ut(jd, swe.TRUE_NODE, FLAGS)[0]
    results['Rahu'] = get_chart_info(rahu[0], rahu[3])
    results['Rahu']['retrograde'] = True
    
    # Ketu (opposite of Rahu)
    ketu_lon = (rahu[0] + 180.0) % 360.0
    results['Ketu'] = get_chart_info(ketu_lon, rahu[3])
    results['Ketu']['retrograde'] = True
    
    # Ascendant
    cusps_result, ascmc = swe.houses_ex(jd, lat, lon, b'P', flags=FLAGS)
    results['Ascendant'] = get_chart_info(ascmc[0])
    
    return results, ascmc[0], cusps_result[1:]


def get_house_from_longitude(longitude: float, asc_deg: float) -> int:
    """Get house number from longitude"""
    lagna_rasi = int(asc_deg // 30)
    planet_rasi = int(longitude // 30)
    return (planet_rasi - lagna_rasi) % 12 + 1


def get_planet_house_ownership(lagna_sign: str, planet_name: str) -> List[int]:
    """Get houses owned by a planet"""
    try:
        lagna_idx = RASIS.index(lagna_sign)
    except ValueError:
        return []
    owned_houses = []
    for i, sign in enumerate(RASIS):
        if SIGN_LORDS.get(sign) == planet_name:
            house = (i - lagna_idx) % 12 + 1
            owned_houses.append(house)
    return owned_houses


def get_nth_house_from(from_house: int, n: int) -> int:
    """Get nth house from a given house"""
    return ((from_house + n - 2) % 12) + 1


def get_planet_aspects(planet: str, from_house: int) -> Set[int]:
    """Get houses aspected by a planet"""
    aspects = set()
    seventh_house = get_nth_house_from(from_house, 7)
    aspects.add(seventh_house)
    
    if planet == 'Mars':
        aspects.add(get_nth_house_from(from_house, 4))
        aspects.add(get_nth_house_from(from_house, 8))
    elif planet == 'Jupiter':
        aspects.add(get_nth_house_from(from_house, 5))
        aspects.add(get_nth_house_from(from_house, 9))
    elif planet == 'Saturn':
        aspects.add(get_nth_house_from(from_house, 3))
        aspects.add(get_nth_house_from(from_house, 10))
    
    return sorted(aspects)


def determine_planetary_state(planet: str, sign: str) -> str:
    """Determine planetary dignity"""
    if planet in ['Rahu', 'Ketu', 'Ascendant']:
        return 'N/A'
    
    states = PLANETARY_STATES.get(planet, {})
    if sign == states.get('exalted'):
        return 'Exalted'
    if sign == states.get('debilitated'):
        return 'Debilitated'
    
    own_signs = states.get('own', [])
    if sign in own_signs:
        return 'Own Sign'
    
    sign_lord = SIGN_LORDS[sign]
    friendships = {
        'Sun': {'friends': ['Moon', 'Mars', 'Jupiter'], 'enemies': ['Venus', 'Saturn']},
        'Moon': {'friends': ['Sun', 'Mercury'], 'enemies': []},
        'Mars': {'friends': ['Sun', 'Moon', 'Jupiter'], 'enemies': ['Mercury']},
        'Mercury': {'friends': ['Sun', 'Venus'], 'enemies': ['Moon']},
        'Jupiter': {'friends': ['Sun', 'Moon', 'Mars'], 'enemies': ['Mercury', 'Venus']},
        'Venus': {'friends': ['Mercury', 'Saturn'], 'enemies': ['Sun', 'Moon']},
        'Saturn': {'friends': ['Mercury', 'Venus'], 'enemies': ['Sun', 'Moon', 'Mars']}
    }
    
    planet_friends = friendships.get(planet, {})
    if sign_lord in planet_friends.get('friends', []):
        return 'Friend'
    elif sign_lord in planet_friends.get('enemies', []):
        return 'Enemy'
    else:
        return 'Neutral'


def analyze_complete_connections(data: Dict, asc_deg: float) -> List[Dict]:
    """Analyze all planetary connections"""
    lagna_sign = data['Ascendant']['rasi']
    planet_connections = []
    planets_to_analyze = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

    for planet in planets_to_analyze:
        if planet not in data:
            continue
        
        pdata = data[planet]
        longitude = pdata['longitude']
        sign = pdata['rasi']
        nakshatra = pdata['nakshatra']
        pada = pdata['pada']
        house = get_house_from_longitude(longitude, asc_deg)
        aspects = get_planet_aspects(planet, house)
        
        nak_lord = NAKSHATRA_TO_LORD[nakshatra]
        nak_lord_house = get_house_from_longitude(data[nak_lord]['longitude'], asc_deg) if nak_lord in data else '-'
        nak_lord_owns = get_planet_house_ownership(lagna_sign, nak_lord)
        
        sign_lord = SIGN_LORDS[sign]
        sign_lord_data = data.get(sign_lord, {})
        sign_lord_house = get_house_from_longitude(sign_lord_data['longitude'], asc_deg) if sign_lord_data else '-'
        sign_lord_owns = get_planet_house_ownership(lagna_sign, sign_lord)
        
        planet_owns = get_planet_house_ownership(lagna_sign, planet)
        state = determine_planetary_state(planet, sign)

        all_houses = set()
        all_houses.add(house)
        all_houses.update(planet_owns)
        if nak_lord_house != '-':
            all_houses.add(nak_lord_house)
        all_houses.update(nak_lord_owns)
        if sign_lord_house != '-':
            all_houses.add(sign_lord_house)
        all_houses.update(sign_lord_owns)
        all_houses.update(aspects)

        planet_connections.append({
            'Planet': planet,
            'Placed_House': house,
            'Sign': sign,
            'Sign_Lord': sign_lord,
            'Nakshatra': nakshatra,
            'Pada': pada,
            'Nak_Lord': nak_lord,
            'State': state,
            'Degree': round(longitude % 30, 2),
            'Retrograde': 'R' if pdata['retrograde'] else '-',
            'Planet_Owns': planet_owns,
            'Nak_Lord_In': nak_lord_house,
            'Nak_Lord_Owns': nak_lord_owns,
            'Aspects': aspects,
            'All_Connected_Houses': sorted(all_houses),
            'Total_Connections': len(all_houses)
        })

    return planet_connections


def calculate_natal_chart(dob: str, tob: str, lat: float, lon: float, tz_offset: float) -> Tuple[Dict, List[Dict], float]:
    """Calculate complete natal chart"""
    dob_date = datetime.datetime.strptime(dob, '%Y-%m-%d').date()
    tob_time = datetime.datetime.strptime(tob, '%H:%M').time()
    local_dt = datetime.datetime.combine(dob_date, tob_time)
    utc_dt = local_dt - datetime.timedelta(hours=tz_offset)
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    natal_data, natal_asc_deg, _ = get_planet_positions(jd, lat, lon)
    planet_connections = analyze_complete_connections(natal_data, natal_asc_deg)
    return natal_data, planet_connections, natal_asc_deg


# ============================================================================
# TRANSIT ANALYSIS & SCORING FUNCTIONS
# ============================================================================

def calculate_dignity_score(planet: str, sign: str, state: str) -> float:
    """Calculate score based on planetary dignity"""
    base_scores = {
        'Exalted': 100,
        'Own Sign': 90,
        'Friend': 70,
        'Neutral': 50,
        'Enemy': 30,
        'Debilitated': 10,
        'N/A': 50
    }
    return base_scores.get(state, 50)


def calculate_house_quality_score(house: int) -> float:
    """Score based on house quality"""
    if house in HOUSE_CLASSIFICATIONS['kendra'] and house in HOUSE_CLASSIFICATIONS['trikona']:
        return 100  # House 1
    elif house in HOUSE_CLASSIFICATIONS['trikona']:
        return 90  # Houses 5, 9
    elif house in HOUSE_CLASSIFICATIONS['kendra']:
        return 80  # Houses 4, 7, 10
    elif house in HOUSE_CLASSIFICATIONS['upachaya']:
        return 70  # Houses 3, 6, 10, 11
    elif house in HOUSE_CLASSIFICATIONS['dusthana']:
        return 30  # Houses 6, 8, 12
    else:
        return 50


def calculate_planetary_transit_score(planet_name: str, transit_house: int, natal_state: str, is_retrograde: bool) -> float:
    """Calculate comprehensive transit score"""
    nature = PLANETARY_NATURE.get(planet_name, {'type': 'neutral'})
    house_score = calculate_house_quality_score(transit_house)

    if nature['type'] == 'benefic':
        if transit_house in HOUSE_CLASSIFICATIONS['kendra'] + HOUSE_CLASSIFICATIONS['trikona']:
            house_score += 10
        elif transit_house in HOUSE_CLASSIFICATIONS['dusthana']:
            house_score -= 5
    elif nature['type'] == 'malefic':
        if transit_house in HOUSE_CLASSIFICATIONS['upachaya']:
            house_score += 10
        elif transit_house in HOUSE_CLASSIFICATIONS['dusthana']:
            house_score += 5
        else:
            house_score -= 10

    dignity_score = calculate_dignity_score(planet_name, '', natal_state)
    retro_modifier = 0.9 if is_retrograde and planet_name not in ['Rahu', 'Ketu'] else 1.0
    final_score = ((house_score * 0.6) + (dignity_score * 0.4)) * retro_modifier
    
    return max(0, min(100, final_score))


def get_rag_status(score: float) -> Dict:
    """Return RAG status based on score"""
    if score >= 70:
        return {'status': 'GREEN', 'emoji': '🟢', 'label': 'Positive/Supportive'}
    elif score >= 40:
        return {'status': 'AMBER', 'emoji': '🟡', 'label': 'Neutral/Mixed'}
    else:
        return {'status': 'RED', 'emoji': '🔴', 'label': 'Challenging'}


def generate_interpretation(planet: str, transit_house: int, natal_houses: List[int], 
                           activated_houses: List[int], score: float, rag: Dict) -> Dict:
    """Generate human-readable interpretation"""
    house_area = HOUSE_SIGNIFICATIONS[transit_house]['area']
    themes = ', '.join(HOUSE_SIGNIFICATIONS[transit_house]['themes'][:3])
    nature = PLANETARY_NATURE.get(planet, {'type': 'neutral'})

    if rag['status'] == 'GREEN':
        impact = f"{planet} is favorably positioned, bringing positive energy to {house_area}"
        advice = f"Good time to focus on {themes}. Take proactive steps."
    elif rag['status'] == 'AMBER':
        impact = f"{planet} brings mixed influences to {house_area}, requiring balanced approach"
        advice = f"Be mindful with {themes}. Neither push too hard nor neglect."
    else:
        impact = f"{planet} creates challenges in {house_area}, requiring patience and care"
        advice = f"Exercise caution with {themes}. Avoid major decisions."

    if len(activated_houses) > 5:
        impact += f" Wide activation across {len(activated_houses)} life areas."

    return {
        'impact': impact,
        'advice': advice,
        'life_areas': [HOUSE_SIGNIFICATIONS[h]['area'] for h in activated_houses[:3]]
    }


def calculate_overall_transit_health(all_scores: List[float]) -> Dict:
    """Calculate overall transit health"""
    if not all_scores:
        return {
            'average_score': 50.0,
            'rag': get_rag_status(50),
            'green_count': 0,
            'amber_count': 0,
            'red_count': 0,
            'total_planets': 0
        }

    avg_score = sum(all_scores) / len(all_scores)
    green_count = sum(1 for s in all_scores if s >= 70)
    red_count = sum(1 for s in all_scores if s < 40)

    return {
        'average_score': round(avg_score, 1),
        'rag': get_rag_status(avg_score),
        'green_count': green_count,
        'amber_count': len(all_scores) - green_count - red_count,
        'red_count': red_count,
        'total_planets': len(all_scores)
    }


def rank_house_activations(house_activation_data: Dict) -> List[Dict]:
    """Rank houses by activation intensity"""
    ranked = []
    for house, activations in house_activation_data.items():
        quality_score = calculate_house_quality_score(house)
        intensity = activations['count']
        planets = activations['planets']
        weighted_score = (quality_score * 0.4) + (min(intensity * 20, 100) * 0.6)

        ranked.append({
            'house': house,
            'area': HOUSE_SIGNIFICATIONS[house]['area'],
            'themes': HOUSE_SIGNIFICATIONS[house]['themes'],
            'activation_count': intensity,
            'planets': planets,
            'quality_score': quality_score,
            'weighted_score': round(weighted_score, 1),
            'rag': get_rag_status(weighted_score)
        })

    ranked.sort(key=lambda x: x['weighted_score'], reverse=True)
    return ranked


def calculate_transits(dob: str, tob: str, lat: float, lon: float, tz_offset: float, 
                       transit_date: str = None) -> Dict:
    """
    Calculate complete transit analysis for a given date.
    
    Args:
        dob: Date of birth (YYYY-MM-DD)
        tob: Time of birth (HH:MM)
        lat: Latitude
        lon: Longitude
        tz_offset: Timezone offset
        transit_date: Date for transit analysis (YYYY-MM-DD), defaults to today
    
    Returns:
        Dict with transit analysis, overall health, and house rankings
    """
    if transit_date is None:
        transit_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # Calculate natal chart
    natal_data, planet_connections, natal_asc_deg = calculate_natal_chart(dob, tob, lat, lon, tz_offset)
    
    # Convert planet_connections to dict for easy lookup
    natal_dict = {pc['Planet']: pc for pc in planet_connections}
    
    # Calculate transit positions
    transit_date_obj = datetime.datetime.strptime(transit_date, '%Y-%m-%d')
    jd = swe.julday(transit_date_obj.year, transit_date_obj.month, transit_date_obj.day, 12.0)
    transit_data, _, _ = get_planet_positions(jd, lat, lon)
    
    # Analyze transits
    detailed_analysis = []
    all_scores = []
    house_activation_count = defaultdict(int)
    house_activation_by = defaultdict(list)
    
    planets_to_analyze = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
    
    for planet_name in planets_to_analyze:
        if planet_name not in transit_data or planet_name not in natal_dict:
            continue
        
        transit_planet = transit_data[planet_name]
        natal_planet = natal_dict[planet_name]
        
        transit_house = get_house_from_longitude(transit_planet['longitude'], natal_asc_deg)
        nak = transit_planet['nakshatra']
        pada = transit_planet['pada']
        pada_lord = NAKSHATRA_TO_LORD[nak]
        
        # Get activated houses
        activated_houses = set([transit_house])
        aspects = get_planet_aspects(planet_name, transit_house)
        activated_houses.update(aspects)
        
        # Add lord's houses
        if pada_lord in natal_dict:
            lord_data = natal_dict[pada_lord]
            activated_houses.add(lord_data['Placed_House'])
            activated_houses.update(lord_data['Planet_Owns'])
        
        activated_houses = sorted(activated_houses)
        
        # Calculate score
        natal_state = natal_planet['State']
        is_retrograde = transit_planet['retrograde']
        score = calculate_planetary_transit_score(planet_name, transit_house, natal_state, is_retrograde)
        all_scores.append(score)
        
        rag = get_rag_status(score)
        interpretation = generate_interpretation(planet_name, transit_house, [natal_planet['Placed_House']], 
                                                list(activated_houses), score, rag)
        
        detailed_analysis.append({
            'planet': planet_name,
            'natal_house': natal_planet['Placed_House'],
            'transit_house': transit_house,
            'transit_sign': transit_planet['rasi'],
            'transit_degree': round(transit_planet['longitude'] % 30, 2),
            'nakshatra': nak,
            'pada': pada,
            'pada_lord': pada_lord,
            'activated_houses': list(activated_houses),
            'score': score,
            'rag': rag,
            'interpretation': interpretation
        })
        
        for house in activated_houses:
            house_activation_count[house] += 1
            house_activation_by[house].append(planet_name)
    
    # Calculate overall health
    overall_health = calculate_overall_transit_health(all_scores)
    
    # Rank houses
    house_activation_detailed = {
        house: {'count': count, 'planets': house_activation_by[house]}
        for house, count in house_activation_count.items()
    }
    house_rankings = rank_house_activations(house_activation_detailed)
    
    return {
        'transit_date': transit_date,
        'overall_health': overall_health,
        'transit_analysis': detailed_analysis,
        'house_rankings': house_rankings
    }


def calculate_auspicious_dates(dob: str, tob: str, lat: float, lon: float, tz_offset: float,
                               month: str, sav_chart: List[int] = None, top_n: int = 10) -> Dict:
    """
    Calculate auspicious dates for a given month based on Gochara and BAV/SAV.
    
    Args:
        dob: Date of birth (YYYY-MM-DD)
        tob: Time of birth (HH:MM)
        lat: Latitude
        lon: Longitude
        tz_offset: Timezone offset
        month: Month in YYYY-MM format (e.g., "2024-01")
        sav_chart: SAV chart (12 houses) to factor into scoring, optional
        top_n: Number of top dates to return (default 10)
    
    Returns:
        Dict with top dates, scores, RAG status, and reasons
    """
    import calendar
    
    # Parse month
    year, month_num = map(int, month.split('-'))
    
    # Get all dates in the month
    num_days = calendar.monthrange(year, month_num)[1]
    dates_in_month = [
        f"{year}-{month_num:02d}-{day:02d}"
        for day in range(1, num_days + 1)
    ]
    
    # Calculate natal chart once (for all dates)
    natal_data, planet_connections, natal_asc_deg = calculate_natal_chart(dob, tob, lat, lon, tz_offset)
    natal_dict = {pc['Planet']: pc for pc in planet_connections}
    
    # Calculate date scores
    date_scores = []
    
    for date_str in dates_in_month:
        try:
            # Calculate transits for this date
            transit_result = calculate_transits(dob, tob, lat, lon, tz_offset, date_str)
            
            overall_health = transit_result.get('overall_health', {})
            transit_analysis = transit_result.get('transit_analysis', [])
            
            base_score = overall_health.get('average_score', 50.0)
            sav_modifier = 0.0
            sav_reasons = []
            
            # Factor in BAV/SAV if provided
            if sav_chart and len(sav_chart) == 12:
                # Check SAV for transit houses
                for transit in transit_analysis:
                    transit_house = transit.get('transit_house', 0)
                    if 1 <= transit_house <= 12:
                        sav_points = sav_chart[transit_house - 1]
                        
                        # High SAV (>30) boosts score
                        if sav_points >= 30:
                            sav_modifier += 5.0
                            sav_reasons.append(f"H{transit_house} (SAV {sav_points})")
                        # Low SAV (<22) reduces score
                        elif sav_points < 22:
                            sav_modifier -= 3.0
                            sav_reasons.append(f"H{transit_house} (SAV {sav_points})")
            
            # Apply modifier (cap at ±15 points)
            final_score = max(0, min(100, base_score + sav_modifier))
            
            # Get RAG status
            rag = get_rag_status(final_score)
            
            # Extract detailed explanations
            top_planets = sorted(
                transit_analysis,
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:5]  # Top 5 planets for detailed explanation
            
            reasons = []
            detailed_explanations = []
            planetary_details = []
            
            for planet_data in top_planets:
                planet = planet_data.get('planet', '')
                score = planet_data.get('score', 0)
                transit_house = planet_data.get('transit_house', 0)
                natal_house = planet_data.get('natal_house', 0)
                rag_status = planet_data.get('rag', {}).get('status', '')
                transit_sign = planet_data.get('transit_sign', '')
                nakshatra = planet_data.get('nakshatra', '')
                
                # Short reason for display
                if score >= 70:
                    reasons.append(f"{planet} in H{transit_house} ({rag_status})")
                
                # Detailed explanation
                explanation = f"{planet} transiting {transit_sign} in House {transit_house}"
                if natal_house:
                    explanation += f" (natal position: House {natal_house})"
                explanation += f" with score {score:.1f}/100 ({rag_status})"
                if nakshatra:
                    explanation += f" in {nakshatra} Nakshatra"
                
                detailed_explanations.append(explanation)
                
                # Store planetary details
                planetary_details.append({
                    'planet': planet,
                    'transit_house': transit_house,
                    'natal_house': natal_house,
                    'transit_sign': transit_sign,
                    'score': round(score, 1),
                    'rag': rag_status,
                    'nakshatra': nakshatra
                })
            
            # Add SAV explanation
            sav_explanation = ""
            if sav_reasons:
                reasons.append(f"SAV: {', '.join(sav_reasons[:2])}")
                if len(sav_reasons) > 0:
                    sav_explanation = f"Strong SAV houses ({', '.join(sav_reasons[:3])}) enhance planetary transits, boosting overall auspiciousness."
            
            # Create comprehensive explanation
            comprehensive_explanation = ""
            if detailed_explanations:
                comprehensive_explanation = "This date is auspicious because: "
                comprehensive_explanation += "; ".join(detailed_explanations[:3])
                if sav_explanation:
                    comprehensive_explanation += f" Additionally, {sav_explanation}"
            
            date_scores.append({
                'date': date_str,
                'score': round(final_score, 1),
                'base_score': round(base_score, 1),
                'sav_modifier': round(sav_modifier, 2) if sav_chart else 0.0,
                'rag': rag,
                'reasons': reasons[:5],  # Top 5 short reasons
                'detailed_explanation': comprehensive_explanation,
                'planetary_details': planetary_details,
                'sav_explanation': sav_explanation,
                'overall_health': overall_health,
                'transit_count': len(transit_analysis),
                'green_count': overall_health.get('green_count', 0),
                'amber_count': overall_health.get('amber_count', 0),
                'red_count': overall_health.get('red_count', 0)
            })
        except Exception as e:
            # Skip dates that fail calculation
            print(f"Error calculating date {date_str}: {e}")
            continue
    
    # Sort by date (ascending - chronological order)
    date_scores.sort(key=lambda x: x['date'])
    
    # Get top N dates by score (but keep them in chronological order)
    # First, identify top N by score
    sorted_by_score = sorted(date_scores, key=lambda x: x['score'], reverse=True)
    top_n_dates_by_score = sorted_by_score[:top_n]
    top_n_dates_set = {d['date'] for d in top_n_dates_by_score}
    
    # Filter all dates to only include top N, then sort chronologically
    top_dates_chronological = [d for d in date_scores if d['date'] in top_n_dates_set]
    top_dates_chronological.sort(key=lambda x: x['date'])
    
    return {
        'month': month,
        'total_dates_analyzed': len(date_scores),
        'top_5': top_dates_chronological[:5],
        'top_10': top_dates_chronological[:10] if top_n >= 10 else top_dates_chronological,
        'all_dates': date_scores  # All dates in chronological order
    }

