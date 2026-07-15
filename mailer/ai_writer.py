"""Write outreach emails with Claude, tailored to each specific job posting.

Falls back gracefully (returns None) whenever the Anthropic API key is missing
or any error occurs, so the caller can drop back to the deterministic template.
"""

import os
import json
import logging

from mailer.generator import (
    SENDER_NAME, SENDER_TITLE, BRAND,
    CALENDAR_LINK, WEBSITE_LINK, LINKEDIN_LINK, INSTAGRAM_LINK,
    clean_job_title, generate_subject,
)

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = f"""You are {SENDER_NAME}, {SENDER_TITLE} at {BRAND} — a USA-based design and \
digital experience company. You write warm, professional, highly specific cold-outreach emails to \
companies that are hiring for in-house design roles, proposing {BRAND} as an external UX and product \
design partner instead of (or alongside) a single full-time hire.

About {BRAND}:
- We combine experienced human designers with AI-assisted processes to accelerate research, exploration, \
analysis, prototyping, and production — without compromising strategic or creative thinking.
- Our work is psychology-driven: we focus on how users process information, respond to visual patterns, \
build habits, navigate complex journeys, and make decisions within an experience.
- Services: UX Research & Strategy; Information Architecture & Sitemap Planning; Wireframing & User \
Experience Design; UI Design & Design Systems; Responsive Website Design and Development; Social Media Marketing.
- Brands we have worked with: Nike, Walmart.ca, PepsiCo, Canon, Nissan, and Bell.
- Core positioning: instead of relying on one full-time designer to independently cover UX research, product \
thinking, UI design, design systems, and evolving AI-assisted workflows, the company gets access to a broader \
multidisciplinary design team — "one hire versus access to a team." AI accelerates the work; experienced human \
designers remain responsible for psychology, strategy, creative direction, and final design decisions.

Your task: given a specific job posting, write a tailored outreach email.

Rules:
- Open with exactly the greeting the user provides.
- Reference the SPECIFIC role and company, and weave in two to four concrete details drawn from the actual job \
description (real responsibilities, focus areas, product context). It must read as written for THIS posting, not a \
generic template.
- Introduce yourself and {BRAND} early.
- Include the "one hire versus a team" positioning and the AI-plus-human framing.
- Naturally mention a few relevant services and, briefly, the notable brands.
- Warm, confident, and human; concise but complete (roughly 220-360 words). Professional business English.
- End with one short sentence inviting a conversation or call. Do NOT write a sign-off, your name, a calendar link, \
or any URLs — those are appended automatically after your text.
- Never use clichés or filler: no "I hope this finds you well", "game-changing", "revolutionary", "synergy", \
"circle back", "touch base", or "leverage". No emojis. No markdown. No bracketed placeholders.

Respond with ONLY a JSON object (no markdown, no code fences, no commentary) with two fields: "subject" \
(a concise, specific subject line for this company and role) and "body" (the email text from the greeting \
through the closing invitation, with paragraphs separated by blank lines)."""


def _extract_json(text):
    """Parse a JSON object from the model response, tolerating stray wrapping text."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def _get_api_key():
    """Resolve the Anthropic API key from Streamlit secrets or the environment."""
    try:
        import streamlit as st
        secrets = st.secrets
        if "anthropic" in secrets and "api_key" in secrets["anthropic"]:
            return secrets["anthropic"]["api_key"]
        if "ANTHROPIC_API_KEY" in secrets:
            return secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def is_ai_available():
    """True if an Anthropic API key is configured (AI writing is possible)."""
    return bool(_get_api_key())


def _footer():
    """Deterministic calendar / links / signature block appended to every email."""
    return (
        f"\n\nYou can schedule a time here:\n\n{CALENDAR_LINK}\n\n"
        f"Our calendar currently reflects EST availability, but we are happy to work around your "
        f"local time and find a slot that is convenient for you.\n\n"
        f"Website:\n{WEBSITE_LINK}\n\nLinkedIn:\n{LINKEDIN_LINK}\n\nInstagram:\n{INSTAGRAM_LINK}\n\n"
        f"I look forward to connecting with you.\n\nBest regards,\n\n"
        f"{SENDER_NAME}\n{SENDER_TITLE}\n{BRAND}"
    )


def write_email(job_title, job_description, company_name, recipient_email=None, contact_name=None):
    """Write a job-specific outreach email with Claude.

    Returns a dict with 'subject', 'body', 'themes', 'recipient', 'source', or
    None if the API key is missing or the call fails (caller falls back to the
    deterministic template).
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        import anthropic
    except Exception as e:
        logger.warning(f"anthropic package not available: {e}")
        return None

    title = clean_job_title(job_title)
    company = (company_name or "").strip()
    first_name = contact_name.strip().split()[0] if contact_name and contact_name.strip() else None
    greeting = f"Hi {first_name}," if first_name else "Hello,"

    user_prompt = (
        f"Company: {company or 'Unknown'}\n"
        f"Role / job title: {title}\n"
        f"Greeting to open with: {greeting}\n\n"
        f"Job posting content:\n\"\"\"\n{(job_description or '')[:4000]}\n\"\"\""
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if not text:
            return None
        data = _extract_json(text)
        if not isinstance(data, dict):
            return None
    except Exception as e:
        logger.warning(f"AI email generation failed, falling back to template: {e}")
        return None

    body = (data.get("body") or "").strip()
    if len(body) < 80:
        return None
    subject = (data.get("subject") or "").strip() or generate_subject(company)

    return {
        "subject": subject,
        "body": body + _footer(),
        "themes": [],
        "recipient": recipient_email,
        "source": "ai",
    }
