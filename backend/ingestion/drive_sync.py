"""Persist the daily collection journal and recent PDFs in Google Drive."""

import argparse
import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

from ingestion.daily_worker import collector_lock

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "bpdb"
SECRETS = ROOT / "secrets"
STATE_NAME = "bpdb-checkpoint-v1.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


def local_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("Unsafe checkpoint path")
    return path


def recent_revisions(journal, days):
    cutoff = datetime.now(timezone(timedelta(hours=6))).date()
    cutoff -= timedelta(days=days - 1)
    db = sqlite3.connect(journal.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row

    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Journal integrity check failed")

        result = []

        for row in db.execute("SELECT url, metadata FROM sources"):
            metadata = json.loads(row["metadata"])

            try:
                hint = date.fromisoformat(metadata.get("archive_date_hint") or "")
            except ValueError:
                continue

            if hint < cutoff:
                continue

            revision = db.execute(
                "SELECT * FROM revisions WHERE url=? ORDER BY id DESC LIMIT 1",
                (row["url"],),
            ).fetchone()

            if revision:
                result.append(dict(revision))

        return result
    finally:
        db.close()


def download(service, file_id, target):
    with target.open("wb") as handle:
        transfer = MediaIoBaseDownload(
            handle,
            service.files().get_media(fileId=file_id),
            chunksize=4 * 1024 * 1024,
        )
        done = False

        while not done:
            _, done = transfer.next_chunk(num_retries=3)


def find_files(service, folder_id, role, sha=None):
    query = (
        f"'{folder_id}' in parents and trashed=false "
        f"and appProperties has {{key='bpdb_role' and value='{role}'}}"
    )

    if sha:
        query += (
            " and appProperties has "
            f"{{key='sha256' and value='{sha}'}}"
        )

    result = service.files().list(
        q=query,
        spaces="drive",
        pageSize=100,
        fields="nextPageToken,files(id)",
    ).execute(num_retries=3)

    if result.get("nextPageToken") or len(result.get("files", [])) > 1:
        raise RuntimeError("Duplicate remote objects require review")

    return result.get("files", [])


def read_state(service, folder_id):
    matches = find_files(service, folder_id, "checkpoint")

    if not matches:
        return None, None, None

    file_id = matches[0]["id"]
    data = service.files().get_media(fileId=file_id).execute(num_retries=3)
    state = json.loads(data)

    if state.get("schema_version") != 1:
        raise ValueError("Unsupported checkpoint schema")

    return file_id, state, hashlib.sha256(data).hexdigest()


def upload_blob(service, folder_id, path):
    sha = digest(path)
    matches = find_files(service, folder_id, "blob", sha)

    if matches:
        file_id = matches[0]["id"]
    else:
        request = service.files().create(
            body={
                "name": sha + path.suffix,
                "parents": [folder_id],
                "appProperties": {"bpdb_role": "blob", "sha256": sha},
            },
            media_body=MediaFileUpload(
                str(path),
                mimetype="application/octet-stream",
                chunksize=4 * 1024 * 1024,
                resumable=True,
            ),
            fields="id",
        )

        response = None

        while response is None:
            _, response = request.next_chunk(num_retries=3)

        file_id = response["id"]

    # Verify remote bytes, including objects recovered after interruption.
    with tempfile.TemporaryDirectory() as temporary:
        copy = Path(temporary) / "verify.bin"
        download(service, file_id, copy)

        if digest(copy) != sha:
            raise ValueError("Remote blob checksum mismatch")

    return {
        "id": file_id,
        "sha256": sha,
        "size": path.stat().st_size,
    }


def push(service, folder_id, root, days, initialize):
    journal = root / "collection.sqlite3"

    if not journal.is_file():
        raise ValueError("Local collection journal is missing")

    state_id, state, remote_hash = read_state(service, folder_id)
    receipt = root / ".drive-checkpoint.json"

    if initialize:
        if state is not None:
            raise ValueError(
                "Drive is already initialized; restore before pushing"
            )
    else:
        if state is None or not receipt.is_file():
            raise ValueError(
                "Initialize once, or restore the existing checkpoint"
            )

        baseline = json.loads(receipt.read_text(encoding="utf-8"))

        if baseline["sha256"] != remote_hash:
            raise ValueError(
                "Remote checkpoint changed; do not overwrite stale state"
            )

    files = dict(state["files"]) if state else {}
    uploaded = 0

    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "journal.sqlite3"
        source = sqlite3.connect(
            journal.resolve().as_uri() + "?mode=ro",
            uri=True,
        )
        destination = sqlite3.connect(snapshot)

        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        revisions = recent_revisions(snapshot, days)

        for index, revision in enumerate(revisions, 1):
            path = local_path(root, revision["path"])

            if not path.is_file() or digest(path) != revision["sha256"]:
                raise ValueError(
                    "Missing or changed local PDF: " + revision["path"]
                )

            sha = revision["sha256"]

            if sha not in files:
                files[sha] = upload_blob(service, folder_id, path)
                uploaded += 1
            else:
                check = Path(temporary) / "existing-pdf.bin"
                download(service, files[sha]["id"], check)

                if digest(check) != sha:
                    raise ValueError("Existing Drive PDF checksum mismatch")

            print(
                f"PDF storage {index}/{len(revisions)} checked",
                flush=True,
            )

        journal_blob = upload_blob(service, folder_id, snapshot)

    # Hosted runs must also use one GitHub Actions concurrency group.
    _, _, current_hash = read_state(service, folder_id)

    if current_hash != remote_hash:
        raise RuntimeError("Another writer changed the checkpoint")

    checkpoint = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "journal": journal_blob,
        "files": files,
        "restore_days": days,
    }
    data = encode(checkpoint)
    media = MediaIoBaseUpload(
        io.BytesIO(data),
        mimetype="application/json",
    )

    if state_id:
        service.files().update(
            fileId=state_id,
            media_body=media,
        ).execute()
    else:
        service.files().create(
            body={
                "name": STATE_NAME,
                "parents": [folder_id],
                "appProperties": {"bpdb_role": "checkpoint"},
            },
            media_body=media,
        ).execute()

    _, _, saved_hash = read_state(service, folder_id)

    if saved_hash != hashlib.sha256(data).hexdigest():
        raise ValueError("Published checkpoint verification failed")

    receipt.write_bytes(encode({"sha256": saved_hash}))

    print(json.dumps({
        "status": "pushed",
        "recent_pdf_revisions": len(revisions),
        "new_pdf_blobs": uploaded,
        "archived_pdf_blobs": len(files),
        "checkpoint_verified": True,
    }, indent=2))


def pull(service, folder_id, root, days):
    if any(path.name != "collector.lock" for path in root.iterdir()):
        raise ValueError("Restore requires an empty destination directory")

    _, state, state_hash = read_state(service, folder_id)

    if state is None:
        raise ValueError(
            "No Drive checkpoint; initialize from the local archive first"
        )

    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        journal = staging / "collection.sqlite3"
        download(service, state["journal"]["id"], journal)

        if digest(journal) != state["journal"]["sha256"]:
            raise ValueError("Restored journal checksum mismatch")

        revisions = recent_revisions(journal, days)

        for index, revision in enumerate(revisions, 1):
            blob = state["files"].get(revision["sha256"])

            if not blob:
                raise ValueError(
                    "PDF is outside the archived scope; backfill required"
                )

            path = local_path(staging, revision["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            download(service, blob["id"], path)

            if digest(path) != revision["sha256"]:
                raise ValueError("Restored PDF checksum mismatch")

            print(
                f"PDF restore {index}/{len(revisions)} verified",
                flush=True,
            )

        # Copy only after every required file passed verification.
        shutil.copytree(staging, root, dirs_exist_ok=True)

    (root / ".drive-checkpoint.json").write_bytes(
        encode({"sha256": state_hash})
    )

    print(json.dumps({
        "status": "restored",
        "restored_pdf_revisions": len(revisions),
        "checksums_verified": True,
        "destination": str(root),
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("push", "pull"))
    parser.add_argument("--root", type=Path, default=RAW)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()

    if not 1 <= args.days <= 90:
        parser.error("days must be 1..90")

    if args.initialize and args.action != "push":
        parser.error("initialize is only for the first push")

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)

    config = json.loads(
        (SECRETS / "google_drive_config.json").read_text()
    )
    credentials = Credentials.from_authorized_user_file(
        str(SECRETS / "google_drive_token.json"),
        SCOPES,
    )
    credentials.refresh(Request())

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    try:
        with collector_lock(root):
            if args.action == "push":
                push(
                    service,
                    config["folder_id"],
                    root,
                    args.days,
                    args.initialize,
                )
            else:
                pull(service, config["folder_id"], root, args.days)
    finally:
        service.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())