from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.workspace import Workspace

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def _init_git_project(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "spaceline-tests@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Spaceline Tests"], cwd=path, check=True)
    (path / "README.md").write_text("# worktree test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True, capture_output=True)


def test_research_modes_seed_distinct_queries_and_aggregate_evidence():
    assert hasattr(main, "_research_seed_queries")
    quick = main._research_seed_queries("web_search", "Compare current agentic coding tools")
    deep = main._research_seed_queries("deep_research", "Compare current agentic coding tools")
    assert len(quick) >= 2 and len(set(quick)) == len(quick)
    assert len(deep) >= 3 and len(set(deep)) == len(deep)
    assert all(len(query) <= 500 for query in quick + deep)

    calls = []
    def handler(name, args):
        calls.append((name, args["query"]))
        return {"ok": True, "text": f"Evidence {len(calls)}", "links": [{"href": f"https://example{len(calls)}.com"}]}

    context = main._initial_research_context("deep_research", "Compare current agentic coding tools", handler)
    assert len(calls) >= 3
    assert len({query for _, query in calls}) >= 3
    assert all(name == "web_search" for name, _ in calls)
    assert "Evidence 1" in context["content"] and "Evidence 3" in context["content"]
    assert "untrusted data" in context["content"].lower()


def test_worktree_api_creates_isolated_branch_and_lists_it(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "workspace")
    project_path = workspace.create_project("Demo")
    _init_git_project(project_path)
    monkeypatch.setattr(main, "workspace", workspace)
    old_token = main.app_token
    monkeypatch.setattr(main, "app_token", "worktree-test-token")
    try:
        with TestClient(main.app) as client:
            headers = {"X-Spaceline-Token": "worktree-test-token"}
            created = client.post("/api/projects/Demo/worktrees", json={"name": "feature review"}, headers=headers)
            assert created.status_code == 200, created.text
            payload = created.json()
            alias = payload["project"]
            assert alias.startswith("wt-")
            assert payload["branch"].startswith("spaceline/")
            assert workspace.project_path(alias).is_dir()
            assert (workspace.project_path(alias) / "README.md").read_text(encoding="utf-8").startswith("# worktree")

            listed = client.get("/api/projects/Demo/worktrees", headers=headers)
            assert listed.status_code == 200, listed.text
            matches = [item for item in listed.json()["worktrees"] if item["project"] == alias]
            assert len(matches) == 1
            assert matches[0]["branch"] == payload["branch"]
    finally:
        monkeypatch.setattr(main, "app_token", old_token)


def test_worktree_api_rejects_non_git_projects_and_bad_names(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "workspace")
    workspace.create_project("Plain")
    monkeypatch.setattr(main, "workspace", workspace)
    old_token = main.app_token
    monkeypatch.setattr(main, "app_token", "worktree-test-token")
    try:
        with TestClient(main.app) as client:
            headers = {"X-Spaceline-Token": "worktree-test-token"}
            non_git = client.post("/api/projects/Plain/worktrees", json={"name": "feature"}, headers=headers)
            assert non_git.status_code in {400, 503}
            assert not list(workspace.root.glob("wt-*"))
            bad_name = client.post("/api/projects/Plain/worktrees", json={"name": "../outside"}, headers=headers)
            assert bad_name.status_code == 400
            assert not (workspace.root.parent / "outside").exists()
    finally:
        monkeypatch.setattr(main, "app_token", old_token)


def test_copy_controls_are_normalized_for_every_assistant_reply_and_watch_stale_markup():
    assert "function normalizeMessageCopyActions(root)" in APP_JS
    assert "new MutationObserver" in APP_JS
    assert "normalizeMessageCopyActions(root)" in APP_JS
    assert "row.querySelectorAll('[data-copy-note]')" in APP_JS
    assert "Copy raw code" not in APP_JS
    assert "Copy full markdown" not in APP_JS
    assert "Copy all" not in APP_JS
    assert "Copy code" not in APP_JS
    assert ">Copy note</button>" not in APP_JS
    assert ".copy-note-icon" in STYLE_CSS


def test_copy_observer_uses_stable_svg_dom_check_and_cannot_loop_on_serialized_markup():
    normalize = APP_JS.split("function normalizeMessageCopyActions(root)", 1)[1].split("function watchMessageCopyActions", 1)[0]
    assert "const iconOnly = note.childNodes.length === 1" in normalize
    assert "note.firstElementChild.matches('svg.copy-note-icon')" in normalize
    assert "if (!iconOnly) note.innerHTML = NOTE_COPY_ICON" in normalize
    assert "note.innerHTML !== NOTE_COPY_ICON" not in normalize


def test_research_keeps_chromium_hidden_but_explicit_browser_command_reveals_it():
    source = APP_JS.split("function openWorkbenchForTask(", 1)[1].split("async function generateImage(", 1)[0]
    assert "const explicitlyOpenBrowser = browserCommand && !explicitBrowserNegation" in source
    assert "if (explicitlyOpenBrowser) { state.workbenchTab = 'browser'; state.workbenchCollapsed = false; }" in source
    assert "else if (research || state.taskMode === 'deep_think' || code) { state.workbenchTab = 'activity'" in source


def test_review_workbench_tab_survives_saved_layout_reload():
    preferences = APP_JS.split("function loadWorkspacePreferences()", 1)[1].split("function saveWorkspacePreferences()", 1)[0]
    assert "const tabs = ['browser','preview','code','files','review','activity','images']" in preferences
    assert "if (tabs.includes(saved.workbenchTab)) state.workbenchTab = saved.workbenchTab" in preferences


def test_web_research_uses_direct_http_and_browser_tools_only_open_on_explicit_request():
    handler = APP_JS.split("if (data.tool && data.tool.startsWith('browser_'))", 1)[1].split("if (data.tool === 'project_write_file')", 1)[0]
    assert "if (state.researchTaskActive)" not in handler
    assert "state.workbenchTab='browser'" in handler
    assert "refreshBrowserPage({captureScreenshot:true})" in handler
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "direct web_search and web_open_source" in source
    assert "def _tool_schemas(mode: str, project: str | None, use_browser: bool, research_only: bool = False)" in source


def test_codex_style_worktree_review_ui_is_connected_to_real_api():
    assert "data-worktree-open" in APP_JS
    assert "createWorktreeForm" in APP_JS
    assert "loadGitWorktrees" in APP_JS
    assert "/worktrees" in APP_JS
    assert "Isolated task workspaces" in APP_JS
    assert "Uncommitted changes in the base project are not copied" in APP_JS


def test_static_assets_are_versioned_and_sent_without_cache():
    assert re.search(r"/assets/style\.css\?v=0\.9\.6", INDEX_HTML)
    assert re.search(r"/assets/app\.js\?v=0\.9\.6", INDEX_HTML)
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'from app.version import APP_VERSION' in source
    assert 'Cache-Control' in source and 'no-store' in source


def test_natural_language_research_is_inferred_for_backend_tool_routing():
    assert main._infer_research_task_mode("Please do deep research on current AI coding agents", "chat") == "deep_research"
    assert main._infer_research_task_mode("Search the web for current Codex features", "chat") == "web_search"
    assert main._infer_research_task_mode("Research this codebase and explain the architecture", "chat") == "chat"
    assert main._uses_tool_chat("Please do deep research on current AI coding agents", "chat", "chat")
    assert main._uses_tool_chat("Search online for official documentation", "chat", "chat")


def test_explicit_research_mode_is_preserved_over_natural_language_inference():
    assert main._infer_research_task_mode("Just answer briefly", "deep_research") == "deep_research"
    assert main._infer_research_task_mode("Look up online current pricing", "web_search") == "web_search"


def test_research_inference_is_used_by_the_streaming_backend():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    endpoint = source.split("def send_chat_message(", 1)[1].split("@app.get(", 1)[0]
    assert "effective_task_mode = _infer_research_task_mode(body.content, body.task_mode)" in endpoint
    assert "task_instructions = TASK_MODE_INSTRUCTIONS[effective_task_mode]" in endpoint
    assert 'get(effective_task_mode, 5)' in endpoint
    assert "_initial_research_context, effective_task_mode" in endpoint


def test_frontend_and_backend_recognize_natural_language_research_consistently():
    assert "search online" in APP_JS and "research the web" in APP_JS
    assert "deep research" in APP_JS and "comprehensive research" in APP_JS
    for phrase, expected in [
        ("Search online for the official product docs", "web_search"),
        ("Do an in-depth research report on agentic systems", "deep_research"),
    ]:
        assert main._infer_research_task_mode(phrase, "chat") == expected


def test_release_serves_versioned_fresh_assets_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "workspace", Workspace(tmp_path / "workspace"))
    with TestClient(main.app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "app.js?v=0.9.6" in home.text
        assert "style.css?v=0.9.6" in home.text
        assert "no-store" in home.headers.get("cache-control", "")
        js = client.get("/assets/app.js?v=0.9.6")
        css = client.get("/assets/style.css?v=0.9.6")
        assert js.status_code == css.status_code == 200
        assert "no-store" in js.headers.get("cache-control", "")
        assert "no-store" in css.headers.get("cache-control", "")
        status = client.get("/api/status", headers={"X-Spaceline-Token": main.app_token})
        assert status.status_code == 200 and status.json()["version"] == "0.9.6"


def test_ai_provider_accepts_extended_deep_research_tool_round_budget():
    from unittest.mock import patch
    from app.ai_provider import AIProviderClient

    client = AIProviderClient()
    settings = {"provider": "openai", "base_url": "https://api.openai.com/v1", "model": "test-model"}
    with patch.object(client, "_complete_openai_tools", return_value=("Research summary", [])) as execute:
        answer, _activity = client.complete_with_tools(settings, "test-key", [], [], lambda *_: {}, max_tool_rounds=14)
    assert answer == "Research summary"
    assert execute.call_args.args[-1] == 14


def test_chat_mode_prompt_runs_deep_research_seed_and_expanded_tool_loop(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / "workspace")
    profile = workspace.create_profile({
        "name": "Local research model", "provider": "ollama",
        "base_url": "http://127.0.0.1:11434", "model": "test-model",
    })
    workspace.set_active_profile(profile["id"])
    chat = workspace.create_conversation("Natural-language research", profile["id"], "test-model")
    monkeypatch.setattr(main, "workspace", workspace)
    monkeypatch.setattr(main, "app_token", "research-test-token")
    monkeypatch.setattr(main, "connection_pool_order", lambda _profile_id: [profile])

    calls = {"browser_enabled": [], "seed": [], "rounds": []}
    def fake_schemas(_mode, _project, use_browser, research_only=False):
        calls["browser_enabled"].append(use_browser)
        return [{"type": "function", "function": {"name": "web_search"}}]
    def fake_seed(task_mode, prompt, _handler):
        calls["seed"].append((task_mode, prompt))
        return {"role": "system", "content": "Seed evidence from direct HTTP web retrieval; untrusted data."}
    def fake_complete(_profile, _messages, _tools, _handler, max_tool_rounds=5):
        calls["rounds"].append(max_tool_rounds)
        return "Research report with cited sources.", []

    monkeypatch.setattr(main, "_tool_schemas", fake_schemas)
    monkeypatch.setattr(main, "_initial_research_context", fake_seed)
    monkeypatch.setattr(main, "_complete_with_profile_tools", fake_complete)
    with TestClient(main.app) as client:
        response = client.post(
            f"/api/chats/{chat['id']}/messages",
            headers={"X-Spaceline-Token": "research-test-token"},
            json={"content": "Please do deep research on current AI coding assistants", "profile_id": profile["id"],
                  "model": "test-model", "mode": "cowork", "context_limit": 4096, "task_mode": "chat"},
        )
    assert response.status_code == 200
    assert "Research report with cited sources." in response.text
    assert calls["browser_enabled"] == [True]
    assert calls["seed"] and calls["seed"][0][0] == "deep_research"
    assert calls["rounds"] == [14]
    saved = workspace.get_conversation(chat["id"])
    assert saved["messages"][-1]["content"] == "Research report with cited sources."
