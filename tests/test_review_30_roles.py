from pathlib import Path
from unittest.mock import patch

import pytest

from app.browser import ChromeBrowser
from app.key_vault import KeyVault
from app.workspace import Workspace
import app.main as main


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_profile_key_selection_does_not_expand_to_every_saved_provider_key(tmp_path, monkeypatch):
    ws = Workspace(tmp_path)
    vault = KeyVault(ws)

    class Store:
        def __init__(self):
            self.values = {}
        def set_password(self, key_id, secret):
            self.values[key_id] = secret
        def get_password(self, key_id):
            return self.values.get(key_id)
        def delete_password(self, key_id):
            self.values.pop(key_id, None)

    store = Store()
    monkeypatch.setattr('app.key_vault._create_store', lambda: store)
    first = vault.add_key('Groq', 'Selected', 'selected-secret')
    second = vault.add_key('Groq', 'Not selected', 'unselected-secret')

    assert vault.provider_key_ids('groq', [first['id']]) == [first['id']]
    assert vault.provider_key_ids('groq', []) == []
    assert set(vault.provider_key_ids('groq')) == {first['id'], second['id']}


def test_direct_browser_link_tool_rejects_risky_labels_even_without_command_parser():
    browser = ChromeBrowser(Path('/tmp/spaceline-link-safety-test'))
    with patch.object(browser, '_ensure'):
        with pytest.raises(ValueError, match='potentially destructive'):
            browser._click_link('Delete account')
        with pytest.raises(ValueError, match='potentially destructive'):
            browser._click_link('Logout')
    browser.close()


def test_browser_interactions_that_change_page_state_are_side_effects():
    for name in (
        'browser_click_link', 'browser_click_element', 'browser_fill_field',
        'browser_select_option', 'browser_set_checkbox',
    ):
        assert main._tool_execution_has_side_effect(name, {'ok': True}) is True


def test_live_tool_handler_exposes_side_effects_to_provider_retry_guard():
    source = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
    route = source[source.index('def send_chat_message'):source.index('@app.get("/api/ai/settings")')]
    assert 'live_tool_handler.side_effects = tool_side_effects' in route


def test_connection_consent_compares_provider_endpoint_and_key_pool_not_only_model_id():
    source = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    consent = source[source.index('function confirmModelSwitch'):source.index('function setupCustomCursor')]
    assert 'base_url' in consent
    assert 'provider' in consent
    assert 'key_ids' in consent


def test_opening_older_conversation_warns_when_saved_model_has_changed():
    source = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    open_chat = source[source.index('async function openChat'):source.index('// --- Search')]
    assert 'conversation.model' in open_chat
    assert 'savedProfile.model' in open_chat
    assert 'confirmModelSwitch' in open_chat


def test_browser_is_closed_on_fastapi_shutdown():
    assert callable(getattr(main, 'shutdown_spaceline_browser', None))
    class FakeBrowser:
        closed = False
        def close(self):
            self.closed = True
    fake = FakeBrowser()
    with patch.object(main, 'browser', fake):
        main.shutdown_spaceline_browser()
    assert fake.closed


def test_key_pool_copy_explains_explicit_key_selection_and_auth_only_fallback():
    source = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    assert 'only the keys you select' in source.lower()
    assert 'authentication failure' in source.lower()


def test_chat_body_accepts_a_bounded_user_context_window():
    body = main.ChatMessageBody(content="hello", context_limit=4096)
    assert body.context_limit == 4096
    with pytest.raises(Exception):
        main.ChatMessageBody(content="hello", context_limit=100)


def test_context_history_budget_uses_model_window_and_is_bounded():
    assert main.context_history_char_budget(4096) <= 10_000
    assert main.context_history_char_budget(100_000) == 60_000
    assert main.context_history_char_budget(None) == 60_000


def test_skill_prompt_context_has_a_total_budget_not_per_skill_200kb():
    from app.skills import format_skill_context
    skills = [{"name": f"Large skill {i}", "content": "x" * 200_000} for i in range(5)]
    rendered = format_skill_context(skills)
    assert len(rendered) <= 12_500
    assert "truncated" in rendered.lower() or "budget" in rendered.lower()


def test_frontend_sends_manual_context_limit_with_chat_request():
    source = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    request = source[source.index('body:JSON.stringify({content, profile_id:profileId'):source.index('});', source.index('body:JSON.stringify({content, profile_id:profileId'))]
    assert 'context_limit:contextLimitForProfile(chosenProfile)' in request


def test_successful_tool_side_effect_stops_retry_to_another_selected_key(monkeypatch):
    profile = {"id": "profile-a", "provider": "openai", "model": "model-a"}
    attempts = []
    monkeypatch.setattr(main, "profile_key_candidates", lambda _profile: [("key-a", "secret-a"), ("key-b", "secret-b")])

    def fake_complete(_profile, secret, _messages, _tools, handler):
        attempts.append(secret)
        handler.side_effects.add("project_write_file")
        raise main.ProviderError("auth expired after tool execution", 401)

    monkeypatch.setattr(main.ai_client, "complete_with_tools", fake_complete)
    handler = lambda *_args: {"ok": True}
    handler.side_effects = set()
    with pytest.raises(main.ProviderError):
        main._complete_with_profile_tools(profile, [], [], handler)
    assert attempts == ["secret-a"]


def test_browser_close_is_safe_to_call_more_than_once():
    browser = ChromeBrowser(Path('/tmp/spaceline-close-idempotent-test'))
    browser.close()
    browser.close()
