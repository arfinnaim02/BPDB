"""Bounded archive discovery; archive dates are hints, never confirmed report dates."""

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit

import httpx
from app.core.config import get_settings
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class DiscoveredDocument:
    url: str
    label: str
    category: str
    archive_page_url: str
    archive_date_hint: str | None


def official_url(url: str) -> bool:
    p = urlsplit(url)
    return (
        p.scheme == "https"
        and p.hostname == "misc.bpdb.gov.bd"
        and p.port in (None, 443)
        and p.username is None
        and p.password is None
    )


def category(label: str) -> str:
    normalized = re.sub(r"[\s_-]+", " ", label.lower()).strip()
    match = re.search(r"page\s*([123])", normalized)
    if match:
        return "page_" + match.group(1)
    for name in ("summary", "energy", "load"):
        if re.search(r"\b" + name + r"\b", normalized):
            return name
    return "unknown"


def date_hint(text: str) -> str | None:
    # Deliberately do not infer ambiguous month-first dates or PDF operational dates.
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if not match:
        local = re.search(r"\b(\d{2})/(\d{2})/(20\d{2})\b", text)
        if not local:
            return None
        try:
            day, month, year = map(int, local.groups())
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return None


def parse_archive(html: str, page_url: str) -> tuple[list[DiscoveredDocument], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    documents: dict[str, DiscoveredDocument] = {}
    pages: set[str] = set()
    for anchor in soup.select("a[href]"):
        url = urljoin(page_url, anchor["href"])
        try:
            allowed = official_url(url)
        except ValueError:
            continue
        if not allowed:
            continue
        p = urlsplit(url)
        url = urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
        label = anchor.get_text(" ", strip=True) or anchor.get("title", "")
        if p.path.lower().endswith(".pdf"):
            row = anchor.find_parent("tr")
            document_category = category(label)
            if document_category == "unknown" and row:
                cell = anchor.find_parent(["td", "th"])
                table = row.find_parent("table")
                if cell and table:
                    cells = row.find_all(["td", "th"], recursive=False)
                    headers = table.select("thead tr:last-child th")
                    if not headers:
                        first_row = table.find("tr")
                        headers = first_row.find_all("th") if first_row else []
                    index = cells.index(cell) if cell in cells else -1
                    if 0 <= index < len(headers):
                        document_category = category(headers[index].get_text(" ", strip=True))
            documents.setdefault(
                url,
                DiscoveredDocument(
                    url=url,
                    label=label,
                    category=document_category,
                    archive_page_url=page_url,
                    archive_date_hint=date_hint(row.get_text(" ", strip=True)) if row else None,
                ),
            )
        elif p.path == urlsplit(page_url).path:
            page = parse_qs(p.query).get("page", [])
            if len(page) == 1 and page[0].isdigit() and int(page[0]) > 0:
                pages.add(url)
    return list(documents.values()), sorted(pages)


def fetch_page(client: httpx.Client, url: str) -> str:
    if not official_url(url):
        raise ValueError("Archive URL must use the official HTTPS origin")
    # Redirects are intentionally disabled: a changed origin requires source review.
    for attempt in range(3):
        try:
            response = client.get(url, follow_redirects=False)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            if "html" not in response.headers.get("content-type", "").lower():
                raise ValueError("Archive response is not HTML")
            return response.text
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Archive retries exhausted")


def discover(client: httpx.Client, start_url: str, max_pages: int = 2) -> dict:
    if not 1 <= max_pages <= 20:
        raise ValueError("Page bound must be between 1 and 20")
    queue, visited, found = [start_url], [], {}
    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        if visited:
            time.sleep(0.5)
        html = fetch_page(client, url)
        docs, pages = parse_archive(html, url)
        visited.append(url)
        for doc in docs:
            found.setdefault(doc.url, doc)
        queue.extend(p for p in pages if p not in visited and p not in queue)
    if not found:
        raise ValueError("No PDF links found; inspect source HTML before treating run as success")
    return {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "pages": visited,
        "document_count": len(found),
        "documents": [asdict(d) for d in found.values()],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    settings = get_settings()
    try:
        with httpx.Client(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": "BPDB-Research-Collector/0.1"},
        ) as client:
            result = discover(
                client, settings.bpdb_archive_url, args.max_pages or settings.discovery_max_pages
            )
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path

        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
