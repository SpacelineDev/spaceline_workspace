from __future__ import annotations

import ipaddress
import re
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlsplit


def normalize_browser_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Enter a website address.")
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only normal HTTP or HTTPS website addresses are allowed.")
    hostname = parts.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local", ".internal", ".lan", ".home")) or "." not in hostname:
        raise ValueError("Local and private-network destinations are blocked in the embedded browser.")
    try:
        address = ipaddress.ip_address(hostname)
        if not address.is_global:
            raise ValueError("Local and private-network destinations are blocked in the embedded browser.")
    except ValueError as exc:
        if "blocked" in str(exc):
            raise
    if parts.username or parts.password:
        raise ValueError("This website address is not valid.")
    if len(raw) > 2048:
        raise ValueError("Website address is too long.")
    try:
        _ = parts.port
    except ValueError:
        raise ValueError("Website address contains an invalid port.") from None
    return raw


def _host_resolves_publicly(hostname: str, port: int) -> bool:
    """Reject DNS names resolving to any local, private, reserved or link-local IP."""
    try:
        rows = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        return False
    addresses = set()
    for row in rows:
        try:
            addresses.add(ipaddress.ip_address(row[4][0]))
        except ValueError:
            return False
    return bool(addresses) and all(address.is_global for address in addresses)


_SENSITIVE_FIELD = re.compile(
    r"password|passcode|passphrase|secret|api.?key|access.?token|refresh.?token|credit.?card|card.?number|cvv|cvc|security.?code|one.?time|\botp\b|bank.?account|routing.?number|private.?key",
    re.I,
)
_RISKY_CONTROL = re.compile(
    r"\b(submit|checkout|purchase|buy|pay|payment|delete|remove|send|transfer|place order|add to (?:cart|basket|wishlist)|confirm|book|subscribe|unsubscribe|activate|deactivate|cancel|publish|logout|sign out|like|follow|vote|archive)\b",
    re.I,
)

def parse_browser_command(command: str) -> tuple[str, dict[str, Any]]:
    """Parse a small, auditable set of plain-language browser commands.

    Browser page text is untrusted. This parser deliberately does not accept
    JavaScript, arbitrary selectors, form submission, or transaction actions.
    """
    import re
    value = re.sub(r"\s+", " ", str(command or "")).strip()
    if not value or len(value) > 1000:
        raise ValueError("Enter a browser command up to 1,000 characters.")
    low = value.lower()

    if re.match(r"^(submit|purchase|buy|pay|checkout|delete|remove|send|transfer|book|subscribe|publish|confirm|logout|sign out)\b", low):
        raise ValueError("For safety, Spaceline will not submit forms, make purchases, send messages, or perform destructive/account actions in the browser.")

    match = re.match(r"^(?:open|visit|navigate to|go to)\s+(.+)$", value, re.I)
    if match:
        target = match.group(1).strip().strip('\"\'')
        if not target:
            raise ValueError("Enter a website address to open.")
        return "open", {"target": target}

    match = re.match(r"^(?:search(?: the web)? for|search)\s+(.+)$", value, re.I)
    if match:
        return "search", {"query": match.group(1).strip().strip('\"\'')}

    match = re.match(r"^click\s+(?:on\s+)?(?:the\s+)?(?:(?:link|button|tab|menu item)\s+)?(.+?)(?:\s+(?:link|button|tab|menu item))?$", value, re.I)
    if match:
        target = match.group(1).strip().strip('\"\'')
        if _RISKY_CONTROL.search(target):
            raise ValueError("That browser control could trigger an account, transaction, or destructive action and is blocked.")
        if target:
            return "click", {"target": target}

    match = re.match(r"^(check|uncheck)\s+(?:the\s+)?(.+)$", value, re.I)
    if match:
        label = match.group(2).strip().strip('"\'')
        if not label or _SENSITIVE_FIELD.search(label) or _RISKY_CONTROL.search(label):
            raise ValueError("That checkbox is empty, sensitive or potentially destructive.")
        return match.group(1).lower(), {"label": label}

    match = re.match(r"^(?:type|enter)\s+(.+?)\s+into\s+(.+)$", value, re.I)
    if match:
        field_value, label = match.group(1).strip().strip('"\''), match.group(2).strip().strip('"\'')
        if _SENSITIVE_FIELD.search(label) or re.search(r"\b(my|the)\s+(?:password|passcode|passphrase|secret|api.?key|access.?token|refresh.?token|credit.?card|card.?number|otp)\b", field_value, re.I):
            raise ValueError("Spaceline will not fill passwords, API keys, tokens, payment details, or authentication codes in the browser.")
        if not label or not field_value or len(field_value) > 5000:
            raise ValueError("Provide a visible field label and a value up to 5,000 characters.")
        return "fill", {"label": label, "value": field_value}

    match = re.match(r"^(?:fill|type|enter)\s+(.+?)\s+with\s+(.+)$", value, re.I)
    if match:
        label, field_value = match.group(1).strip().strip('\"\''), match.group(2).strip().strip('\"\'')
        if _SENSITIVE_FIELD.search(label):
            raise ValueError("Spaceline will not fill passwords, API keys, tokens, payment details, or authentication codes in the browser.")
        if not label or not field_value or len(field_value) > 5000:
            raise ValueError("Provide a visible field label and a value up to 5,000 characters.")
        return "fill", {"label": label, "value": field_value}

    match = re.match(r"^scroll(?:\s+(up|down))?(?:\s+(\d+))?(?:\s+pages?)?$", low, re.I)
    if match:
        direction = match.group(1) or "down"
        pages = min(5, max(1, int(match.group(2) or 1)))
        return "scroll", {"direction": direction, "pages": pages}

    if re.match(r"^(?:go\s+)?back$", low):
        return "back", {}
    if re.match(r"^(?:go\s+)?forward$", low):
        return "forward", {}
    if re.match(r"^(?:read|inspect|summari[sz]e|refresh)(?:\s+(?:this|the|current))?\s*(?:page)?$", low) or low in {"what is on this page", "what's on this page"}:
        return "read", {}

    match = re.match(r"^hover\s+(?:over\s+)?(.+)$", value, re.I)
    if match:
        target = match.group(1).strip().strip('\"\'')
        if _RISKY_CONTROL.search(target):
            raise ValueError("That browser control is blocked because it may trigger an account or transaction action.")
        return "hover", {"target": target}

    match = re.match(r"^select\s+(.+?)\s+in\s+(.+)$", value, re.I)
    if match:
        option, label = match.group(1).strip().strip('\"\''), match.group(2).strip().strip('\"\'')
        if _SENSITIVE_FIELD.search(label):
            raise ValueError("Spaceline will not change password, payment, or authentication fields in the browser.")
        return "select", {"label": label, "value": option}

    raise ValueError("I couldn't map that to a safe browser action. Try: open a URL; search for a topic; click a link or button; fill a labeled field with text; scroll up/down; go back/forward; hover over text; read this page; check or uncheck a checkbox.")


class ChromeBrowser:
    """A persistent, isolated Chromium profile controlled by Spaceline through Playwright."""

    def __init__(self, profile_dir: Path):
        self.profile_dir = Path(profile_dir).expanduser().resolve()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spaceline-chrome")
        self._playwright = None
        self._context = None
        self._page = None
        self._lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False

    def _call(self, method: str, *args: Any) -> dict[str, Any]:
        return self._executor.submit(getattr(self, f"_{method}"), *args).result(timeout=45)

    def _ensure(self) -> None:
        if self._closed:
            raise RuntimeError("The embedded browser is shutting down. Restart Spaceline to use it again.")
        if self._context is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError("Embedded browser automation needs Playwright. Close Spaceline, then run: python -m pip install playwright") from None
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        try:
            # Use Playwright's managed Chromium only. Do not launch the user's
            # installed Chrome channel: Spaceline owns this headless browser and
            # renders its screenshots/readable page inside the workbench.
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir), headless=True,
                viewport={"width": 1440, "height": 900}, args=["--disable-features=Translate"],
            )
            # Apply to every request, including redirects, iframes and subresources.
            self._context.route("**/*", self._guard_request)
        except Exception:
            self._playwright.stop()
            self._playwright = None
            raise RuntimeError(
                "Could not start Spaceline's private embedded browser. Install its browser engine with `python -m playwright install chromium`, then restart Spaceline."
            ) from None
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()

    @staticmethod
    def _guard_request(route) -> None:
        try:
            url = normalize_browser_url(route.request.url)
            parts = urlsplit(url)
            port = parts.port or (443 if parts.scheme == "https" else 80)
            if not _host_resolves_publicly(parts.hostname or "", port):
                route.abort("blockedbyclient")
                return
            route.continue_()
        except Exception:
            route.abort("blockedbyclient")

    def _open(self, url: str) -> dict[str, Any]:
        self._ensure()
        self._page.goto(normalize_browser_url(url), wait_until="domcontentloaded", timeout=30000)
        return self._snapshot()

    def _snapshot(self) -> dict[str, Any]:
        self._ensure()
        try:
            title = self._page.title()
            current_url = self._page.url
            text = self._page.locator("body").inner_text(timeout=5000)
            links = self._page.locator("a[href]").evaluate_all("""items => items.map(a => ({
                text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                href: a.href
            })).filter(x => x.text && /^https?:/i.test(x.href)).slice(0, 80)""")
        except Exception as exc:
            raise RuntimeError(f"Could not inspect the current embedded browser page: {str(exc)[:180]}") from None
        return {"url": current_url, "title": title, "text": text[:16000],
                "truncated": len(text) > 16000, "links": links}

    def _search_web(self, query: str) -> dict[str, Any]:
        term = (query or "").strip()
        if not term or len(term) > 500:
            raise ValueError("Enter a web search query (up to 500 characters).")

        # A single blocked/captcha-prone engine should not make the entire research
        # workflow appear empty. Chromium remains the one private browser session;
        # only the public search destination changes between attempts.
        engines = (
            ("Google", "https://www.google.com/search?q="),
            ("Bing", "https://www.bing.com/search?q="),
            ("DuckDuckGo", "https://html.duckduckgo.com/html/?q="),
        )
        challenge_markers = (
            "our systems have detected unusual traffic",
            "detected unusual traffic from your computer network",
            "your computer or network may be sending automated queries",
            "verify you are human", "verify you're human", "you are not a robot",
            "robot check", "captcha", "access denied", "before you continue to google",
        )
        failures: list[str] = []
        for engine, endpoint in engines:
            try:
                page = self._open(endpoint + quote_plus(term))
                title = str(page.get("title", ""))
                text = str(page.get("text", ""))
                sample = (title + "\n" + text[:1800]).casefold()
                if any(marker in sample for marker in challenge_markers):
                    failures.append(f"{engine}: search challenge or access block")
                    continue
                if not text.strip() and not page.get("links"):
                    failures.append(f"{engine}: empty search response")
                    continue
                result = dict(page)
                result["search_engine"] = engine
                if failures:
                    result["search_fallbacks"] = failures[:]
                return result
            except Exception as exc:
                failures.append(f"{engine}: {str(exc)[:180]}")

        details = "; ".join(failures) or "no search engine returned evidence"
        raise RuntimeError("Web search failed across all search engines. " + details)

    def _screenshot(self) -> bytes:
        self._ensure()
        try:
            return self._page.screenshot(type="png", full_page=False, animations="disabled")
        except Exception as exc:
            raise RuntimeError(f"Could not capture the browser preview: {str(exc)[:160]}") from None

    def _click_link(self, text: str) -> dict[str, Any]:
        self._ensure()
        label = (text or "").strip()
        if not label or len(label) > 200 or _RISKY_CONTROL.search(label):
            raise ValueError("That link label is empty, too long, or potentially destructive.")
        link = self._page.get_by_role("link", name=label, exact=True).first
        if link.count() == 0:
            raise RuntimeError(f"Could not find a link named '{label}'.")
        href = link.get_attribute("href")
        if not href:
            raise RuntimeError("That link has no destination.")
        # Open only ordinary web destinations; no javascript:, file:, or data: navigation.
        from urllib.parse import urljoin
        destination = normalize_browser_url(urljoin(self._page.url, href))
        return self._open(destination)

    def _click_element(self, target: str) -> dict[str, Any]:
        self._ensure()
        label = (target or "").strip()
        if not label or len(label) > 200 or _RISKY_CONTROL.search(label):
            raise ValueError("That control is empty, too long, or potentially destructive.")
        link = self._page.get_by_role("link", name=label, exact=True).first
        if link.count():
            return self._click_link(label)
        for role in ("button", "tab", "menuitem"):
            control = self._page.get_by_role(role, name=label, exact=True).first
            if not control.count():
                continue
            details = control.evaluate("el => ({tag: el.tagName.toLowerCase(), type: (el.type || '').toLowerCase(), disabled: !!el.disabled, ariaDisabled: el.getAttribute('aria-disabled') === 'true'})")
            if details.get("disabled") or details.get("ariaDisabled") or (details.get("tag") == "button" and details.get("type") == "submit"):
                raise ValueError("Submitting or activating a disabled form control is blocked.")
            control.click(timeout=5000)
            try:
                self._page.wait_for_load_state("domcontentloaded", timeout=1800)
            except Exception:
                pass
            return self._snapshot()
        raise RuntimeError(f"No visible link, button, tab or menu item named '{label}' was found.")

    def _fill_field(self, label: str, value: str) -> dict[str, Any]:
        self._ensure()
        name = (label or "").strip()
        text = str(value or "")
        if not name or len(name) > 160 or len(text) > 5000:
            raise ValueError("Provide a visible field label and text up to 5,000 characters.")
        if _SENSITIVE_FIELD.search(name):
            raise ValueError("Filling password, token, payment, or authentication fields is blocked.")
        locator = self._page.get_by_label(name, exact=True).first
        if not locator.count():
            locator = self._page.get_by_placeholder(name, exact=True).first
        if not locator.count():
            locator = self._page.get_by_role("textbox", name=name, exact=True).first
        if not locator.count():
            raise RuntimeError(f"No field labeled or placeholdered '{name}' was found.")
        details = locator.evaluate("el => ({tag: el.tagName.toLowerCase(), type: (el.getAttribute('type') || 'text').toLowerCase(), autocomplete: (el.getAttribute('autocomplete') || '').toLowerCase(), disabled: !!el.disabled, readonly: !!el.readOnly})")
        if details.get("tag") not in {"input", "textarea"} or details.get("type") in {"password", "hidden", "file", "button", "submit", "image"} or details.get("disabled") or details.get("readonly"):
            raise ValueError("This field is not a safe, editable text field.")
        if _SENSITIVE_FIELD.search(" ".join((name, details.get("autocomplete", "")))):
            raise ValueError("Filling password, token, payment, or authentication fields is blocked.")
        locator.fill(text, timeout=5000)
        return self._snapshot()

    def _scroll(self, direction: str, pages: int = 1) -> dict[str, Any]:
        self._ensure()
        if direction not in {"up", "down"}:
            raise ValueError("Scroll direction must be up or down.")
        amount = min(5, max(1, int(pages))) * 650 * (1 if direction == "down" else -1)
        self._page.mouse.wheel(0, amount)
        self._page.wait_for_timeout(150)
        return self._snapshot()

    def _hover_element(self, target: str) -> dict[str, Any]:
        self._ensure()
        label = (target or "").strip()
        if not label or len(label) > 200 or _RISKY_CONTROL.search(label):
            raise ValueError("That target is empty, too long, or potentially destructive.")
        element = self._page.get_by_text(label, exact=True).first
        if not element.count():
            raise RuntimeError(f"Could not find visible page text '{label}'.")
        element.hover(timeout=5000)
        return self._snapshot()

    def _select_option(self, label: str, value: str) -> dict[str, Any]:
        self._ensure()
        field = (label or "").strip()
        option = (value or "").strip()
        if not field or not option or _SENSITIVE_FIELD.search(field) or _RISKY_CONTROL.search(option) or len(option) > 200:
            raise ValueError("That select field is empty, sensitive, or invalid.")
        locator = self._page.get_by_label(field, exact=True).first
        if not locator.count():
            raise RuntimeError(f"No select field labeled '{field}' was found.")
        tag = locator.evaluate("el => el.tagName.toLowerCase()")
        if tag != "select":
            raise ValueError("Only ordinary select menus can be changed.")
        locator.select_option(label=option, timeout=5000)
        return self._snapshot()

    def _set_checkbox(self, label: str, checked: bool) -> dict[str, Any]:
        self._ensure()
        name = (label or "").strip()
        if not name or len(name) > 160 or _SENSITIVE_FIELD.search(name) or _RISKY_CONTROL.search(name):
            raise ValueError("That checkbox is empty, sensitive or potentially destructive.")
        locator = self._page.get_by_role("checkbox", name=name, exact=True).first
        if not locator.count():
            locator = self._page.get_by_label(name, exact=True).first
        if not locator.count():
            raise RuntimeError(f"No checkbox labeled '{name}' was found.")
        details = locator.evaluate("el => ({tag: el.tagName.toLowerCase(), type: (el.type || '').toLowerCase(), disabled: !!el.disabled, readonly: !!el.readOnly})")
        if details.get("tag") != "input" or details.get("type") != "checkbox" or details.get("disabled"):
            raise ValueError("Only enabled, ordinary checkbox inputs can be changed.")
        locator.check(timeout=5000) if checked else locator.uncheck(timeout=5000)
        return self._snapshot()

    def _go_back(self) -> dict[str, Any]:
        self._ensure()
        self._page.go_back(wait_until="domcontentloaded", timeout=10000)
        return self._snapshot()

    def _go_forward(self) -> dict[str, Any]:
        self._ensure()
        self._page.go_forward(wait_until="domcontentloaded", timeout=10000)
        return self._snapshot()

    def _command(self, command: str) -> dict[str, Any]:
        action, args = parse_browser_command(command)
        if action == "open":
            page = self._open(normalize_browser_url(args["target"]))
        elif action == "search":
            page = self._search_web(args["query"])
        elif action == "click":
            page = self._click_element(args["target"])
        elif action == "fill":
            page = self._fill_field(args["label"], args["value"])
        elif action == "scroll":
            page = self._scroll(args["direction"], args["pages"])
        elif action == "hover":
            page = self._hover_element(args["target"])
        elif action == "check":
            page = self._set_checkbox(args["label"], True)
        elif action == "uncheck":
            page = self._set_checkbox(args["label"], False)
        elif action == "select":
            page = self._select_option(args["label"], args["value"])
        elif action == "back":
            page = self._go_back()
        elif action == "forward":
            page = self._go_forward()
        else:
            page = self._snapshot()
        return {"ok": True, "action": action, "summary": f"Browser action completed: {action}.", **page}

    def command(self, command: str) -> dict[str, Any]:
        return self._call("command", command)

    def open(self, url: str) -> dict[str, Any]:
        return self._call("open", url)

    def snapshot(self) -> dict[str, Any]:
        return self._call("snapshot")

    def search_web(self, query: str) -> dict[str, Any]:
        return self._call("search_web", query)

    def screenshot(self) -> bytes:
        return self._executor.submit(self._screenshot).result(timeout=20)

    def click_link(self, text: str) -> dict[str, Any]:
        return self._call("click_link", text)

    def close(self) -> None:
        """Close Chromium and its worker exactly once during app shutdown."""
        with self._close_lock:
            if self._closed:
                return
            self._closed = True

        def _close() -> dict[str, Any]:
            if self._context is not None:
                self._context.close()
                self._context = None
                self._page = None
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
            return {"ok": True}

        try:
            self._executor.submit(_close).result(timeout=15)
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
