"""Authorize the BPDB worker to access app-created Google Drive files."""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parents[2]
SECRETS = ROOT / "secrets"
CLIENT_FILE = SECRETS / "google_oauth_client.json"
TOKEN_FILE = SECRETS / "google_drive_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main():
    if not CLIENT_FILE.is_file():
        raise SystemExit(
            "Missing secrets/google_oauth_client.json. "
            "Download a Desktop app OAuth client first."
        )

    credentials = None

    if TOKEN_FILE.is_file():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_FILE), SCOPES
        )
        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="consent",
        )

    if not credentials.refresh_token:
        raise SystemExit(
            "No refresh token received. Authorization must include "
            "offline access before scheduling the worker."
        )

    data = credentials.to_json()
    json.loads(data)

    SECRETS.mkdir(parents=True, exist_ok=True)
    temporary = TOKEN_FILE.with_suffix(".tmp")
    temporary.write_text(data, encoding="utf-8")
    temporary.replace(TOKEN_FILE)

    print("Google Drive authorization saved.")
    print("Refresh token present: yes")
    print("Credentials remain inside the ignored secrets folder.")


if __name__ == "__main__":
    main()