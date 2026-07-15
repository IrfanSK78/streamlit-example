"""Generate personalized emails for leads."""

import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def extract_key_themes(job_description, company_research=None):
    """
    Extract 2-4 key themes from job description.
    Returns: list of theme strings
    """
    if not job_description:
        return []

    desc_lower = job_description.lower()

    theme_patterns = {
        'research_focus': ['user research', 'user behavior', 'research-driven', 'understanding users', 'user testing'],
        'design_systems': ['design system', 'design tokens', 'component library', 'scalable', 'consistency'],
        'multiple_disciplines': ['research', 'strategy', 'wireframing', 'ui design', 'implementation'],
        'product_complexity': ['complex', 'multiple stakeholder', 'user journey', 'cross-functional', 'product thinking'],
        'transformation': ['digital transformation', 'redesign', 'modernize', 'evolve', 'improvement'],
        'experience_design': ['customer experience', 'ux', 'user experience', 'touchpoint', 'journey'],
        'underresourced': ['first design hire', 'solo designer', 'wear multiple hats', 'startup', 'small team'],
        'b2b': ['b2b', 'enterprise', 'saas', 'platform', 'business user'],
        'consumer': ['consumer', 'engagement', 'conversion', 'user acquisition', 'retention'],
        'mobile': ['mobile', 'app', 'responsive', 'ios', 'android'],
        'international': ['international', 'global', 'multi-market', 'localization', 'expansion'],
        'market_position': ['competitive', 'market', 'differentiation', 'competitive advantage'],
    }

    themes = []
    for theme_name, keywords in theme_patterns.items():
        for keyword in keywords:
            if keyword in desc_lower:
                themes.append(theme_name)
                break

    return list(set(themes))[:4]

def find_contact_info(job_description, company_website=None):
    """
    Try to find contact email or hiring manager info in job posting.
    Returns: {email, name, title}
    """
    if not job_description:
        return {}

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, job_description)

    result = {}

    if emails:
        result['emails'] = emails[:3]

    hiring_keywords = ['contact', 'reach out', 'apply', 'questions', 'email']
    for keyword in hiring_keywords:
        if keyword in job_description.lower():
            result['has_contact_info'] = True
            break

    return result

def generate_email(job_title, company_name, location, job_description, contact_name=None, contact_title=None, themes=None):
    """
    Generate personalized email for a lead.

    Returns: {
        'email_body': full email text,
        'subject_line': email subject,
        'valid': bool,
        'warnings': [list]
    }
    """
    from email.templates import (
        MASTER_TEMPLATE, PARAGRAPH_1_TEMPLATES, PARAGRAPH_2_TEMPLATES, PARAGRAPH_3_TEMPLATES,
        build_personalized_paragraph
    )

    if not themes:
        themes = extract_key_themes(job_description)

    person_name = contact_name or "there"

    email_body = MASTER_TEMPLATE
    email_body = email_body.replace('[PERSON_NAME]', person_name)
    email_body = email_body.replace('[COMPANY_NAME]', company_name)
    email_body = email_body.replace('[JOB_TITLE]', job_title)
    email_body = email_body.replace('[LOCATION]', location or "your location")

    para1 = build_personalized_paragraph(PARAGRAPH_1_TEMPLATES, themes, job_description, company_name)
    email_body = email_body.replace('[PERSONALIZED_PARAGRAPH_1]', para1)

    para2 = build_personalized_paragraph(PARAGRAPH_2_TEMPLATES, themes, job_description, company_name)
    email_body = email_body.replace('[PERSONALIZED_PARAGRAPH_2]', para2)

    para3 = build_personalized_paragraph(PARAGRAPH_3_TEMPLATES, themes, job_description, company_name)
    email_body = email_body.replace('[PERSONALIZED_PARAGRAPH_3]', para3)

    subject = generate_subject_line(job_title, company_name, themes)

    return {
        'email_body': email_body,
        'subject_line': subject,
        'themes': themes,
        'valid': True,
        'warnings': []
    }

def generate_subject_line(job_title, company_name, themes=None):
    """
    Generate personalized subject line.

    Returns: email subject line
    """
    if not themes:
        themes = []

    subject_templates = [
        f"UX/Product design partnership for {company_name}",
        f"Design support for {company_name}'s {job_title} role",
        f"Multidisciplinary design team for {company_name}",
        f"External UX partner for {company_name}",
        f"{company_name} design team support opportunity",
    ]

    if 'research_focus' in themes:
        return f"Design research partnership for {company_name}"
    elif 'design_systems' in themes:
        return f"Design systems expertise for {company_name}"
    elif 'international' in themes:
        return f"Global design partnership for {company_name}"

    return subject_templates[0]

def create_mime_message(recipient_email, subject_line, email_body, sender_name="Sonia Baig", sender_email="sonia.baig@invasived.com"):
    """
    Create MIME message for email.

    Returns: MIME message object
    """
    message = MIMEMultipart('alternative')
    message['Subject'] = subject_line
    message['From'] = f"{sender_name} <{sender_email}>"
    message['To'] = recipient_email

    text_part = MIMEText(email_body, 'plain', 'utf-8')
    message.attach(text_part)

    return message

def validate_email(email_body):
    """
    Validate email content.

    Returns: (is_valid, warnings)
    """
    warnings = []

    forbidden = [
        "I hope this email finds you well",
        "game-changing",
        "revolutionary",
        "synergy",
        "impressed by your innovative",
    ]

    for phrase in forbidden:
        if phrase.lower() in email_body.lower():
            warnings.append(f"Contains forbidden phrase: '{phrase}'")

    if email_body.count('[') > 3:
        warnings.append("Email contains unfilled placeholders")

    return len(warnings) == 0, warnings
