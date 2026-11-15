from __future__ import annotations

import base64
import httpx
import pytest

from app.web_research import WebResearchClient


DDG_RESULTS = '''<!doctype html><html><head><title>Search results</title></head><body>
<div class="result"><a class="result__a" href="https://example.com/official">Official documentation</a>
<a class="result__snippet">The primary documentation explains the supported workflow and API.</a></div>
<div class="result"><a class="result__a" href="https://research.example.org/report">Independent research report</a>
<a class="result__snippet">A separate study compares the approach and its limitations.</a></div>
</body></html>'''


def test_web_search_returns_structured_results_without_using_chromium(monkeypatch):
    client = WebResearchClient()
    requested = []

    def fake_fetch(url):
        requested.append(url)
        return url, DDG_RESULTS, "text/html; charset=utf-8"

    monkeypatch.setattr(client, "_fetch_html", fake_fetch)
    result = client.search("compare current coding agents")

    assert requested
    assert result["search_engine"] == "DuckDuckGo"
    assert result["query"] == "compare current coding agents"
    assert len(result["results"]) == 2
    assert result["results"][0]["url"] == "https://example.com/official"
    assert "primary documentation" in result["text"].lower()


def test_open_source_reads_page_over_http_and_extracts_clean_text(monkeypatch):
    client = WebResearchClient()
    html = '''<html><head><title>Example source</title><script>secret()</script></head>
    <body><nav>Navigation noise</nav><main><h1>Key finding</h1>
    <p>The study reports a measured improvement.</p><a href="/methods">Methodology</a></main></body></html>'''
    monkeypatch.setattr(client, "_fetch_html", lambda url: ("https://example.com/source", html, "text/html"))

    result = client.open_source("https://example.com/source")
    assert result["title"] == "Example source"
    assert "The study reports a measured improvement." in result["text"]
    assert "secret()" not in result["text"]
    assert "Navigation noise" not in result["text"]
    assert result["links"] == [{"text": "Methodology", "href": "https://example.com/methods"}]


def test_fetch_rechecks_each_redirect_destination_and_caps_redirects(monkeypatch):
    client = WebResearchClient()
    seen = []
    responses = [
        httpx.Response(302, headers={"location": "https://public.example/final"}, request=httpx.Request("GET", "https://public.example/start")),
        httpx.Response(200, headers={"content-type": "text/html"}, text="<html><title>OK</title><body>Done</body></html>", request=httpx.Request("GET", "https://public.example/final")),
    ]

    class FakeStream:
        def __init__(self, response): self.response = response
        def __enter__(self): return self.response
        def __exit__(self, *args): return False

    def fake_stream(method, url, **kwargs):
        assert method == "GET"
        seen.append(url)
        return FakeStream(responses.pop(0))

    monkeypatch.setattr("app.web_research._host_resolves_publicly", lambda host, port: True)
    monkeypatch.setattr("app.web_research.httpx.stream", fake_stream)
    final_url, html, content_type = client._fetch_html("https://public.example/start")
    assert seen == ["https://public.example/start", "https://public.example/final"]
    assert final_url == "https://public.example/final"
    assert "Done" in html
    assert content_type.startswith("text/html")


def test_fetch_rejects_local_or_non_html_targets(monkeypatch):
    client = WebResearchClient()
    with pytest.raises(ValueError, match="private-network"):
        client._fetch_html("http://127.0.0.1/admin")

    monkeypatch.setattr("app.web_research._host_resolves_publicly", lambda host, port: True)
    response = httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF", request=httpx.Request("GET", "https://public.example/file.pdf"))
    class FakeStream:
        def __enter__(self): return response
        def __exit__(self, *args): return False
    monkeypatch.setattr("app.web_research.httpx.stream", lambda *args, **kwargs: FakeStream())
    with pytest.raises(ValueError, match="HTML or plain-text"):
        client._fetch_html("https://public.example/file.pdf")


def test_bing_wrapped_search_url_is_unwrapped_to_public_destination():
    destination = "https://example.com/official"
    encoded = "a1" + base64.urlsafe_b64encode(destination.encode()).decode().rstrip("=")
    wrapped = "https://www.bing.com/ck/a?u=" + encoded
    assert WebResearchClient._unwrap_search_url(wrapped) == destination


def test_fetch_stops_streaming_as_soon_as_page_exceeds_size_limit(monkeypatch):
    client = WebResearchClient()
    request = httpx.Request("GET", "https://public.example/large")
    response = httpx.Response(
        200,
        headers={"content-type": "text/html"},
        content=b"x" * (client.MAX_RESPONSE_BYTES + 100),
        request=request,
    )
    class FakeStream:
        def __enter__(self): return response
        def __exit__(self, *args): return False
    monkeypatch.setattr("app.web_research._host_resolves_publicly", lambda host, port: True)
    monkeypatch.setattr("app.web_research.httpx.stream", lambda *args, **kwargs: FakeStream())
    with pytest.raises(ValueError, match="limit 2 MB"):
        client._fetch_html("https://public.example/large")
