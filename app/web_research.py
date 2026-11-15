from __future__ import annotations

import base64
import binascii
import html
import re
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, urljoin, urlsplit

import httpx

from app.browser import _host_resolves_publicly, normalize_browser_url


class _ReadableHTML(HTMLParser):
    """Small stdlib HTML extractor; does not execute page scripts or load subresources."""

    _SKIP = {"script", "style", "noscript", "svg", "iframe", "canvas", "template", "nav", "footer"}
    _BREAK = {"br", "p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "li", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._in_title = False
        self._skip_depth = 0
        self._anchor: dict[str, str] | None = None

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): (value or "") for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = self._attrs(attrs)
        if tag in self._SKIP:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in self._BREAK:
            self.text_parts.append("\n")
        if tag == "a" and values.get("href"):
            self._anchor = {"href": values["href"], "text": ""}

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in self._BREAK:
            self.text_parts.append("\n")
        if tag == "a" and self._anchor is not None:
            label = re.sub(r"\s+", " ", self._anchor["text"]).strip()
            href = self._anchor["href"].strip()
            if label and href:
                self.links.append({"text": label[:300], "href": href[:2048]})
            self._anchor = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean = html.unescape(data)
        if self._in_title:
            self.title_parts.append(clean)
        text = clean.strip()
        if text:
            self.text_parts.append(text + " ")
        if self._anchor is not None:
            self._anchor["text"] += clean

    def result(self, base_url: str) -> dict[str, Any]:
        title = re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()
        text = re.sub(r"[ \t]+", " ", "".join(self.text_parts))
        text = re.sub(r"\n\s*\n+", "\n", text).strip()
        links: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in self.links:
            target = urljoin(base_url, item["href"])
            parsed = urlsplit(target)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                continue
            if target not in seen:
                seen.add(target)
                links.append({"text": item["text"], "href": target})
        return {"title": title[:300], "text": text[:18000], "links": links[:80], "truncated": len(text) > 18000}


class WebResearchClient:
    """Direct HTTP search and page reading for chat research, independent of Chromium."""

    SEARCH_ENGINES = (
        ("DuckDuckGo", "https://html.duckduckgo.com/html/?q="),
        ("Bing", "https://www.bing.com/search?q="),
        ("Google", "https://www.google.com/search?q="),
    )
    CHALLENGE_MARKERS = (
        "verify you are human", "verify you're human", "captcha", "robot check",
        "access denied", "unusual traffic", "before you continue to google",
    )
    MAX_RESPONSE_BYTES = 2_000_000
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 SpacelineResearch/0.9.6"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def _fetch_html(self, url: str) -> tuple[str, str, str]:
        current = normalize_browser_url(url)
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.2",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
        }
        for _redirect in range(6):
            current = normalize_browser_url(current)
            parts = urlsplit(current)
            port = parts.port or (443 if parts.scheme == "https" else 80)
            if not _host_resolves_publicly(parts.hostname or "", port):
                raise ValueError("Web research blocks local, private, or non-public network destinations.")
            with httpx.stream("GET", current, headers=headers, timeout=self.timeout, follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise RuntimeError("The source returned a redirect without a destination.")
                    current = urljoin(current, location)
                    continue
                if response.status_code < 200 or response.status_code >= 300:
                    raise RuntimeError(f"Source returned HTTP {response.status_code}.")
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise ValueError("Web research can read HTML or plain-text pages, not this file type.")
                chunks: list[bytes] = []
                total_bytes = 0
                for chunk in response.iter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > self.MAX_RESPONSE_BYTES:
                        raise ValueError("The source page is too large to read safely (limit 2 MB).")
                    chunks.append(chunk)
                encoding = response.encoding or "utf-8"
                return current, b"".join(chunks).decode(encoding, errors="replace"), content_type
        raise RuntimeError("The source redirected too many times; the final destination was not opened.")

    @staticmethod
    def _parse_page(url: str, content: str, content_type: str) -> dict[str, Any]:
        if content_type == "text/plain":
            text = re.sub(r"\s+", " ", content).strip()
            return {"url": url, "title": urlsplit(url).hostname or "Text page", "text": text[:18000], "links": [], "truncated": len(text) > 18000}
        parser = _ReadableHTML()
        parser.feed(content)
        parser.close()
        return {"url": url, **parser.result(url)}

    @staticmethod
    def _unwrap_search_url(value: str) -> str:
        absolute = value.strip()
        parsed = urlsplit(absolute)
        params = parse_qs(parsed.query)
        if parsed.path.endswith("/url") or parsed.path == "/url":
            for key in ("q", "url"):
                if params.get(key):
                    absolute = params[key][0]
                    break
        elif "uddg" in params:
            absolute = params["uddg"][0]
        elif (parsed.path.startswith("/ck/a") or "bing.com" in (parsed.hostname or "")) and params.get("u"):
            # Bing wraps outgoing destinations in a URL-safe base64 `u` value.
            encoded = params["u"][0]
            if encoded.startswith("a1"):
                encoded = encoded[2:]
            try:
                decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8", errors="strict")
                if urlsplit(decoded).scheme in {"http", "https"}:
                    absolute = decoded
            except (ValueError, UnicodeDecodeError, binascii.Error):
                pass
        return html.unescape(absolute)

    def search(self, query: str) -> dict[str, Any]:
        term = re.sub(r"\s+", " ", str(query or "")).strip()
        if not term or len(term) > 500:
            raise ValueError("Enter a web search query (up to 500 characters).")
        failures: list[str] = []
        engine_domains = ("duckduckgo.com", "bing.com", "google.com")
        for engine, endpoint in self.SEARCH_ENGINES:
            try:
                url, content, content_type = self._fetch_html(endpoint + quote_plus(term))
                page = self._parse_page(url, content, content_type)
                sample = (page.get("title", "") + "\n" + page.get("text", "")[:1500]).casefold()
                if any(marker in sample for marker in self.CHALLENGE_MARKERS):
                    raise RuntimeError("Search provider returned an access challenge.")
                results: list[dict[str, str]] = []
                seen: set[str] = set()
                for link in page.get("links", []):
                    target = self._unwrap_search_url(link["href"])
                    parsed = urlsplit(target)
                    host = (parsed.hostname or "").lower()
                    if parsed.scheme not in {"http", "https"} or not host:
                        continue
                    if any(host == domain or host.endswith("." + domain) for domain in engine_domains):
                        continue
                    if target in seen or len(link["text"]) < 4:
                        continue
                    seen.add(target)
                    results.append({"title": link["text"], "url": target})
                    if len(results) >= 15:
                        break
                if not results:
                    raise RuntimeError("The search page did not contain readable external results.")
                return {
                    "ok": True,
                    "type": "web_search_results",
                    "query": term,
                    "search_engine": engine,
                    "url": url,
                    "title": page.get("title") or f"Search results for {term}",
                    "text": page.get("text", "")[:12000],
                    "results": results,
                    "links": [{"text": item["title"], "href": item["url"]} for item in results],
                    "search_fallbacks": failures,
                }
            except Exception as exc:
                failures.append(f"{engine}: {str(exc)[:180]}")
        raise RuntimeError("Direct web search failed across all available search providers. " + "; ".join(failures))

    def open_source(self, url: str) -> dict[str, Any]:
        final_url, content, content_type = self._fetch_html(url)
        page = self._parse_page(final_url, content, content_type)
        if not page.get("text"):
            raise RuntimeError("The source page did not contain readable text.")
        return {"ok": True, "type": "web_source", **page}
