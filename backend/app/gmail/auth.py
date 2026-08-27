import json
import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _paths():
    credentials_path = Path(settings.google_credentials_path).expanduser().resolve()
    token_path = Path(settings.google_token_path).expanduser().resolve()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    return credentials_path, token_path


def credentials_exist() -> bool:
    credentials_path, _ = _paths()
    return credentials_path.exists()


def token_exists() -> bool:
    _, token_path = _paths()
    return token_path.exists()


def load_credentials(interactive: bool = False) -> Credentials:
    credentials_path, token_path = _paths()
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials not found at {credentials_path}. "
            "Create Desktop App OAuth credentials and save them as credentials.json."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except OSError:
            pass

    if not creds or not creds.valid:
        if not interactive:
            raise PermissionError("Gmail is not connected yet. Use Connect Gmail first.")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True, prompt="consent")
        token_path.write_text(creds.to_json(), encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except OSError:
            pass

    return creds


def connect_interactive() -> str:
    creds = load_credentials(interactive=True)
    return str(getattr(creds, "account", "") or "connected")


def disconnect() -> None:
    _, token_path = _paths()
    if token_path.exists():
        token_path.unlink()
