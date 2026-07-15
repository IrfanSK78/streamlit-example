"""Send emails via Google Workspace using OAuth."""

import os
import base64
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

HAS_GOOGLE_API = False

def _load_google_api():
    """Lazy load Google API libraries."""
    global HAS_GOOGLE_API
    if HAS_GOOGLE_API:
        return True

    try:
        import google.auth.exceptions
        from google.auth.transport.requests import Request as RequestClass
        from google.oauth2.credentials import Credentials
        from google.auth.oauthlib.flow import InstalledAppFlow
        from google.api_core.exceptions import GoogleAPIError
        from googleapiclient.discovery import build

        globals()['Request'] = RequestClass
        globals()['Credentials'] = Credentials
        globals()['InstalledAppFlow'] = InstalledAppFlow
        globals()['GoogleAPIError'] = GoogleAPIError
        globals()['build'] = build
        globals()['google_auth_exceptions'] = google.auth.exceptions

        HAS_GOOGLE_API = True
        return True
    except ImportError as e:
        logger.warning(f"Google API not available: {e}")
        return False

def _get_streamlit_secrets():
    """Get credentials from Streamlit secrets (for cloud deployment)."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'google_oauth' in st.secrets:
            return st.secrets['google_oauth']
    except:
        pass
    return None

def get_credentials():
    """Get valid Google credentials for Gmail."""
    if not _load_google_api():
        logger.error("Google API libraries not installed")
        return None

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                streamlit_secrets = _get_streamlit_secrets()
                if not streamlit_secrets:
                    logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                    return None

                logger.info("Using Streamlit secrets for OAuth")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds

def send_email(recipient_email, subject_line, email_body, sender_email="sonia.baig@invasived.com"):
    """
    Send email via Google Workspace Gmail.

    Args:
        recipient_email: Target email address
        subject_line: Email subject
        email_body: Plain text email body
        sender_email: From email (should be sonia.baig@invasived.com)

    Returns: {
        'success': bool,
        'message_id': Gmail message ID if sent,
        'error': error message if failed
    }
    """
    if not _load_google_api():
        return {
            'success': False,
            'message_id': None,
            'error': 'Google API libraries not installed. Run: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client'
        }

    try:
        creds = get_credentials()
        if not creds:
            return {
                'success': False,
                'message_id': None,
                'error': 'Could not obtain Google credentials. Ensure credentials.json is configured.'
            }

        service = build('gmail', 'v1', credentials=creds)

        message = {
            'raw': base64.urlsafe_b64encode(
                f"""From: {sender_email}
To: {recipient_email}
Subject: {subject_line}

{email_body}""".encode('utf-8')
            ).decode('utf-8')
        }

        result = service.users().messages().send(userId='me', body=message).execute()

        logger.info(f"Email sent to {recipient_email}, Message ID: {result.get('id')}")

        return {
            'success': True,
            'message_id': result.get('id'),
            'error': None
        }

    except google_auth_exceptions.RefreshError as e:
        logger.error(f"Authentication refresh failed: {str(e)}")
        return {
            'success': False,
            'message_id': None,
            'error': f'Authentication failed: {str(e)}. Please re-authenticate by deleting token.json.'
        }
    except GoogleAPIError as e:
        logger.error(f"Gmail API error: {str(e)}")
        return {
            'success': False,
            'message_id': None,
            'error': f'Gmail API error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return {
            'success': False,
            'message_id': None,
            'error': f'Unexpected error: {str(e)}'
        }

def test_connection():
    """Test Gmail connection."""
    if not _load_google_api():
        return False, "Google API libraries not installed"

    try:
        creds = get_credentials()
        if not creds:
            return False, "Could not obtain credentials"

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()

        email = profile.get('emailAddress', 'Unknown')
        return True, f"Connected to Gmail account: {email}"

    except Exception as e:
        return False, str(e)

def revoke_credentials():
    """Revoke credentials and delete token file."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        logger.info("Credentials revoked")
        return True
    return False
