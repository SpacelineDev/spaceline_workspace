import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path
from app.browser import ChromeBrowser, normalize_browser_url


class BrowserUrlTests(unittest.TestCase):
    def test_adds_https_to_domain_only(self):
        self.assertEqual(normalize_browser_url("example.com"), "https://example.com")

    def test_rejects_loopback_and_private_network_urls(self):
        for url in ("http://127.0.0.1:3000", "http://localhost:8000", "http://192.168.1.1", "http://169.254.169.254/latest/meta-data"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_browser_url(url)

    def test_rejects_non_web_schemes(self):
        with self.assertRaises(ValueError):
            normalize_browser_url("file:///C:/secret.txt")

    def test_rejects_missing_host(self):
        with self.assertRaises(ValueError):
            normalize_browser_url("https://")

    def test_browser_launches_headless_for_in_workspace_view(self):
        calls = {}
        class FakeContext:
            pages = [object()]
            def route(self, pattern, handler):
                calls["route"] = pattern
                calls["route_handler"] = handler
            def close(self): pass
        class FakeChromium:
            def launch_persistent_context(self, **kwargs):
                calls.update(kwargs)
                return FakeContext()
        class FakePlaywright:
            chromium = FakeChromium()
            def stop(self): pass
        class FakeStarter:
            def start(self): return FakePlaywright()
        fake_module = types.SimpleNamespace(sync_playwright=lambda: FakeStarter())
        browser = ChromeBrowser(Path("/tmp/spaceline-browser-test"))
        with patch.dict(sys.modules, {"playwright.sync_api": fake_module}):
            browser._ensure()
        self.assertIs(calls.get("headless"), True)
        self.assertNotIn("channel", calls, "Spaceline must not launch the user's installed Chrome window")
        self.assertEqual(calls.get("route"), "**/*", "Every browser request must pass the SSRF guard")
        browser.close()


    def test_rejects_javascript_and_data_urls(self):
        for url in ("javascript:alert(1)", "data:text/html,hello"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_browser_url(url)


if __name__ == "__main__":
    unittest.main()


class BrowserDnsGuardTests(unittest.TestCase):
    def test_dns_guard_rejects_hostname_with_private_resolution(self):
        from app.browser import _host_resolves_publicly
        private_row = (None, None, None, None, ("10.0.0.8", 443))
        with patch("app.browser.socket.getaddrinfo", return_value=[private_row]):
            self.assertFalse(_host_resolves_publicly("example.test", 443))

    def test_dns_guard_accepts_hostname_with_only_public_resolution(self):
        from app.browser import _host_resolves_publicly
        public_row = (None, None, None, None, ("8.8.8.8", 443))
        with patch("app.browser.socket.getaddrinfo", return_value=[public_row]):
            self.assertTrue(_host_resolves_publicly("example.test", 443))

    def test_dns_guard_rejects_mixed_public_and_private_resolution(self):
        from app.browser import _host_resolves_publicly
        rows = [(None, None, None, None, ("8.8.8.8", 443)), (None, None, None, None, ("192.168.0.10", 443))]
        with patch("app.browser.socket.getaddrinfo", return_value=rows):
            self.assertFalse(_host_resolves_publicly("example.test", 443))

class BrowserCommandParsingTests(unittest.TestCase):
    def test_parses_basic_natural_language_browser_commands(self):
        from app.browser import parse_browser_command
        cases = {
            "open https://example.com": ("open", {"target": "https://example.com"}),
            "search for python async tutorial": ("search", {"query": "python async tutorial"}),
            "click the Pricing link": ("click", {"target": "Pricing"}),
            "click on the Pricing button": ("click", {"target": "Pricing"}),
            "fill Search with green dashboards": ("fill", {"label": "Search", "value": "green dashboards"}),
            "type green dashboards into Search": ("fill", {"label": "Search", "value": "green dashboards"}),
            "check Remember me": ("check", {"label": "Remember me"}),
            "uncheck Remember me": ("uncheck", {"label": "Remember me"}),
            "scroll down": ("scroll", {"direction": "down", "pages": 1}),
            "go back": ("back", {}),
            "read this page": ("read", {}),
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertEqual(parse_browser_command(command), expected)

    def test_rejects_sensitive_or_transactional_browser_commands(self):
        from app.browser import parse_browser_command
        for command in (
            "submit the form", "buy this item", "delete my account", "enter my password into Login",
            "click checkout", "pay now", "send this message",
        ):
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_browser_command(command)

    def test_rejects_unknown_browser_commands_with_supported_examples(self):
        from app.browser import parse_browser_command
        with self.assertRaisesRegex(ValueError, "Try"):
            parse_browser_command("do something magical")

class BrowserSearchFallbackTests(unittest.TestCase):
    def test_search_uses_an_alternate_engine_when_google_shows_a_challenge(self):
        browser = ChromeBrowser(Path("/tmp/spaceline-browser-search-fallback-test"))
        pages = [
            {"title": "Google Search", "url": "https://www.google.com/search?q=test",
             "text": "Our systems have detected unusual traffic from your computer network.", "links": []},
            {"title": "Bing", "url": "https://www.bing.com/search?q=test",
             "text": "Search results for test", "links": [{"text": "Official documentation", "href": "https://example.com/docs"}]},
        ]
        with patch.object(browser, "_open", side_effect=pages) as open_page:
            result = browser._search_web("test")
        self.assertEqual(result["search_engine"], "Bing")
        self.assertEqual(result["links"][0]["href"], "https://example.com/docs")
        self.assertEqual(open_page.call_count, 2)

    def test_search_reports_all_engine_failures_instead_of_returning_a_fake_result(self):
        browser = ChromeBrowser(Path("/tmp/spaceline-browser-search-failure-test"))
        with patch.object(browser, "_open", side_effect=RuntimeError("network blocked")) as open_page:
            with self.assertRaisesRegex(RuntimeError, "all search engines"):
                browser._search_web("test")
        self.assertEqual(open_page.call_count, 3)
