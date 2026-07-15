"""Score and qualify leads based on job posting analysis."""

from datetime import datetime

def score_lead(job_title, job_description, date_posted, company_website, date_discovered):
    """Score a lead 0-100."""
    score = 0
    factors = {}
    score += score_recency(date_posted, date_discovered)
    score += score_role_match(job_title)
    score += score_design_keywords(job_description)
    score += score_responsibility_breadth(job_description)
    score += score_underresourced_signals(job_description)
    score += score_company_complexity(company_website)
    recommendation = "Strong fit - High priority outreach" if score >= 80 else \
                     "Good fit - Priority outreach" if score >= 70 else \
                     "Possible fit - Consider outreach" if score >= 60 else \
                     "Weak fit - Lower priority"
    return {
        'score': min(100, score),
        'recommendation': recommendation,
        'factors': factors
    }

def score_recency(date_posted, date_discovered):
    """Score based on job posting recency (0-20 points)."""
    if not date_posted:
        return 10
    try:
        posted = datetime.fromisoformat(date_posted)
        discovered = datetime.fromisoformat(date_discovered)
        days_old = (discovered - posted).days
        if days_old < 7:
            return 20
        elif days_old < 30:
            return 15
        elif days_old < 90:
            return 10
        else:
            return 5
    except:
        return 10

def score_role_match(job_title):
    """Score based on UX/UI design role keywords (0-15 points)."""
    if not job_title:
        return 0
    title_lower = job_title.lower()
    ux_keywords = ['ux', 'ui', 'user experience', 'user interface', 'interaction', 'design', 'designer']
    matches = sum(1 for kw in ux_keywords if kw in title_lower)
    if matches >= 2:
        return 15
    elif matches == 1:
        return 10
    else:
        return 0

def score_design_keywords(job_description):
    """Score based on design-related keywords (0-15 points)."""
    if not job_description:
        return 0
    desc_lower = job_description.lower()
    design_keywords = ['ux', 'ui', 'user experience', 'user interface', 'interaction design',
        'information architecture', 'wireframe', 'prototyping', 'figma', 'sketch',
        'design system', 'component library', 'usability', 'accessibility', 'wcag']
    matches = sum(1 for kw in design_keywords if kw in desc_lower)
    return min(15, matches * 2)

def score_responsibility_breadth(job_description):
    """Score based on breadth of responsibilities (0-30 points)."""
    if not job_description:
        return 0
    desc_lower = job_description.lower()
    responsibility_keywords = {
        'research': 2, 'strategy': 2, 'leadership': 3, 'mentoring': 2,
        'cross-functional': 3, 'stakeholder': 2, 'roadmap': 3,
        'product': 2, 'brand': 2, 'analytics': 2, 'usability testing': 3
    }
    score = 0
    for keyword, points in responsibility_keywords.items():
        if keyword in desc_lower:
            score += points
    return min(30, score)

def score_underresourced_signals(job_description):
    """Score based on underresourced signals (0-20 points)."""
    if not job_description:
        return 0
    desc_lower = job_description.lower()
    understaffed_signals = [
        'wear multiple hats', 'diverse skillset', 'generalist', 'independent',
        'self-motivated', 'problem solver', 'end-to-end', 'full stack designer',
        'startup', 'fast-paced', 'rapid growth', 'small team'
    ]
    matches = sum(1 for signal in understaffed_signals if signal in desc_lower)
    return min(20, matches * 3)

def score_company_complexity(company_website):
    """Score based on company website complexity (0-20 points)."""
    if not company_website:
        return 5
    return 10

def explain_score(score_result):
    """Provide explanation of score."""
    score = score_result['score']
    if score >= 90:
        level = 'Strong fit (90-100)'
        explanation = 'This is a high-priority lead with clear UX/UI focus.'
    elif score >= 70:
        level = 'Good fit (70-89)'
        explanation = 'This is a solid outreach opportunity with good design responsibilities.'
    elif score >= 60:
        level = 'Moderate fit (60-69)'
        explanation = 'This lead has potential with relevant design components.'
    else:
        level = 'Weak fit (below 60)'
        explanation = 'This lead may not be a strong match for outreach.'
    return f"**{level}**\n\n{explanation}"
