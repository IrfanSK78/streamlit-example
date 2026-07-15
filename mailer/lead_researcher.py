"""Research a job posting on the web with Claude — identify the company, the role,
the founder/decision-maker and a contact email, then draft an outreach email.

Uses Claude's server-side web search. Returns a dict or an {'error': ...} dict.
Every result is best-effort: the contact email must be verified before sending.
"""

import os
import json
import logging

from mailer.generator import (
    SENDER_NAME, SENDER_TITLE, BRAND,
    CALENDAR_LINK, WEBSITE_LINK, LINKEDIN_LINK, INSTAGRAM_LINK,
)

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-8"
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

SYSTEM_PROMPT = f"""You are a business-development research assistant for {BRAND}, a USA-based UX and \
product design studio. The sender of the outreach is {SENDER_NAME}, {SENDER_TITLE}.

About {BRAND}: we combine experienced human designers with AI-assisted processes to accelerate research, \
exploration, prototyping, and production, while our senior designers own psychology, strategy, creative \
direction, and final decisions. Our pitch is "one hire versus access to a multidisciplinary team." Services: \
UX Research & Strategy; Information Architecture; Wireframing & UX Design; UI Design & Design Systems; \
Responsive Web Design & Development; Social Media Marketing. Past brands: Nike, Walmart.ca, PepsiCo, Canon, \
Nissan, Bell.

Given a job posting (a URL and/or pasted text), do the following, using web search as needed:
1. Identify the hiring COMPANY, the ROLE title, the LOCATION, and a short summary of what the role focuses on. \
If a LinkedIn (or other) URL cannot be opened directly, search the web for the company and role to reconstruct \
the details.
2. Find the most senior relevant decision-maker to approach — ideally the FOUNDER or CEO; otherwise a Head of \
Design or equivalent design leader. Give their name and title.
3. Find a plausible PUBLIC business email for that person. Strongly prefer an address actually published on a \
public source (company website, app-store developer listing, WHOIS, press, etc.). If you can only infer it from \
the company's email pattern (e.g. first@domain), mark the confidence as "inferred". Always state where it came from.
4. Write a personalized outreach email FROM {SENDER_NAME} TO that person, in the {BRAND} house voice, addressed to \
them by first name, referencing the specific role and company and two to three concrete details from the posting. \
Warm, confident, human, ~220-340 words. Do NOT include a sign-off, a signature, a calendar link, or any URLs — \
those are appended automatically. No clichés ("I hope this finds you well", "synergy", "game-changing"), no emojis, \
no markdown.

Respond with ONLY a JSON object (no markdown, no code fences) with these fields:
"company", "role", "location", "role_summary", "contact_name", "contact_title", "contact_email", \
"email_confidence" (one of "published", "inferred", "unknown"), "email_source" (short description including the URL \
you found it on), "subject", "body", "notes" (anything the user should double-check before sending)."""


def _get_api_key():
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


def _footer():
    return (
        f"\n\nYou can schedule a time here:\n\n{CALENDAR_LINK}\n\n"
        f"Our calendar currently reflects EST availability, but we are happy to work around your "
        f"local time and find a slot that is convenient for you.\n\n"
        f"Website:\n{WEBSITE_LINK}\n\nLinkedIn:\n{LINKEDIN_LINK}\n\nInstagram:\n{INSTAGRAM_LINK}\n\n"
        f"I look forward to connecting with you.\n\nBest regards,\n\n"
        f"{SENDER_NAME}\n{SENDER_TITLE}\n{BRAND}"
    )


def _extract_json(text):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
    return None


def research_and_write(job_input):
    """Research a pasted job posting and draft an email to the decision-maker.

    Returns a dict with the research fields plus 'subject'/'body', or
    {'error': <message>} on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        return {"error": "AI is not enabled — add an Anthropic API key in the app's Secrets first."}

    try:
        import anthropic
    except Exception:
        return {"error": "The anthropic package is not installed."}

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": (
        "Here is the job posting to research (URL and/or pasted text):\n\n" + job_input.strip()
    )}]

    try:
        # Server-side web search may pause the turn between search rounds; resume up to a few times.
        response = None
        for _ in range(6):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=[WEB_SEARCH_TOOL],
            )
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue
            break
    except Exception as e:
        logger.warning(f"Lead research failed: {e}")
        return {"error": f"Research call failed: {e}"}

    text = "".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )
    data = _extract_json(text)
    if not isinstance(data, dict) or not data.get("body"):
        return {"error": "Could not parse the research result — please try again."}

    data["body"] = data["body"].strip() + _footer()
    if not (data.get("subject") or "").strip():
        data["subject"] = f"A UX and Product Design Partnership for {data.get('company') or 'your team'}"
    data["source"] = "ai_research"
    return data
