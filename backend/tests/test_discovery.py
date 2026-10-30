from pathlib import Path

import httpx
import pytest
from ingestion.discovery import date_hint, discover, fetch_page, parse_archive

URL = "https://misc.bpdb.gov.bd/daily-generation-archive"
HTML = Path(__file__).with_name("fixtures").joinpath("archive.html").read_text()


def test_relative_links_headers_date_and_deduplication():
    docs, pages = parse_archive(HTML, URL)
    assert len(docs) == 2
    assert [d.category for d in docs] == ["page_1", "summary"]
    assert all(d.archive_date_hint == "2026-10-24" for d in docs)
    assert pages == [URL + "?page=2"]


def test_invalid_date_is_null():
    assert date_hint("2026-02-31") is None
    assert date_hint("31/02/2026") is None
    assert date_hint("unknown") is None


def test_page_bound():
    seen = []

    def handle(request):
        seen.append(str(request.url))
        return httpx.Response(200, text=HTML, headers={"Content-Type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = discover(client, URL, max_pages=1)
    assert result["document_count"] == 2
    assert len(seen) == 1


def test_empty_page_is_failure():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, text="<html>maintenance</html>", headers={"Content-Type": "text/html"}
            )
        )
    ) as client:
        with pytest.raises(ValueError, match="No PDF"):
            discover(client, URL)


def test_transient_retry(monkeypatch):
    monkeypatch.setattr("ingestion.discovery.time.sleep", lambda _: None)
    statuses = iter([503, 200])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                next(statuses), text=HTML, headers={"Content-Type": "text/html"}
            )
        )
    ) as client:
        assert fetch_page(client, URL) == HTML


def test_redirect_not_followed():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"Location": "https://evil.example"})
        )
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_page(client, URL)
