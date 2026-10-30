"""Collect original BPDB PDFs. Does not extract measurements or write to Neon."""

import argparse
import hashlib
import io
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import httpx
from pypdf import PdfReader

from ingestion.discovery import official_url, parse_archive
from ingestion.http import create_client

ARCHIVE = "https://misc.bpdb.gov.bd/daily-generation-archive"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 30 * 1024 * 1024


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".part")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def request_bytes(client, url, limit):
    if not official_url(url):
        raise ValueError("Only official BPDB HTTPS URLs are allowed")

    for attempt in range(3):
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                chunks = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise ValueError("Response exceeds size limit")
                    chunks.append(chunk)
                return b"".join(chunks), response.headers.get("content-type", "")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise
            if attempt == 2:
                raise
        except (httpx.NetworkError, httpx.TimeoutException):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)

    raise RuntimeError("Request retries exhausted")


def open_journal(root):
    db = sqlite3.connect(root / "collection.sqlite3")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            url TEXT PRIMARY KEY,
            metadata TEXT NOT NULL,
            discovered_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS revisions (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            page_count INTEGER NOT NULL,
            content_type TEXT,
            retrieved_at TEXT NOT NULL,
            UNIQUE(url, sha256)
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY,
            run_id TEXT NOT NULL,
            url TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            status TEXT NOT NULL,
            error_type TEXT
        );
    """)
    return db

def scan_archive(client, db, root, max_pages, delay, daily=False):
    page = 1
    last_page = 1
    failures = []
    scanned = 0
    consecutive_known_pages = 0
    stopped_at_known_pages = False

    while page <= min(last_page, max_pages):
        url = ARCHIVE + "?" + urlencode({"page": page})
        documents = []
        new_count = 0
        try:
            data, content_type = request_bytes(client, url, 10 * 1024 * 1024)
            if "html" not in content_type.lower():
                raise ValueError("Archive response is not HTML")

            atomic_write(
                root / "archive_html" / f"{sha256(data)}.html",
                data,
            )
            documents, pagination = parse_archive(
                data.decode("utf-8-sig"), url
            )

            for link in pagination:
                values = parse_qs(urlsplit(link).query).get("page", [])
                if len(values) == 1 and values[0].isdigit():
                    last_page = max(last_page, int(values[0]))

            new_count = sum(
                db.execute(
                    "SELECT 1 FROM sources WHERE url=?",
                    (document.url,),
                ).fetchone() is None
                for document in documents
            )

            with db:
                for document in documents:
                    db.execute(
                        "INSERT INTO sources VALUES (?, ?, ?) "
                        "ON CONFLICT(url) DO UPDATE SET "
                        "metadata=excluded.metadata",
                        (
                            document.url,
                            json.dumps(vars(document)),
                            timestamp(),
                        ),
                    )

            scanned += 1
            print(
                f"Archive page {page}/{last_page}: "
                f"{len(documents)} PDF links",
                flush=True,
            )
        except (httpx.HTTPError, ValueError, UnicodeError) as exc:
            failures.append({
                "page": page,
                "error_type": type(exc).__name__,
            })
            print(
                f"Archive page {page}: FAILED "
                f"({type(exc).__name__})",
                flush=True,
            )

        if daily:
            if documents and new_count == 0:
                consecutive_known_pages += 1
            else:
                consecutive_known_pages = 0

            if consecutive_known_pages >= 3:
                stopped_at_known_pages = True
                print(
                    "Daily scan stopped after 3 consecutive pages "
                    "containing only known PDF URLs.",
                    flush=True,
                )
                break

        page += 1
        time.sleep(delay)

    return {
        "pages_scanned": scanned,
        "last_observed_page": last_page,
        "page_failures": failures,
        "safety_cap_reached": (
            last_page > max_pages and not stopped_at_known_pages
        ),
        "daily_mode": daily,
        "stopped_at_known_pages": stopped_at_known_pages,
    }


def download_pdf(client, db, root, document, refresh):
    url = document["url"]
    previous = db.execute(
        "SELECT * FROM revisions WHERE url=? ORDER BY id DESC LIMIT 1",
        (url,),
    ).fetchone()

    if previous and not refresh:
        existing = root / previous["path"]
        if existing.is_file():
            if sha256(existing.read_bytes()) == previous["sha256"]:
                return "cached"

    data, content_type = request_bytes(client, url, MAX_BYTES)
    if not data.startswith(b"%PDF-"):
        raise ValueError(
            "Unexpected PDF response: "
            f"content_type={content_type!r}, "
            f"size_bytes={len(data)}, "
            f"pdf_header_position={data.find(b'%PDF-')}, "
            f"first_120_bytes={data[:120]!r}"
        )

    page_count = len(PdfReader(io.BytesIO(data)).pages)
    if page_count < 1:
        raise ValueError("PDF contains no pages")

    digest = sha256(data)
    relative = Path("pdf") / sha256(url.encode()) / f"{digest}.pdf"
    target = root / relative

    if target.exists():
        if sha256(target.read_bytes()) != digest:
            raise ValueError("Stored PDF checksum conflict")
    else:
        atomic_write(target, data)

    with db:
        db.execute(
            "INSERT OR IGNORE INTO revisions "
            "(url,sha256,path,size_bytes,page_count,content_type,retrieved_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                url,
                digest,
                relative.as_posix(),
                len(data),
                page_count,
                content_type,
                timestamp(),
            ),
        )
    return "downloaded"


def run(args, root):
    db = open_journal(root)
    run_id = uuid4().hex
    summary = {
        "run_id": run_id,
        "started_at": timestamp(),
        "downloaded": 0,
        "cached": 0,
        "failed": 0,
        "scan": None,
    }
    try:
        with create_client() as client:
            if args.scan or args.daily:
                summary["scan"] = scan_archive(
                    client,
                    db,
                    root,
                    args.max_pages,
                    args.delay,
                    daily=args.daily,
                )

            documents = [
                json.loads(row["metadata"])
                for row in db.execute(
                    "SELECT metadata FROM sources ORDER BY url"
                )
            ]
            summary["known_sources"] = len(documents)

            inventory = {
                "exported_at": timestamp(),
                "document_count": len(documents),
                "documents": documents,
            }
            atomic_write(
                root / "source-inventory.json",
                json.dumps(inventory, indent=2).encode(),
            )

            candidates = documents

            if args.daily and not args.refresh:
                pending_urls = {
                    row["url"]
                    for row in db.execute(
                        """
                        SELECT s.url
                        FROM sources AS s
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM revisions AS r
                            WHERE r.url = s.url
                        )
                        """
                    )
                }

                candidates = [
                    document
                    for document in documents
                    if document["url"] in pending_urls
                ]

                print(
                    f"Daily collection: {len(candidates)} pending PDFs. "
                    "Previously downloaded PDFs will be skipped.",
                    flush=True,
                )

            selected = (
                candidates[:args.limit]
                if args.limit
                else candidates
            )
            summary["pending_sources"] = len(candidates)
            summary["selected_sources"] = len(selected)

            for index, document in enumerate(selected, 1):
                error_type = None
                try:
                    status = download_pdf(
                        client, db, root, document, args.refresh
                    )
                except Exception as exc:
                    status = "failed"
                    error_type = type(exc).__name__
                    print(
                        f"Download failed: {document['url']}\n"
                        f"Reason: {error_type}: {exc}",
                        flush=True,
                    )

                summary[status] += 1
                with db:
                    db.execute(
                        "INSERT INTO attempts "
                        "(run_id,url,attempted_at,status,error_type) "
                        "VALUES (?,?,?,?,?)",
                        (
                            run_id,
                            document["url"],
                            timestamp(),
                            status,
                            error_type,
                        ),
                    )

                detail = f" ({error_type})" if error_type else ""
                print(
                    f"PDF {index}/{len(selected)}: {status}{detail}",
                    flush=True,
                )
                time.sleep(args.delay)

        scan = summary["scan"]
        incomplete = (
            not documents
            or summary["failed"] > 0
            or len(selected) < len(candidates)
            or bool(scan and (
                scan["page_failures"] or scan["safety_cap_reached"]
            ))
        )
        summary["status"] = "partial" if incomplete else "finished"
        summary["finished_at"] = timestamp()

        atomic_write(
            root / f"run-{run_id}.json",
            json.dumps(summary, indent=2).encode(),
        )
        print(json.dumps(summary, indent=2))
        print(f"Collection folder: {root}")
        return 1 if incomplete else 0
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", action="store_true")
    parser.add_argument(
    "--daily",
    action="store_true",
    help="Scan recent archive pages and download only sources without saved revisions",
)
    parser.add_argument("--max-pages", type=int, default=2000)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "bpdb",
    )
    args = parser.parse_args()

    if not 1 <= args.max_pages <= 10000:
        parser.error("--max-pages must be between 1 and 10000")
    if args.limit < 0 or args.delay < 0.5:
        parser.error("--limit must be >= 0 and --delay must be >= 0.5")

    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)

    # OS lock releases automatically when the process exits or is interrupted.
    with (root / "collector.lock").open("a+b") as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)

        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                parser.exit(1, "Another collector is running.\n")
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                parser.exit(1, "Another collector is running.\n")

        return run(args, root)


if __name__ == "__main__":
    raise SystemExit(main())