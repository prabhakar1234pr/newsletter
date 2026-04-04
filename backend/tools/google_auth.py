"""Shared Google OAuth/credentials helper.

Used by upload_to_gcs.py and send_email.py. Not called directly by Claude.

Handles:
- OAuth user credentials (for Gmail API)
- Service account / API key credentials (for GCS, Gemini)
- Token refresh, scope merging
"""

import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"


def get_oauth_credentials(scopes: list[str]) -> Credentials:
    """Get OAuth2 user credentials, creating or refreshing as needed.

    Args:
        scopes: List of OAuth scopes needed (e.g., gmail.send, drive.file).

    Returns:
        Valid Credentials object.

    Raises:
        FileNotFoundError: If credentials.json is missing and no valid token exists.
    """
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Refresh failed — need re-auth
                creds = _run_auth_flow(scopes)
        else:
            creds = _run_auth_flow(scopes)

        # Save the token for future use
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def _run_auth_flow(scopes: list[str]) -> Credentials:
    """Run the interactive OAuth consent flow."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_PATH}. "
            "Download it from Google Cloud Console > APIs & Services > Credentials."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), scopes)
    return flow.run_local_server(port=0)


def get_gcs_credentials():
    """Get credentials for Google Cloud Storage.

    Uses Application Default Credentials (ADC):
    1. GOOGLE_APPLICATION_CREDENTIALS env var (service account JSON)
    2. gcloud auth application-default login
    """
    import google.auth
    credentials, project = google.auth.default()
    return credentials, project


def get_env_var(key: str, required: bool = True) -> str | None:
    """Get an environment variable, optionally raising if missing."""
    val = os.getenv(key)
    if required and not val:
        raise EnvironmentError(
            f"Missing required environment variable: {key}. Add it to .env"
        )
    return val
