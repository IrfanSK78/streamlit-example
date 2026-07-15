"""Send approved emails over SMTP using only the Python standard library.

No third-party packages (avoids the dependency issues that broke the old Gmail
OAuth path). Credentials come from Streamlit secrets / environment:

    SMTP_EMAIL         = "sonia.baig@invasived.com"   # the mailbox you send from
    SMTP_APP_PASSWORD  = "abcd efgh ijkl mnop"         # a Gmail/Workspace App Password
    SMTP_FROM_NAME     = "Sonia Baig"                  # optional display name
    SMTP_HOST          = "smtp.gmail.com"              # optional (defaults to Gmail)
    SMTP_PORT          = 587                            # optional
"""

import os
import ssl
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

DEFAULT_HOST = "smtp.gmail.com"
DEFAULT_PORT = 587


def _secret(name):
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


def get_smtp_config():
    """Return the SMTP config dict if sending is configured, else None."""
    email = _secret("SMTP_EMAIL")
    password = _secret("SMTP_APP_PASSWORD")
    if not email or not password:
        return None
    return {
        "email": str(email).strip(),
        # Google shows App Passwords in 4 space-separated groups; SMTP wants them joined.
        "password": str(password).replace(" ", ""),
        "from_name": (_secret("SMTP_FROM_NAME") or "").strip() or None,
        "host": (_secret("SMTP_HOST") or DEFAULT_HOST),
        "port": int(_secret("SMTP_PORT") or DEFAULT_PORT),
    }


def is_sending_enabled():
    """True if SMTP credentials are configured."""
    return get_smtp_config() is not None


def sender_address():
    """The address emails will be sent from, or None if not configured."""
    cfg = get_smtp_config()
    return cfg["email"] if cfg else None


def send_email(to_email, subject, body):
    """Send one plain-text email. Returns {'ok': bool, 'error': str|None}."""
    cfg = get_smtp_config()
    if not cfg:
        return {"ok": False, "error": "Email sending is not set up (missing SMTP secrets)."}
    if not to_email or "@" not in str(to_email):
        return {"ok": False, "error": "No valid recipient email address."}

    msg = EmailMessage()
    from_header = f"{cfg['from_name']} <{cfg['email']}>" if cfg["from_name"] else cfg["email"]
    msg["From"] = from_header
    msg["To"] = to_email
    msg["Subject"] = subject or ""
    msg["Reply-To"] = cfg["email"]
    msg.set_content(body or "")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            server.starttls(context=context)
            server.login(cfg["email"], cfg["password"])
            server.send_message(msg)
        return {"ok": True, "error": None}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Login failed — check SMTP_EMAIL and the App Password."}
    except Exception as e:
        logger.warning(f"SMTP send failed: {e}")
        return {"ok": False, "error": str(e)}
