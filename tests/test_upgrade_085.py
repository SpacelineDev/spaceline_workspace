from pathlib import Path
import tempfile

import pytest

import app.main as main
from app.workspace import Workspace


def test_explicit_provider_selection_never_rotates_to_another_profile(monkeypatch, tmp_path):
    original = main.workspace
    ws = Workspace(tmp_path)
    monkeypatch.setattr(main, "workspace", ws)
    a = ws.create_profile({"name":"Selected Gemini", "provider":"gemini", "base_url":"https://generativelanguage.googleapis.com/v1beta", "model":"gemini-selected"})
    ws.create_profile({"name":"Other OpenAI", "provider":"openai", "base_url":"https://api.openai.com/v1", "model":"other-model"})
    try:
        first = main.connection_pool_order(a["id"])
        second = main.connection_pool_order(a["id"])
        assert [p["id"] for p in first] == [a["id"]]
        assert [p["id"] for p in second] == [a["id"]]
        assert first[0]["model"] == "gemini-selected"
    finally:
        monkeypatch.setattr(main, "workspace", original)


def test_chat_message_body_accepts_all_workflow_modes():
    supported = {
        "chat", "web_search", "deep_think", "deep_research", "architect", "build",
        "debug", "review", "autonomous", "file_analysis", "data_analysis", "learn",
        "writing", "plan", "summarize",
    }
    for mode in supported:
        body = main.ChatMessageBody(content="test", task_mode=mode)
        assert body.task_mode == mode


def test_all_workflow_modes_have_distinct_instructions():
    expected = {"architect", "build", "debug", "review", "autonomous", "file_analysis",
                "data_analysis", "learn", "writing", "plan", "summarize"}
    assert expected.issubset(main.TASK_MODE_INSTRUCTIONS)
    assert len({main.TASK_MODE_INSTRUCTIONS[mode] for mode in expected}) == len(expected)


def test_architect_and_review_modes_do_not_offer_write_tools():
    architect = {item["function"]["name"] for item in main._tool_schemas("architect", "Demo", False)}
    review = {item["function"]["name"] for item in main._tool_schemas("review", "Demo", False)}
    assert "project_read_file" in architect
    assert "project_write_file" not in architect
    assert "project_run_check" not in architect
    assert "project_git_diff" in review
    assert "project_write_file" not in review


def test_build_debug_and_autonomous_modes_can_use_bounded_project_tools():
    for mode in ("build", "debug", "autonomous"):
        tools = {item["function"]["name"] for item in main._tool_schemas(mode, "Demo", False)}
        assert {"project_write_file", "project_run_check", "project_list_files"}.issubset(tools)


def test_review_git_tools_are_read_only():
    tools = {item["function"]["name"] for item in main._tool_schemas("review", "Demo", False)}
    assert {"project_git_status", "project_git_diff"}.issubset(tools)
    assert "project_write_file" not in tools


def test_long_conversation_context_is_compacted_but_recent_turns_preserved():
    messages = [{"role":"user", "content":f"User fact {i}: " + ("x" * 1800)} for i in range(45)]
    compacted = main.compact_chat_context(messages, max_chars=12000, keep_recent=10)
    assert len(compacted) < len(messages)
    assert compacted[-1]["content"] == messages[-1]["content"]
    assert any("compacted" in item.get("content", "").lower() for item in compacted if item["role"] == "system")


def test_project_write_checkpoint_preserves_previous_file_without_mutating_it(tmp_path):
    ws = Workspace(tmp_path)
    project = ws.create_project("Checkpoint Demo")
    original = "before edit\n"
    target = project / "app.py"
    target.write_text(original, encoding="utf-8")
    record = main.create_project_checkpoint(project, "app.py")
    assert target.read_text(encoding="utf-8") == original
    checkpoint_path = Path(record["backup_path"])
    assert checkpoint_path.is_file()
    assert checkpoint_path.read_text(encoding="utf-8") == original
    assert record["path"] == "app.py"


def test_assistant_replies_offer_one_copy_note_button_below_the_response():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    render_message = source.split("function renderMessage(", 1)[1].split("function renderMarkdown(", 1)[0]
    assert 'data-copy-note="${index}"' in render_message
    assert "Copy note" in render_message
    assert render_message.index('class="message-content"') < render_message.index('${copyNote}')
    assert "Copy raw code" not in source
    assert "Copy full markdown" not in source
    assert "data-copy-message" not in source
    assert "data-copy-code" not in source
    assert "data-copy-live-note" in source
    assert "copyWithFeedback(message.content, noteButton)" in source
    assert "copyWithFeedback(state.liveAnswer || '', liveButton)" in source
    assert "navigator.clipboard.writeText" in source


def test_terminal_panel_has_copy_output_control():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "copyTerminalOutput" in source
    assert 'id="copyTerminalOutput"' in source


def test_plus_menu_has_expanded_modes_and_mode_search():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "Architect" in source
    assert "Autonomous" in source
    assert "Review / Audit" in source
    assert "taskModeSearch" in source


def test_workspace_uses_requested_dark_green_charcoal_and_accessible_motion():
    css = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8")
    assert "#121614" in css
    assert "#181c1a" in css.lower()
    assert "prefers-reduced-motion" in css
    assert "spaceline-cursor" in css
