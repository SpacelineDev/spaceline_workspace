from pathlib import Path

import app.main as main

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def test_research_tool_schema_is_direct_http_and_excludes_browser_tools():
    tools = main._tool_schemas("cowork", None, True, research_only=True)
    names = {item["function"]["name"] for item in tools}
    assert names == {"web_search", "web_open_source"}


def test_web_research_language_does_not_trigger_interactive_chromium_intent():
    assert main._infer_research_task_mode("Please do deep research on agentic coding", "chat") == "deep_research"
    assert not main._browser_intent("Please do deep research on agentic coding")
    assert not main._browser_intent("Search online for the latest product details")
    assert not main._browser_intent("Do not open the browser; do deep research on this topic")
    assert main._browser_intent("Open the browser and inspect the website")
    assert main._browser_intent("Open https://example.com in Chrome and click Pricing")
    assert main._browser_intent("Open this website in the browser")
    assert not main._browser_intent("Visit https://example.com and read the article with web research")


def test_research_initial_context_uses_direct_http_search_and_source_read_tools():
    calls = []
    def handler(name, args):
        calls.append(name)
        return {"ok": True, "text": "A direct search result", "results": [{"title": "Official", "url": "https://example.com/docs"}]}
    context = main._initial_research_context("deep_research", "Research agentic coding", handler)
    assert calls == ["web_search", "web_search", "web_search"]
    assert "web_open_source" in context["content"]
    assert "browser_open" not in context["content"]


def test_research_turn_does_not_trigger_browser_snapshot_after_completion():
    assert "if (state.researchTaskActive) await refreshBrowserPage({captureScreenshot:false});" not in APP_JS
    assert "Starting the first live web search in private Chromium" not in (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "direct HTTP" in (ROOT / "app" / "main.py").read_text(encoding="utf-8")


def test_task_mode_routes_research_into_activity_and_keeps_browser_separate():
    source = APP_JS.split("function setTaskMode(", 1)[1].split("async function loadBrowserScreenshot", 1)[0]
    assert "state.workbenchTab = 'activity'" in source
    assert "Chromium stays available for explicit browser tasks" in source
    assert "openBrowserWorkbench" in APP_JS
