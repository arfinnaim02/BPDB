"""Create the worker archive folder and verify Drive storage access."""

import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

ROOT = Path(__file__).resolve().parents[2]
SECRETS = ROOT / "secrets"
TOKEN_FILE = SECRETS / "google_drive_token.json"
CONFIG_FILE = SECRETS / "google_drive_config.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_NAME = "BPDB Intelligence Archive"
FOLDER_TYPE = "application/vnd.google-apps.folder"
MARKER = {"bpdb_role": "archive_root_v1"}


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def find_or_create_folder(service):
    if CONFIG_FILE.is_file():
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        folder_id = config["folder_id"]

        folder = service.files().get(
            fileId=folder_id,
            fields="id,mimeType,trashed,appProperties",
        ).execute(num_retries=3)

        if (
            folder.get("trashed")
            or folder.get("mimeType") != FOLDER_TYPE
            or folder.get("appProperties", {}).get("bpdb_role")
            != MARKER["bpdb_role"]
        ):
            raise RuntimeError("Saved archive folder is invalid")

        return folder_id

    query = (
        "trashed = false "
        f"and mimeType = '{FOLDER_TYPE}' "
        "and appProperties has "
        "{ key='bpdb_role' and value='archive_root_v1' }"
    )

    result = service.files().list(
        q=query,
        spaces="drive",
        pageSize=100,
        fields="nextPageToken,files(id,name)",
    ).execute(num_retries=3)

    folders = result.get("files", [])

    if result.get("nextPageToken") or len(folders) > 1:
        raise RuntimeError(
            "Multiple archive folders found; review before proceeding"
        )

    if folders:
        return folders[0]["id"]

    folder = service.files().create(
        body={
            "name": FOLDER_NAME,
            "mimeType": FOLDER_TYPE,
            "appProperties": MARKER,
        },
        fields="id",
    ).execute()

    return folder["id"]


def main():
    if not TOKEN_FILE.is_file():
        raise SystemExit(
            "Missing Drive token. Run ingestion.authorize_drive first."
        )

    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_FILE), SCOPES
    )

    if not credentials.refresh_token:
        raise SystemExit("Drive credentials have no refresh token")

    # Force a refresh to verify unattended authentication works.
    credentials.refresh(Request())

    temporary = TOKEN_FILE.with_suffix(".tmp")
    temporary.write_text(credentials.to_json(), encoding="utf-8")
    temporary.replace(TOKEN_FILE)

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    try:
        folder_id = find_or_create_folder(service)
        save_json(CONFIG_FILE, {
            "schema_version": 1,
            "folder_id": folder_id,
        })

        payload = (
            "BPDB storage verification " + uuid4().hex
        ).encode("utf-8")
        expected_hash = hashlib.sha256(payload).hexdigest()

        uploaded = service.files().create(
            body={
                "name": "storage-check-" + uuid4().hex + ".txt",
                "parents": [folder_id],
                "appProperties": {"bpdb_role": "storage_probe"},
            },
            media_body=MediaIoBaseUpload(
                io.BytesIO(payload),
                mimetype="text/plain",
                resumable=False,
            ),
            fields="id",
        ).execute()

        probe_id = uploaded["id"]

        try:
            downloaded = service.files().get_media(
                fileId=probe_id,
            ).execute(num_retries=3)

            if hashlib.sha256(downloaded).hexdigest() != expected_hash:
                raise RuntimeError("Downloaded file checksum mismatch")
        finally:
            # Delete only the temporary test file created above.
            service.files().delete(
                fileId=probe_id,
            ).execute(num_retries=3)

        print(json.dumps({
            "status": "passed",
            "token_refresh": "passed",
            "upload": "passed",
            "download_checksum": "passed",
            "temporary_file_cleanup": "passed",
            "folder_url": (
                "https://drive.google.com/drive/folders/" + folder_id
            ),
            "config_file": str(CONFIG_FILE),
        }, indent=2))

        return 0
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())