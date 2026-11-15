from pathlib import Path
import re

import app.main as main

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def test_assistant_note_copy_is_single_icon_only_action_for_every_reply():
    render = APP_JS.split("function renderMessage(", 1)[1].split("function normalizeMessageCopyActions(", 1)[0]
    assert 'data-copy-note="${index}"' in render
    assert 'aria-label="Copy note"' in render
    assert 'title="Copy note"' in render
    assert 'class="message-content">${renderMarkdown(message.content)}</div>${copyNote}' in render
    assert "const NOTE_COPY_ICON = '<svg class=\"copy-note-icon\"" in APP_JS
    assert "Copy raw code" not in APP_JS
    assert "Copy full markdown" not in APP_JS
    assert "Copy all" not in APP_JS
    assert "Copy code" not in APP_JS
    assert 'data-copy-live-note' in APP_JS
    assert 'class="code-block-toolbar"><span>' in APP_JS


def test_note_action_copies_the_complete_original_markdown_reply():
    assert 'await copyWithFeedback(message.content, noteButton);' in APP_JS
    assert "const message = state.activeChat?.messages?.[Number(noteButton.dataset.copyNote)];" in APP_JS
    assert "await copyWithFeedback(state.liveAnswer || '', liveButton);" in APP_JS
    assert 'id="liveNoteAction" hidden' in APP_JS


def test_old_message_copy_controls_are_removed_and_note_action_is_normalized():
    assert "function normalizeMessageCopyActions(root)" in APP_JS
    assert "data-copy-note" in APP_JS
    assert "message-note-actions" in APP_JS
    assert "normalizeMessageCopyActions" in APP_JS


def test_web_research_does_not_open_the_visible_browser_panel_automatically():
    set_mode = APP_JS.split("function setTaskMode(", 1)[1].split("async function loadBrowserScreenshot(", 1)[0]
    open_for_task = APP_JS.split("function openWorkbenchForTask(", 1)[1].split("async function generateImage(", 1)[0]
    assert "state.workbenchTab = 'activity'" in set_mode
    assert "state.researchTaskActive" in open_for_task
    assert "state.workbenchTab = 'browser'" not in set_mode
    assert "state.workbenchTab = 'activity'" in open_for_task


def test_browser_tool_events_only_open_browser_for_explicit_interactive_requests():
    handler = APP_JS.split("if (data.tool && data.tool.startsWith('browser_'))", 1)[1].split("if (data.tool === 'project_write_file')", 1)[0]
    assert "if (state.researchTaskActive)" not in handler
    assert "state.workbenchTab='browser'" in handler
    assert "refreshBrowserPage({captureScreenshot:true})" in handler
    assert "refreshBrowserPage({captureScreenshot:false})" not in APP_JS


def test_research_modes_have_distinct_evidence_and_tool_depth_instructions():
    web = main.TASK_MODE_INSTRUCTIONS["web_search"].lower()
    deep = main.TASK_MODE_INSTRUCTIONS["deep_research"].lower()
    assert "publication date" in web or "date" in web
    assert "independent" in deep
    assert "research plan" in deep
    assert "citations" in deep or "source register" in deep


def test_deep_research_uses_more_tool_rounds_than_quick_web_search():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "research_tool_rounds" in source
    assert "max_tool_rounds=research_tool_rounds" in source
    assert "deep_research" in source and "web_search" in source


def test_assets_are_release_versioned_and_home_response_is_not_cached():
    assert re.search(r"/assets/style\.css\?v=0\.9\.6", INDEX_HTML)
    assert re.search(r"/assets/app\.js\?v=0\.9\.6", INDEX_HTML)
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '"Cache-Control": "no-store"' in source
    assert 'from app.version import APP_VERSION' in source


def test_note_copy_control_is_a_single_icon_only_note_glyph():
    render = APP_JS.split("function renderMessage(", 1)[1].split("function normalizeMessageCopyActions(", 1)[0]
    assert 'class="copy-note-button" data-copy-note="${index}"' in render
    assert "copy-note-icon" in APP_JS.split("const NOTE_COPY_ICON", 1)[1]
    assert 'aria-label="Copy note"' in render
    assert '>Copy note</button>' not in render
    assert 'copy-note-button' in (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_message_content_strips_every_legacy_interactive_copy_button():
    normalizer = APP_JS.split("function normalizeMessageCopyActions(", 1)[1].split("function renderMarkdown(", 1)[0]
    assert "row.querySelectorAll" in normalizer and '[role="button"]' in normalizer
    assert "actions.replaceChildren(note)" in normalizer


def test_switching_away_from_research_clears_research_presentation_state():
    set_mode = APP_JS.split("function setTaskMode(", 1)[1].split("async function loadBrowserScreenshot(", 1)[0]
    assert "state.researchTaskActive = ['web_search','deep_research'].includes(mode);" in set_mode


def test_manually_opening_browser_is_the_only_way_research_reveals_chromium_panel():
    tab_binding = APP_JS.split("async function bindWorkbench()", 1)[1].split("function", 1)[0]
    assert "if (button.dataset.workbenchTab === 'browser') state.researchTaskActive = false;" in tab_binding
    assert "state.researchTaskActive = false" in APP_JS.split("function openSpacelineBrowser(", 1)[1].split("function", 1)[0]


def test_browser_research_progress_never_switches_to_browser_tab_while_private_research_runs():
    handler = APP_JS.split("if (data.tool && data.tool.startsWith('browser_'))", 1)[1].split("if (data.tool === 'project_write_file')", 1)[0]
    assert "if (state.researchTaskActive)" not in handler
    assert "state.workbenchTab='browser'" in handler
    assert "refreshBrowserPage({captureScreenshot:true})" in handler
    assert "refreshBrowserPage({captureScreenshot:false})" not in APP_JS


def test_release_092_uses_unique_assets_and_current_release_markers():
    assert "/assets/style.css?v=0.9.6" in INDEX_HTML
    assert "/assets/app.js?v=0.9.6" in INDEX_HTML
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'from app.version import APP_VERSION' in source
    assert ".spaceline_ready_0.9.6" in (ROOT / "start.bat").read_text(encoding="utf-8")


def test_research_modes_run_a_live_seed_search_and_pass_evidence_to_the_model():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "def _initial_research_context(task_mode: str, prompt: str, tool_handler)" in source
    assert "_initial_research_context, effective_task_mode, body.content, live_tool_handler" in source
    assert "messages.append(initial_research_context)" in source
    context = main._initial_research_context("web_search", "  latest   AI model release  ",
        lambda name, args: {"ok": True, "text": "Search evidence", "links": [{"href": "https://example.com"}]})
    assert context["role"] == "system"
    assert "Search evidence" in context["content"]
    assert "untrusted" in context["content"].lower()


def test_initial_research_search_failure_is_reported_without_fabricating_evidence():
    context = main._initial_research_context("deep_research", "Find official docs",
        lambda name, args: (_ for _ in ()).throw(RuntimeError("browser unavailable")))
    assert context["role"] == "system"
    assert "browser unavailable" in context["content"]
    assert "do not claim" in context["content"].lower()


def test_regular_chat_does_not_trigger_an_initial_research_search():
    called = []
    result = main._initial_research_context("chat", "hello", lambda *args: called.append(args))
    assert result is None
    assert not called
