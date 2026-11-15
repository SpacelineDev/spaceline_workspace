from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.key_vault import KeyVault
from app.workspace import Workspace


@pytest.fixture
def client(tmp_path, monkeypatch):
    original_workspace = main.workspace
    original_vault = main.key_vault
    original_token = main.app_token
    ws = Workspace(tmp_path)
    monkeypatch.setattr(main, "workspace", ws)
    monkeypatch.setattr(main, "key_vault", KeyVault(ws))
    monkeypatch.setattr(main, "app_token", "switch-test-token")
    yield TestClient(main.app), ws
    monkeypatch.setattr(main, "workspace", original_workspace)
    monkeypatch.setattr(main, "key_vault", original_vault)
    monkeypatch.setattr(main, "app_token", original_token)


def _create_local_profile(client, name, model):
    response = client.post("/api/providers", json={
        "name": name, "provider": "ollama", "base_url": "http://127.0.0.1:11434", "model": model,
    }, headers={"X-Spaceline-Token": "switch-test-token"})
    assert response.status_code == 200, response.text
    return response.json()


def test_missing_selected_connection_never_defaults_to_first_enabled_profile(client):
    api, _ = client
    _create_local_profile(api, "First", "first-model")
    with pytest.raises(main.ProviderError, match="Select a provider connection"):
        main.connection_pool_order(None)


def test_disabling_active_connection_clears_selection_instead_of_auto_switching(client):
    api, ws = client
    first = _create_local_profile(api, "First", "first-model")
    _create_local_profile(api, "Second", "second-model")
    assert ws.get_active_profile_id() == first["id"]

    response = api.post(f"/api/providers/{first['id']}/enabled", json={"enabled": False},
                        headers={"X-Spaceline-Token": "switch-test-token"})
    assert response.status_code == 200, response.text
    assert response.json()["active_profile_id"] is None
    assert ws.get_active_profile_id() is None



def test_provider_list_does_not_auto_select_an_enabled_model_when_selection_is_cleared(client):
    api, ws = client
    first = _create_local_profile(api, "First", "first-model")
    _create_local_profile(api, "Second", "second-model")
    ws.set_active_profile(None)

    response = api.get("/api/providers", headers={"X-Spaceline-Token": "switch-test-token"})

    assert response.status_code == 200
    assert response.json()["active_profile_id"] is None
    assert response.json()["pool_strategy"] == "explicit_selection_only"
    assert ws.get_active_profile_id() is None

def test_model_change_requires_explicit_confirmation(client):
    api, _ = client
    profile = _create_local_profile(api, "Local", "model-a")
    headers = {"X-Spaceline-Token": "switch-test-token"}
    payload = {**profile, "model": "model-b"}

    blocked = api.put(f"/api/providers/{profile['id']}", json=payload, headers=headers)
    assert blocked.status_code == 409
    assert "confirm" in blocked.json()["detail"].lower()

    approved = api.put(f"/api/providers/{profile['id']}",
                       json={**payload, "confirm_model_switch": True}, headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["model"] == "model-b"

    endpoint_change = api.put(f"/api/providers/{profile['id']}", json={
        **approved.json(), "base_url":"http://127.0.0.1:12345/v1",
    }, headers=headers)
    assert endpoint_change.status_code == 409
    endpoint_approved = api.put(f"/api/providers/{profile['id']}", json={
        **approved.json(), "base_url":"http://127.0.0.1:12345/v1", "confirm_model_switch":True,
    }, headers=headers)
    assert endpoint_approved.status_code == 200


def test_active_connection_change_requires_explicit_confirmation(client):
    api, ws = client
    first = _create_local_profile(api, "First", "first-model")
    second = _create_local_profile(api, "Second", "second-model")
    headers = {"X-Spaceline-Token": "switch-test-token"}

    blocked = api.post("/api/providers/active", json={"profile_id": second["id"]}, headers=headers)
    assert blocked.status_code == 409
    assert ws.get_active_profile_id() == first["id"]

    approved = api.post("/api/providers/active",
                        json={"profile_id": second["id"], "confirm_switch": True}, headers=headers)
    assert approved.status_code == 200
    assert ws.get_active_profile_id() == second["id"]


def test_chat_rejects_model_mismatch_before_sending_or_saving_user_message(client, monkeypatch):
    api, ws = client
    profile = _create_local_profile(api, "Selected", "selected-model")
    chat = api.post("/api/chats", json={"title": "Pin test", "profile_id": profile["id"]},
                    headers={"X-Spaceline-Token": "switch-test-token"}).json()
    called = []
    monkeypatch.setattr(main.ai_client, "stream_chat", lambda *args, **kwargs: called.append(args) or iter(["bad"]))
    response = api.post(f"/api/chats/{chat['id']}/messages", json={
        "content": "Hello", "profile_id": profile["id"], "model": "other-model",
    }, headers={"X-Spaceline-Token": "switch-test-token"})

    assert response.status_code == 409
    assert not called
    assert ws.get_conversation(chat["id"])["messages"] == []



def test_chat_request_invokes_only_the_exact_selected_profile_and_model(client, monkeypatch):
    api, ws = client
    selected = _create_local_profile(api, "Selected model", "exact-model-id")
    other = _create_local_profile(api, "Other model", "must-not-be-used")
    # Creating a second profile must not change the first active selection.
    assert ws.get_active_profile_id() == selected["id"]
    chat = api.post("/api/chats", json={"title": "Exact route", "profile_id": selected["id"]},
                    headers={"X-Spaceline-Token": "switch-test-token"}).json()
    invoked = []
    monkeypatch.setattr(main, "_uses_tool_chat", lambda *args, **kwargs: False)
    monkeypatch.setattr(main, "stream_profile_chat", lambda profile, messages: invoked.append(profile.copy()) or iter(["selected response"]))

    response = api.post(f"/api/chats/{chat['id']}/messages", json={
        "content": "Say hello", "profile_id": selected["id"], "model": "exact-model-id",
    }, headers={"X-Spaceline-Token": "switch-test-token"})

    assert response.status_code == 200
    assert invoked and invoked[0]["id"] == selected["id"]
    assert invoked[0]["model"] == "exact-model-id"
    assert invoked[0]["id"] != other["id"]


def test_chat_request_cannot_bypass_active_selection_by_sending_another_profile(client, monkeypatch):
    api, ws = client
    selected = _create_local_profile(api, "Approved", "approved-model")
    other = _create_local_profile(api, "Unapproved", "unapproved-model")
    chat = api.post("/api/chats", json={"title": "No route bypass", "profile_id": selected["id"]},
                    headers={"X-Spaceline-Token": "switch-test-token"}).json()
    called = []
    monkeypatch.setattr(main, "stream_profile_chat", lambda *args, **kwargs: called.append(args) or iter(["wrong"]))

    response = api.post(f"/api/chats/{chat['id']}/messages", json={
        "content": "Do not route me", "profile_id": other["id"], "model": other["model"],
    }, headers={"X-Spaceline-Token": "switch-test-token"})

    assert response.status_code == 409
    assert "approved active model selection" in response.json()["detail"]
    assert not called
    assert ws.get_conversation(chat["id"])["messages"] == []

def test_frontend_does_not_silently_reselect_on_load_or_open_chat():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "function confirmModelSwitch" in source
    assert "data-confirm-model-switch" in source
    assert "state.profiles.find(p => p.enabled !== false && p.model)" not in source
    open_chat = source[source.index("async function openChat"):source.index("// --- Search")]
    assert "setActiveProfile(" in open_chat
    assert "await confirmModelSwitch" in open_chat
    assert "await api('/api/providers/active'" not in open_chat


def test_frontend_prompts_before_selecting_a_different_provider_or_model():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "await confirmModelSwitch" in source[source.index("async function setActiveProfile"):source.index("function renderSidebar")]
    assert "confirm_model_switch: true" in source
    assert "confirm_switch: true" in source


def test_theme_uses_green_charcoal_and_grotesk_typography_without_pure_black():
    css = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8").lower()
    assert "#121614" in css
    assert "#181c1a" in css
    assert "space grotesk" in css
    assert "geist mono" in css
    assert "--line:rgba(255,255,255,.08)" in css or "rgba(255, 255, 255, 0.08)" in css
    assert "#000000" not in css
