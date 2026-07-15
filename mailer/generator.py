"""Generate personalized outreach emails."""

def extract_key_themes(job_description):
    """Extract key themes from job description."""
    if not job_description:
        return []
    desc_lower = job_description.lower()
    themes = []
    theme_keywords = {
        'research_focus': ['user research', 'research methods', 'user testing', 'qualitative', 'quantitative'],
        'design_systems': ['design system', 'component library', 'consistency', 'guidelines', 'standards'],
        'multiple_disciplines': ['multidisciplinary', 'cross-functional', 'diverse', 'interaction', 'visual design'],
        'product_complexity': ['scale', 'millions', 'platform', 'ecosystem', 'complex'],
        'transformation': ['transformation', 'redesign', 'refresh', 'modernize', 'evolution'],
        'experience_design': ['user experience', 'end-to-end', 'holistic', 'journey', 'touchpoints'],
        'underresourced': ['solo', 'small team', 'wear multiple hats', 'generalist', 'startup phase'],
    }
    for theme, keywords in theme_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            themes.append(theme)
    return themes

def generate_email(job_title, job_description, company_name, recipient_email):
    """Generate personalized email."""
    themes = extract_key_themes(job_description)
    subject = generate_subject(job_title, company_name, themes)
    body = generate_body(job_title, company_name, job_description, themes)
    return {
        'subject': subject,
        'body': body,
        'themes': themes,
        'recipient': recipient_email
    }

def generate_subject(job_title, company_name, themes):
    """Generate personalized subject line."""
    target = company_name or 'your team'
    if 'design_systems' in themes:
        return f"Design systems expertise for {target}"
    elif 'research_focus' in themes:
        return f"UX research partnership idea - {target}"
    elif 'transformation' in themes:
        return f"Supporting {target}'s design transformation" if company_name else "Supporting your design transformation"
    elif 'underresourced' in themes:
        return f"Design support for {target}'s growth" if company_name else "Design support as you grow"
    else:
        return f"Design partnership opportunity - {target}" if company_name else "Design partnership opportunity"

def generate_body(job_title, company_name, job_description, themes):
    """Generate personalized email body."""
    where = f" at {company_name}" if company_name else ""
    opening = f"I came across your {job_title} opening{where} and was impressed by the focus on user-centered design."
    if 'underresourced' in themes:
        value_prop = "We specialize in partnering with companies to scale design capabilities without adding permanent headcount."
    elif 'design_systems' in themes:
        value_prop = "Building robust design systems requires focused expertise. We've helped companies establish scalable design patterns."
    else:
        value_prop = "External design partners can accelerate your progress by bringing specialized expertise and fresh perspective."
    closing = "I'd be curious if there's a fit to explore further. Happy to share examples of similar work we've done."
    return f"{opening}\n\n{value_prop}\n\n{closing}"

def validate_email_content(subject, body):
    """Validate email content against guidelines."""
    errors = []
    forbidden = [
        'I hope this finds you well',
        'game-changing',
        'revolutionary',
        'synergy',
    ]
    content = (subject + ' ' + body).lower()
    for phrase in forbidden:
        if phrase.lower() in content:
            errors.append(f"Contains forbidden phrase: '{phrase}'")
    if '{{' in body and '}}' in body:
        errors.append("Email contains unfilled template placeholders")
    if len(subject) > 60:
        errors.append("Subject line is too long (>60 characters)")
    if len(body) < 100:
        errors.append("Email body is too short")
    return errors
