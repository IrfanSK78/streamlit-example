"""Generate personalized outreach emails in the Invasive Design house style."""

import re

# --- Sender / brand details. Edit these to change every email the app writes. ---
SENDER_NAME = "Sonia Baig"
SENDER_TITLE = "Principal Business Director"
BRAND = "Invasive Design"
CALENDAR_LINK = "https://calendar.app.google/syCR3jcssgrGjgde8"
WEBSITE_LINK = "https://invasived.com"
LINKEDIN_LINK = "https://www.linkedin.com/in/irfanshaikh78"
INSTAGRAM_LINK = "https://www.instagram.com/invasived.studio"

SERVICES = [
    "UX Research & Strategy",
    "Information Architecture & Sitemap Planning",
    "Wireframing & User Experience Design",
    "UI Design & Design Systems",
    "Responsive Website Design and Development",
    "Social Media Marketing",
]

BRANDS_LINE = (
    "Our team has had the opportunity to work with brands including Nike, Walmart.ca, "
    "PepsiCo, Canon, Nissan, and Bell, bringing experience across consumer brands, retail, "
    "digital products, and customer-focused experiences."
)

THEME_KEYWORDS = {
    'research_focus': ['user research', 'research methods', 'user testing', 'qualitative', 'quantitative'],
    'design_systems': ['design system', 'component library', 'consistency', 'guidelines', 'standards'],
    'multiple_disciplines': ['multidisciplinary', 'cross-functional', 'diverse', 'interaction', 'visual design'],
    'product_complexity': ['scale', 'millions', 'platform', 'ecosystem', 'complex'],
    'transformation': ['transformation', 'redesign', 'refresh', 'modernize', 'evolution'],
    'experience_design': ['user experience', 'end-to-end', 'holistic', 'journey', 'touchpoints'],
    'underresourced': ['solo', 'small team', 'wear multiple hats', 'generalist', 'startup phase'],
}

# Phrases for the "what caught my attention" sentence, keyed by detected theme.
FOCUS_PHRASES = {
    'research_focus': 'understanding user behaviour through research',
    'design_systems': 'building scalable design systems',
    'multiple_disciplines': 'bringing multiple design disciplines together',
    'product_complexity': 'designing for scale and product complexity',
    'transformation': 'leading design transformation and modernisation',
    'experience_design': 'translating business goals into end-to-end user experiences',
    'underresourced': 'covering a wide range of design responsibilities with a lean team',
}
DEFAULT_FOCUS = [
    'understanding digital user behaviour',
    'building scalable design systems',
    'translating business goals into user experiences that influence product metrics',
]

# Short phrase for the "Given your focus on ..." fit sentence.
FIT_PHRASES = {
    'product_complexity': 'creating and scaling digital experiences across markets',
    'design_systems': 'building and scaling design systems',
    'transformation': 'evolving and modernising its digital experience',
    'experience_design': 'crafting end-to-end user experiences',
    'research_focus': 'grounding design decisions in real user research',
    'multiple_disciplines': 'bringing design disciplines together under one team',
    'underresourced': 'scaling design capacity without scaling headcount',
}
DEFAULT_FIT = 'creating and scaling digital experiences'


def extract_key_themes(job_description):
    """Extract key themes from a job description."""
    if not job_description:
        return []
    desc_lower = job_description.lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            themes.append(theme)
    return themes


def clean_job_title(job_title):
    """Tidy a scraped job title so it reads naturally inside a sentence."""
    if not job_title:
        return "design role"
    t = job_title.strip()
    # Drop anything after a pipe, en/em dash, or a spaced hyphen (board suffixes).
    t = re.split(r'\s+-\s+|[|–—]', t)[0].strip()
    # Drop a trailing "at Company" fragment the scraper may have left in.
    t = re.split(r'\s+\bat\b\s+', t, maxsplit=1)[0].strip()
    # Remove job-board filler words.
    t = re.sub(r'\b(remote jobs?|jobs?|careers?|hiring|full[- ]time|part[- ]time)\b', ' ', t, flags=re.I)
    t = re.sub(r'\s{2,}', ' ', t).strip(' -|,')
    if not t:
        return "design role"
    # Normalise ALL-CAPS or all-lowercase titles to Title Case.
    if t.islower() or t.isupper():
        t = t.title()
    # Restore common design acronyms.
    t = re.sub(r'\b(Ux|Ui|Ai)\b', lambda m: m.group(0).upper(), t)
    return t


def _article(phrase):
    """Return 'a' or 'an' to fit the following phrase."""
    p = (phrase or "").strip()
    if not p:
        return "a"
    first = p.split()[0].lower()
    # Vowel-letter words that begin with a consonant ('you') sound take 'a'.
    if first in ('ux', 'ui', 'ux/ui', 'ui/ux', 'user', 'unique', 'unified'):
        return "a"
    return "an" if p[0].lower() in 'aeiou' else "a"


def _natural_join(items):
    """Join a list into 'a, b, and c'."""
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _focus_points(themes):
    points = [FOCUS_PHRASES[t] for t in themes if t in FOCUS_PHRASES]
    return points[:3] if points else list(DEFAULT_FOCUS)


def _fit_point(themes):
    for t in themes:
        if t in FIT_PHRASES:
            return FIT_PHRASES[t]
    return DEFAULT_FIT


def generate_subject(company_name, themes=None):
    """Subject line, personalized with the company name when available."""
    company = (company_name or "").strip()
    if company:
        return f"A Flexible UX and Product Design Partnership for {company}"
    return "A Flexible UX and Product Design Partnership"


def generate_email(job_title, job_description, company_name, recipient_email=None, contact_name=None):
    """Generate a full Invasive Design outreach email in the house style.

    Personalizes the greeting (if a contact name is known), the role, the company,
    and the "focus"/"fit" sentences based on themes detected in the job description.
    The body, services, brands, and sign-off match the standard Invasive template.
    """
    themes = extract_key_themes(job_description)
    title = clean_job_title(job_title)
    company = (company_name or "").strip()
    who = company if company else "your team"

    first_name = contact_name.strip().split()[0] if contact_name and contact_name.strip() else None
    greeting = f"Hi {first_name}," if first_name else "Hello,"

    intro = (f"My name is {SENDER_NAME}, and I'm with {BRAND}, a USA-based design and digital "
             f"experience company.")

    article = _article(title)
    if company:
        opening = (f"I recently came across {company}'s opening for {article} {title} and wanted to "
                   f"reach out because I believe there may be a strong alignment between the design "
                   f"challenges your team is addressing and the way we work at {BRAND}.")
    else:
        opening = (f"I recently came across your opening for {article} {title} and wanted to reach "
                   f"out because I believe there may be a strong alignment between the design "
                   f"challenges your team is addressing and the way we work at {BRAND}.")

    attention = (f"What particularly caught my attention was {who}'s focus on "
                 f"{_natural_join(_focus_points(themes))}.")

    about = (f"At {BRAND}, we combine experienced human designers with AI-assisted processes to "
             f"accelerate research, exploration, analysis, prototyping, and production without "
             f"compromising strategic or creative thinking.")

    psychology = ("Our work is psychology-driven. We look beyond how a digital product looks and "
                  "focus on how users process information, respond to visual patterns, build habits, "
                  "navigate complex journeys, and make decisions within an experience.")

    services = "Our services include:\n\n" + "\n".join(SERVICES)

    one_hire = (f"Instead of relying on one full-time designer to independently cover UX research, "
                f"product thinking, UI design, design systems, and evolving AI-assisted workflows, "
                f"{who} could have access to a broader multidisciplinary design team.\n\n"
                f"The idea is simple: one hire versus access to a team.")

    ai_human = ("AI helps us accelerate research, exploration, analysis, and production, while "
                "experienced human designers remain responsible for psychology, strategy, creative "
                "direction, and final design decisions.")

    fit = (f"Given {who}'s focus on {_fit_point(themes)}, I believe there could be a strong fit "
           f"between our teams.")

    cta = (f"I would love to set up a quick call to introduce {BRAND} and explore whether we could "
           f"support {who} as an external UX and product design partner.\n\n"
           f"You can schedule a time here:\n\n{CALENDAR_LINK}\n\n"
           f"Our calendar currently reflects EST availability. However, we are happy to work around "
           f"your local time and schedule a call at a time that is convenient for you.")

    links = f"Website:\n{WEBSITE_LINK}\n\nLinkedIn:\n{LINKEDIN_LINK}\n\nInstagram:\n{INSTAGRAM_LINK}"

    closing = (f"I look forward to connecting with you.\n\nBest regards,\n\n"
               f"{SENDER_NAME}\n{SENDER_TITLE}\n{BRAND}")

    body = "\n\n".join([
        greeting, intro, opening, attention, about, psychology,
        services, BRANDS_LINE, one_hire, ai_human, fit, cta, links, closing,
    ])

    return {
        'subject': generate_subject(company, themes),
        'body': body,
        'themes': themes,
        'recipient': recipient_email,
    }


def validate_email_content(subject, body):
    """Validate email content against basic guidelines."""
    errors = []
    forbidden = ['I hope this finds you well', 'game-changing', 'revolutionary', 'synergy']
    content = (subject + ' ' + body).lower()
    for phrase in forbidden:
        if phrase.lower() in content:
            errors.append(f"Contains forbidden phrase: '{phrase}'")
    if '{{' in body and '}}' in body:
        errors.append("Email contains unfilled template placeholders")
    if len(body) < 100:
        errors.append("Email body is too short")
    return errors
