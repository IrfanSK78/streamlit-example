"""Lead qualification and scoring system."""

import re

TARGET_JOB_TITLES = [
    'ux designer', 'ui designer', 'ux/ui designer', 'ui/ux designer',
    'senior ux designer', 'senior ui designer', 'senior ux/ui designer',
    'product designer', 'senior product designer', 'lead product designer',
    'ux lead', 'ui lead', 'design lead', 'ux manager', 'design manager',
    'design systems designer', 'design systems lead',
    'interaction designer', 'digital product designer',
    'web designer', 'senior web designer',
    'experience designer', 'customer experience designer',
    'digital experience designer',
    'ux researcher', 'ux strategist', 'information architect',
    'head of design', 'design director', 'vp design',
    'branding design', 'motion graphic designer', 'motion designer'
]

DESIGN_KEYWORDS = [
    'ux research', 'ux strategy', 'information architecture',
    'user journey', 'wireframing', 'prototyping',
    'ui design', 'design systems', 'responsive design',
    'website redesign', 'digital product', 'conversion',
    'customer experience', 'digital transformation',
    'ai-assisted', 'design thinking', 'usability',
    'user behavior', 'design operations', 'user testing',
    'accessibility', 'mobile experience', 'e-commerce',
    'user research', 'design strategy', 'cross-functional'
]

COMPANY_QUALITY_KEYWORDS = [
    'scale', 'growth', 'international', 'multi-market',
    'digital', 'product', 'technology', 'innovation',
    'global', 'distributed', 'remote-first', 'expansion'
]

def is_target_role(job_title):
    """Check if job title matches target roles."""
    title_lower = job_title.lower().strip()
    for target in TARGET_JOB_TITLES:
        if target in title_lower:
            return True
    return False

def count_design_keywords(text):
    """Count how many design/UX keywords appear in text."""
    if not text:
        return 0

    text_lower = text.lower()
    count = 0

    for keyword in DESIGN_KEYWORDS:
        count += text_lower.count(keyword)

    return count

def detect_responsibility_breadth(job_description):
    """
    Detect if the role expects one person to handle a broad range of responsibilities.
    Returns: (breadth_score 0-30, keywords_found)
    """
    if not job_description:
        return 0, []

    desc_lower = job_description.lower()

    responsibility_patterns = [
        r'research.*design', r'strategy.*design',
        r'product.*design', r'ux.*ui',
        r'wireframe.*prototype', r'design.*develop',
        r'systems.*implement', r'user.*behavior',
        r'analytics.*design', r'cross-functional',
        r'end-to-end', r'full stack.*design'
    ]

    found_patterns = []
    for pattern in responsibility_patterns:
        if re.search(pattern, desc_lower):
            found_patterns.append(pattern)

    breadth_score = min(30, len(found_patterns) * 5)

    return breadth_score, found_patterns

def detect_underresourced_signals(job_description):
    """
    Detect signals that the company may be underresourced or overloading one hire.
    Returns: (signal_score 0-20, signals_found)
    """
    if not job_description:
        return 0, []

    desc_lower = job_description.lower()

    signals = {
        'must be self-motivated': 10,
        'wear multiple hats': 10,
        'startup environment': 8,
        'small design team': 10,
        'first design hire': 15,
        'build from scratch': 8,
        'solo designer': 12,
        'no design background': 5,
        'fast-paced': 6,
        'diverse responsibilities': 8,
    }

    found_signals = []
    signal_score = 0

    for signal, score in signals.items():
        if signal in desc_lower:
            found_signals.append(signal)
            signal_score += score

    return min(20, signal_score), found_signals

def assess_company_fit(company_website, company_info):
    """
    Assess company fit based on website and info.
    Returns: (company_score 0-20, observations)
    """
    observations = []
    company_score = 0

    if not company_website:
        return 0, ['No company website provided']

    website_lower = company_website.lower()

    if any(keyword in website_lower for keyword in ['complex', 'dynamic', 'interactive', 'saas', 'platform']):
        company_score += 10
        observations.append('Website suggests product/platform complexity')

    if any(keyword in website_lower for keyword in ['international', 'global', 'multi', 'expansion', 'scale']):
        company_score += 10
        observations.append('International or multi-market presence')

    return company_score, observations

def score_lead(job_title, job_description, date_posted, company_website, date_discovered):
    """
    Calculate lead fit score (0-100) based on multiple factors.

    Returns: {
        'score': 0-100,
        'factors': {name: (score, explanation)},
        'recommendation': 'QUALIFY' | 'REVIEW' | 'REJECT'
    }
    """
    factors = {}
    total_score = 0

    from datetime import datetime, timedelta

    now = datetime.fromisoformat(date_discovered)
    posted = None
    recency_score = 0

    if date_posted:
        try:
            posted = datetime.fromisoformat(date_posted)
            days_ago = (now - posted).days

            if days_ago <= 7:
                recency_score = 20
                factors['recency'] = (20, 'Posted within 7 days')
            elif days_ago <= 14:
                recency_score = 15
                factors['recency'] = (15, 'Posted within 14 days')
            elif days_ago <= 30:
                recency_score = 5
                factors['recency'] = (5, 'Posted within 30 days')
            else:
                recency_score = 0
                factors['recency'] = (0, 'Posted more than 30 days ago')
        except:
            factors['recency'] = (0, 'Date parsing error')

    total_score += recency_score

    role_match = is_target_role(job_title)
    role_score = 15 if role_match else 0
    factors['role_match'] = (role_score, f"Target role: {role_match}")
    total_score += role_score

    design_keyword_count = count_design_keywords(job_description)
    keyword_score = min(15, design_keyword_count * 2)
    factors['design_keywords'] = (keyword_score, f'Found {design_keyword_count} design keywords')
    total_score += keyword_score

    breadth_score, breadth_patterns = detect_responsibility_breadth(job_description)
    factors['responsibility_breadth'] = (breadth_score, f'Multiple responsibility areas detected')
    total_score += breadth_score

    underresource_score, underresource_signals = detect_underresourced_signals(job_description)
    factors['underresourced_signals'] = (underresource_score, f'Signals of possible underresourcing')
    total_score += underresource_score

    company_score, company_obs = assess_company_fit(company_website, None)
    factors['company_complexity'] = (company_score, 'Company complexity assessment')
    total_score += company_score

    total_score = min(100, max(0, total_score))

    if total_score >= 70:
        recommendation = 'QUALIFY'
    elif total_score >= 50:
        recommendation = 'REVIEW'
    else:
        recommendation = 'REJECT'

    return {
        'score': total_score,
        'factors': factors,
        'recommendation': recommendation
    }

def explain_score(score_result):
    """Generate human-readable score explanation."""
    lines = [
        f"Lead Fit Score: {score_result['score']}/100",
        f"Recommendation: {score_result['recommendation']}",
        "",
        "Scoring Breakdown:"
    ]

    for factor_name, (points, explanation) in score_result['factors'].items():
        lines.append(f"  - {factor_name}: +{points} ({explanation})")

    return "\n".join(lines)
