import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from app.workspace import Workspace
from app.key_vault import KeyVault
from unittest.mock import patch, Mock


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_workspace = main.workspace
        self.original_vault = main.key_vault
        self.original_token = main.app_token
        main.workspace = Workspace(Path(self.temp.name))
        main.key_vault = KeyVault(main.workspace)
        main.app_token = "test-token"
        self.original_web_configured = main.FIREBASE_WEB_CONFIGURED
        self.original_admin_ready = main.FIREBASE_ADMIN_READY
        self.original_firebase_auth = main.firebase_auth
        main.FIREBASE_WEB_CONFIGURED = True
        main.FIREBASE_ADMIN_READY = True
        main.firebase_auth = Mock()
        main.firebase_auth.verify_id_token.return_value = {"uid": "test-user"}
        self.client = TestClient(main.app)

    def tearDown(self):
        main.workspace = self.original_workspace
        main.key_vault = self.original_vault
        main.app_token = self.original_token
        main.FIREBASE_WEB_CONFIGURED = self.original_web_configured
        main.FIREBASE_ADMIN_READY = self.original_admin_ready
        main.firebase_auth = self.original_firebase_auth
        self.temp.cleanup()

    def test_image_generation_requires_local_session_and_saves_artifact(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"openai-key", "provider":"openai", "label":"OpenAI"}]):
            profile = self.client.post("/api/providers", json={
                "name":"OpenAI", "provider":"openai", "model":"gpt-6", "key_id":"openai-key",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        with patch.object(main, "profile_key_candidates", return_value=[("key-1", "fake-secret")]), \
             patch.object(main.ai_client, "generate_image", return_value=(b"fake-png", "image/png", "png")):
            unauthorized = self.client.post("/api/images/generate", json={
                "profile_id":profile.json()["id"], "prompt":"A green robot"
            })
            self.assertEqual(unauthorized.status_code, 401)
            response = self.client.post("/api/images/generate", json={
                "profile_id":profile.json()["id"], "prompt":"A green robot"
            }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["filename"].endswith(".png"))
        self.assertTrue(Path(main.workspace.root / "Generated Images" / response.json()["filename"]).exists())


    def test_image_history_persists_metadata_and_supports_delete(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"openai-key", "provider":"openai", "label":"OpenAI"}]):
            profile = self.client.post("/api/providers", json={
                "name":"OpenAI", "provider":"openai", "model":"gpt-6", "key_id":"openai-key",
            }, headers=headers)
        with patch.object(main, "profile_key_candidates", return_value=[("key-1", "fake-secret")]), \
             patch.object(main.ai_client, "generate_image", return_value=(b"fake-png", "image/png", "png")):
            generated = self.client.post("/api/images/generate", json={
                "profile_id":profile.json()["id"], "prompt":"A forest green robot poster",
                "model":"gpt-image-2.5-flare", "aspect_ratio":"16:9", "quality":"high",
            }, headers=headers)
        self.assertEqual(generated.status_code, 200)
        filename = generated.json()["filename"]
        history = self.client.get("/api/images", headers=headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["images"]), 1)
        self.assertEqual(history.json()["images"][0]["prompt"], "A forest green robot poster")
        self.assertEqual(history.json()["images"][0]["aspect_ratio"], "16:9")
        image = self.client.get(f"/api/images/{filename}", headers=headers)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.content, b"fake-png")
        deleted = self.client.delete(f"/api/images/{filename}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/images", headers=headers).json()["images"], [])

    def test_image_history_requires_local_session(self):
        self.assertEqual(self.client.get("/api/images").status_code, 401)

    def test_project_git_review_endpoint_returns_read_only_status_and_diff(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        project = self.client.post("/api/projects", json={"name": "review-demo"}, headers=headers).json()["name"]
        calls = []

        def fake_tool(name, arguments, selected_project):
            calls.append((name, arguments, selected_project))
            if name == "project_git_status":
                return {"ok": True, "summary": "Status loaded", "output": " M app.py"}
            if name == "project_git_diff":
                return {"ok": True, "summary": "Diff loaded", "output": "diff --git a/app.py b/app.py\n+print('review')", "redactions": 0}
            raise AssertionError(f"Unexpected tool: {name}")

        with patch.object(main, "_tool_handler", side_effect=fake_tool):
            response = self.client.get(f"/api/projects/{project}/git-review", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], " M app.py")
        self.assertIn("+print('review')", response.json()["diff"])
        self.assertEqual([item[0] for item in calls], ["project_git_status", "project_git_diff"])
        self.assertTrue(all(item[2] == project for item in calls))

    def test_project_git_review_endpoint_requires_local_session(self):
        response = self.client.get("/api/projects/review-demo/git-review")
        self.assertEqual(response.status_code, 401)

    def test_edenai_image_model_catalog_requires_local_session_and_selected_eden_connection(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"eden-key", "provider":"Eden AI", "label":"Eden"}]):
            profile = self.client.post("/api/providers", json={
                "name":"Eden AI Images", "provider":"edenai", "model":"", "key_id":"eden-key",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200, profile.text)
        profile_id = profile.json()["id"]
        self.assertEqual(self.client.get(f"/api/images/models/{profile_id}").status_code, 401)
        with patch.object(main, "profile_key_candidates", return_value=[("eden-key", "eden-secret")]), \
             patch.object(main.ai_client, "list_image_models", return_value=[{"id":"google/gemini-2.5-flash-image", "name":"Gemini Flash Image"}]) as list_models:
            response = self.client.get(f"/api/images/models/{profile_id}", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["provider"], "edenai")
        self.assertEqual(response.json()["models"][0]["id"], "google/gemini-2.5-flash-image")
        list_models.assert_called_once()

    def test_edenai_image_generation_uses_selected_eden_profile_and_marks_gallery_source(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"eden-key", "provider":"Eden AI", "label":"Eden"}]):
            profile = self.client.post("/api/providers", json={
                "name":"Eden AI Images", "provider":"edenai", "model":"", "key_id":"eden-key",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200, profile.text)
        with patch.object(main, "profile_key_candidates", return_value=[("eden-key", "eden-secret")]), \
             patch.object(main.ai_client, "generate_image", return_value=(b"eden-png", "image/png", "png")) as generate:
            response = self.client.post("/api/images/generate", json={
                "profile_id": profile.json()["id"], "prompt": "A polished green robot",
                "model": "google/gemini-3.1-flash-image", "aspect_ratio": "1:1", "quality": "high",
            }, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["provider"], "edenai")
        self.assertEqual(response.json()["model"], "google/gemini-3.1-flash-image")
        self.assertEqual(response.json()["quality"], "provider-default")
        generate.assert_called_once()
        history = self.client.get("/api/images", headers=headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["images"][0]["provider"], "edenai")

    def test_edenai_saved_api_key_test_uses_image_model_catalog_not_chat_models(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key = {"id":"eden-key", "provider":"Eden AI", "label":"Eden image key", "base_url":""}
        with patch.object(main.key_vault, "list_keys", return_value=[key]), \
             patch.object(main.key_vault, "get_secret", return_value="eden-secret"), \
             patch.object(main.ai_client, "list_image_models", return_value=[{"id":"google/gemini-2.5-flash-image", "name":"Gemini Flash"}]) as list_images, \
             patch.object(main.ai_client, "list_models") as list_chat:
            response = self.client.post("/api/keys/eden-key/test", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["provider"], "edenai")
        self.assertEqual(response.json()["sample_models"], ["google/gemini-2.5-flash-image"])
        self.assertIn("image model IDs", response.json()["message"])
        list_images.assert_called_once()
        list_chat.assert_not_called()

    def test_explicitly_selected_connection_stays_pinned_instead_of_rotating(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        first = self.client.post("/api/providers", json={"name":"Local A", "provider":"ollama", "model":"model-a"}, headers=headers)
        second = self.client.post("/api/providers", json={"name":"Local B", "provider":"ollama", "model":"model-b"}, headers=headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_id, second_id = first.json()["id"], second.json()["id"]
        self.assertTrue(first.json()["enabled"])
        main._connection_pool_rotation.clear()
        first_order = main.connection_pool_order(first_id)
        second_order = main.connection_pool_order(first_id)
        self.assertEqual([item["id"] for item in first_order], [first_id])
        self.assertEqual([item["id"] for item in second_order], [first_id])
        self.assertEqual(first_order[0]["model"], "model-a")
        disabled = self.client.post(f"/api/providers/{second_id}/enabled", json={"enabled":False}, headers=headers)
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()["profile"]["enabled"])
        self.assertEqual([item["id"] for item in main.connection_pool_order(first_id)], [first_id])

    def test_cannot_disable_last_enabled_provider_connection(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={"name":"Local", "provider":"ollama", "model":"model-a"}, headers=headers)
        response = self.client.post(f"/api/providers/{profile.json()['id']}/enabled", json={"enabled":False}, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("at least one", response.json()["detail"].lower())

    def test_model_catalog_endpoint_returns_openrouter_free_and_pricing_metadata(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"or-key", "provider":"OpenRouter", "label":"OR"}]), \
             patch.object(main.key_vault, "get_secret", return_value="secret"):
            profile = self.client.post("/api/providers", json={"name":"OpenRouter", "provider":"openrouter", "model":"vendor/free:free", "key_id":"or-key"}, headers=headers)
        catalog = [{"id":"vendor/free:free", "name":"Free", "pricing_status":"free-variant", "pricing_label":"Free variant · usage limited", "free_variant":True}]
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"or-key", "provider":"OpenRouter", "label":"OR"}]), \
             patch.object(main.key_vault, "get_secret", return_value="secret"), \
             patch.object(main.ai_client, "list_model_catalog", return_value=catalog):
            response = self.client.get(f"/api/providers/{profile.json()['id']}/models", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["models"], ["vendor/free:free"])
        self.assertTrue(response.json()["catalog"][0]["free_variant"])


    def test_model_access_probe_uses_saved_profile_key_and_returns_verified_status(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"g-key", "provider":"Gemini", "label":"Gemini"}]):
            profile = self.client.post("/api/providers", json={
                "name":"Gemini", "provider":"gemini", "model":"gemini-4-argon", "key_id":"g-key",
            }, headers=headers)
        with patch.object(main, "profile_key_candidates", return_value=[("g-key", "test-secret")]), \
             patch.object(main.ai_client, "probe_model", return_value={"ok":True, "status":"verified", "message":"Model accepted a minimal request."}) as probe:
            response = self.client.post(f"/api/providers/{profile.json()['id']}/models/check", json={"model":"gemini-4-argon"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["status"], "verified")
        self.assertEqual(probe.call_args.args[0]["model"], "gemini-4-argon")
        self.assertEqual(probe.call_args.args[1], "test-secret")

    def test_model_access_probe_reports_paid_tier_or_account_gate_cleanly(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"g-key", "provider":"Gemini", "label":"Gemini"}]):
            profile = self.client.post("/api/providers", json={
                "name":"Gemini", "provider":"gemini", "model":"gemini-4-argon", "key_id":"g-key",
            }, headers=headers)
        with patch.object(main, "profile_key_candidates", return_value=[("g-key", "test-secret")]), \
             patch.object(main.ai_client, "probe_model", side_effect=main.ProviderError("This key or account does not have access to this model.", 403)):
            response = self.client.post(f"/api/providers/{profile.json()['id']}/models/check", json={"model":"gemini-4-argon"}, headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn("does not have access", response.json()["detail"].lower())
        self.assertNotIn("test-secret", response.text)

    def test_context_meter_uses_conversation_text_estimate_and_profile(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name":"Local Qwen", "provider":"ollama", "model":"qwen3:8b",
        }, headers=headers)
        chat = self.client.post("/api/chats", json={"title":"Usage test", "profile_id":profile.json()["id"]}, headers=headers)
        with patch.object(main.ai_client, "get_context_window", return_value=(32768, "provider")):
            response = self.client.get(f"/api/chats/{chat.json()['id']}/usage", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen3:8b")
        self.assertEqual(response.json()["context_window"], 32768)
        self.assertEqual(response.json()["context_source"], "provider")
        self.assertIsInstance(response.json()["estimated_used_tokens"], int)

    def test_mutations_require_local_session_token(self):
        response = self.client.post("/api/projects", json={"name":"Demo"})
        self.assertEqual(response.status_code, 401)

    def test_api_reads_require_local_session_token(self):
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 401)

    def test_project_file_round_trip_through_api(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        created = self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        self.assertEqual(created.status_code, 200)
        saved = self.client.put("/api/file", json={"project":"Demo","path":"main.py","content":"print(123)"}, headers=headers)
        self.assertEqual(saved.status_code, 200)
        loaded = self.client.get("/api/file", params={"project":"Demo","path":"main.py"}, headers=headers)
        self.assertEqual(loaded.json()["content"], "print(123)")

    def test_file_api_rejects_path_traversal(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        response = self.client.put("/api/file", json={"project":"Demo","path":"../outside.txt","content":"bad"}, headers=headers)
        self.assertEqual(response.status_code, 400)


    def test_ai_settings_are_persisted_without_exposing_secret_values(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        response = self.client.put("/api/ai/settings", json={
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen2.5:7b",
            "key_id": None,
        }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen2.5:7b")
        self.assertNotIn("secret", response.json())
        loaded = self.client.get("/api/ai/settings", headers=headers)
        self.assertEqual(loaded.json()["provider"], "ollama")

    def test_ai_settings_reads_require_session_token(self):
        response = self.client.get("/api/ai/settings")
        self.assertEqual(response.status_code, 401)

    def test_ai_settings_reject_invalid_endpoint_scheme(self):
        response = self.client.put("/api/ai/settings", json={
            "provider": "openai-compatible", "base_url": "file:///etc/passwd", "model": "model-a",
        }, headers={"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 400)

    def test_saved_api_key_can_be_tested_individually_without_exposing_secret(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key = {"id": "key-openai", "provider": "OpenAI", "label": "Primary", "base_url": ""}
        with patch.object(main.key_vault, "list_keys", return_value=[key]), \
             patch.object(main.key_vault, "get_secret", return_value="sk-secret-value"), \
             patch.object(main.ai_client, "list_models", return_value=["gpt-test", "gpt-mini"] ) as list_models:
            unauthorized = self.client.post("/api/keys/key-openai/test")
            self.assertEqual(unauthorized.status_code, 401)
            response = self.client.post("/api/keys/key-openai/test", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["model_count"], 2)
        self.assertEqual(response.json()["provider"], "openai")
        self.assertNotIn("secret", response.text)
        list_models.assert_called_once()
        self.assertEqual(list_models.call_args.args[0]["base_url"], "https://api.openai.com/v1")
        self.assertEqual(list_models.call_args.args[1], "sk-secret-value")

    def test_saved_api_key_test_reports_invalid_auth_without_leaking_key(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key = {"id": "key-groq", "provider": "Groq", "label": "Bad key", "base_url": ""}
        with patch.object(main.key_vault, "list_keys", return_value=[key]), \
             patch.object(main.key_vault, "get_secret", return_value="gsk-secret-value"), \
             patch.object(main.ai_client, "list_models", side_effect=main.ProviderError("Authentication failed.", 401)):
            response = self.client.post("/api/keys/key-groq/test", headers=headers)
        self.assertEqual(response.status_code, 502)
        self.assertIn("Authentication failed", response.json()["detail"])
        self.assertNotIn("gsk-secret-value", response.text)

    def test_saved_api_key_test_rejects_unknown_key(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[]):
            response = self.client.post("/api/keys/missing/test", headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_ai_connection_test_returns_models(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.put("/api/ai/settings", json={
            "provider": "ollama", "model": "qwen2.5:7b", "key_id": None,
        }, headers=headers)
        with patch.object(main.ai_client, "list_models", return_value=["qwen2.5:7b", "llama3.2:3b"]):
            response = self.client.post("/api/ai/test", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["models"], ["qwen2.5:7b", "llama3.2:3b"])

    def test_ai_chat_streams_content_as_server_sent_events(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.put("/api/ai/settings", json={
            "provider": "ollama", "model": "qwen2.5:7b", "key_id": None,
        }, headers=headers)
        with patch.object(main.ai_client, "stream_chat", return_value=iter(["Hello", " there"])):
            response = self.client.post("/api/ai/chat", json={
                "messages": [{"role": "user", "content": "Say hello"}],
            }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('"delta": "Hello"', response.text)
        self.assertIn('"delta": " there"', response.text)
        self.assertIn('"done": true', response.text)

    def test_ai_chat_requires_a_saved_model(self):
        response = self.client.post("/api/ai/chat", json={
            "messages": [{"role": "user", "content": "Hello"}],
        }, headers={"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 400)

    def test_notes_can_be_saved_and_exported(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        saved = self.client.post("/api/notes", json={"title":"Test note","content":"Keep this data"}, headers=headers)
        self.assertEqual(saved.status_code, 200)
        exported = self.client.get("/api/notes/export", headers=headers)
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()["notes"][0]["title"], "Test note")


    def test_provider_presets_api_exposes_vendor_selector_options(self):
        response = self.client.get("/api/provider-presets", headers={"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 200)
        providers = {item["id"]: item for item in response.json()["providers"]}
        for provider in ("openai", "nvidia", "groq", "kimi", "openrouter", "deepseek", "anthropic", "gemini", "freellm"):
            self.assertIn(provider, providers)
        self.assertEqual(providers["nvidia"]["default_base_url"], "https://integrate.api.nvidia.com/v1")
        self.assertEqual(providers["groq"]["default_base_url"], "https://api.groq.com/openai/v1")
        self.assertEqual(providers["kimi"]["default_base_url"], "https://api.moonshot.ai/v1")

    def test_vendor_profile_id_is_saved_and_kept(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"key-test", "label":"Groq main", "provider":"Groq"}]), \
             patch.object(main.key_vault, "get_secret", return_value="fake-secret"):
            response = self.client.post("/api/providers", json={
                "name":"Groq primary", "provider":"groq", "model":"llama-test", "key_id":"key-test",
            }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "groq")
        self.assertEqual(response.json()["base_url"], "https://api.groq.com/openai/v1")
        self.assertNotIn("secret", response.json())

    def test_provider_profiles_and_persistent_chat_stream(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name":"Local Qwen", "provider":"ollama", "base_url":"http://127.0.0.1:11434",
            "model":"qwen2.5:7b", "key_id":None,
        }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertNotIn("secret", profile.json())
        listed = self.client.get("/api/providers", headers=headers)
        self.assertEqual(listed.json()["profiles"][0]["name"], "Local Qwen")
        chat = self.client.post("/api/chats", json={"title":"New chat"}, headers=headers)
        self.assertEqual(chat.status_code, 200)
        with patch.object(main.ai_client, "stream_chat", return_value=iter(["Built ", "it."])):
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={"content":"Make a small app"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn('"delta": "Built "', response.text)
        self.assertIn('"done": true', response.text)
        loaded = self.client.get(f"/api/chats/{chat.json()['id']}", headers=headers)
        self.assertEqual([m["role"] for m in loaded.json()["messages"]], ["user", "assistant"])
        self.assertEqual(loaded.json()["messages"][1]["content"], "Built it.")



    def test_provider_models_route_discovers_models_for_quick_picker(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.key_vault, "list_keys", return_value=[{"id":"key-primary","provider":"groq","label":"Primary"}]):
            profile = self.client.post("/api/providers", json={
                "name":"Groq quick", "provider":"groq", "model":"llama-test", "key_id":"key-primary",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        catalog = [{"id":"llama-3.3","name":"llama-3.3","pricing_status":"unknown","pricing_label":"Pricing not exposed by provider","free_variant":False},
                   {"id":"qwen-qwq","name":"qwen-qwq","pricing_status":"unknown","pricing_label":"Pricing not exposed by provider","free_variant":False}]
        with patch.object(main, "discover_profile_model_catalog", return_value=(catalog, "key-primary")):
            response = self.client.get(f"/api/providers/{profile.json()['id']}/models", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["models"], ["llama-3.3", "qwen-qwq"])

    def test_keys_are_retried_after_401_and_working_key_becomes_primary(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key_rows = [{"id":"key-bad","provider":"groq","label":"Bad"}, {"id":"key-good","provider":"groq","label":"Good"}]
        with patch.object(main.key_vault, "list_keys", return_value=key_rows):
            profile = self.client.post("/api/providers", json={
                "name":"Groq pool", "provider":"groq", "model":"llama-test",
                "key_ids":["key-bad", "key-good"],
            }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        def fake_get_secret(key_id):
            return {"key-bad":"invalid-secret", "key-good":"valid-secret"}[key_id]
        def fake_stream(settings, secret, messages):
            if secret == "invalid-secret":
                raise main.ProviderError("authentication failed", 401)
            yield "Authenticated response"
        with patch.object(main.key_vault, "list_keys", return_value=key_rows), \
             patch.object(main.key_vault, "get_secret", side_effect=fake_get_secret), \
             patch.object(main.ai_client, "stream_chat", side_effect=fake_stream):
            chat = self.client.post("/api/chats", json={"title":"Test"}, headers=headers)
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                "content":"Say hello", "profile_id":profile.json()["id"]
            }, headers=headers)
        self.assertIn("Authenticated response", response.text)
        updated = self.client.get("/api/providers", headers=headers).json()["profiles"][0]
        self.assertEqual(updated["key_id"], "key-good")

    def test_skills_api_imports_a_claude_skill_for_auto_activation(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        content = "---\nname: sql-helper\ndescription: Help with SQL query optimization.\ntriggers: sql, query plan\n---\nInspect indexes before optimizing."
        saved = self.client.post("/api/skills/import", json={"name":"SQL Helper", "content":content}, headers=headers)
        self.assertEqual(saved.status_code, 200)
        listed = self.client.get("/api/skills", headers=headers)
        self.assertTrue(any(item["id"] == "sql-helper" for item in listed.json()["skills"]))

    def test_browser_open_rejects_non_http_url(self):
        response = self.client.post("/api/browser/open", json={"url":"javascript:alert(1)"}, headers={"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 400)

    def test_browser_search_uses_persistent_browser_and_requires_local_token(self):
        unauthorized = self.client.post("/api/browser/search", json={"query":"motion ui libraries"})
        self.assertEqual(unauthorized.status_code, 401)
        with patch.object(main.browser, "search_web", return_value={"title":"Search", "url":"https://www.google.com/search?q=motion", "text":"Motion docs"}) as search:
            response = self.client.post("/api/browser/search", json={"query":"motion ui libraries"}, headers={"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Motion docs", response.json()["text"])
        search.assert_called_once_with("motion ui libraries")

    def test_browser_screenshot_is_served_only_to_authorized_local_session(self):
        unauthorized = self.client.get("/api/browser/screenshot")
        self.assertEqual(unauthorized.status_code, 401)
        with patch.object(main.browser, "screenshot", return_value=b"fake-png"):
            response = self.client.get("/api/browser/screenshot", headers={"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.content, b"fake-png")


    def test_browser_intent_automatically_enables_chrome_tools_and_browser_skill(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name":"Local tool model", "provider":"ollama", "model":"qwen3:8b",
        }, headers=headers)
        chat = self.client.post("/api/chats", json={"title":"Browse"}, headers=headers)
        captured = {}
        def fake_complete(_profile, messages, tools, _handler):
            captured["messages"] = messages
            captured["tools"] = tools
            return "Opened the page.", [{"tool":"browser_open","ok":True,"summary":"Opened Example"}]
        with patch.object(main, "_complete_with_profile_tools", side_effect=fake_complete):
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                "content":"Please open https://example.com in Chrome and inspect it", "profile_id":profile.json()["id"]
            }, headers=headers)
        self.assertIn("Opened the page.", response.text)
        names = {item["function"]["name"] for item in captured["tools"]}
        self.assertIn("browser_open", names)
        self.assertIn("browser_read_page", names)
        self.assertTrue(any("browser-research" in message["content"] for message in captured["messages"] if message["role"] == "system"))

    def test_code_mode_enables_project_file_and_safe_check_tools(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        profile = self.client.post("/api/providers", json={
            "name":"Local tool model", "provider":"ollama", "model":"qwen3:8b",
        }, headers=headers)
        chat = self.client.post("/api/chats", json={"title":"Code"}, headers=headers)
        captured = {}
        def fake_complete(_profile, _messages, tools, _handler):
            captured["tools"] = tools
            return "Implemented.", []
        with patch.object(main, "_complete_with_profile_tools", side_effect=fake_complete):
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                "content":"Implement a small feature in this project", "profile_id":profile.json()["id"],
                "project":"Demo", "mode":"code"
            }, headers=headers)
        self.assertIn("Implemented.", response.text)
        names = {item["function"]["name"] for item in captured["tools"]}
        self.assertTrue({"project_list_files", "project_read_file", "project_write_file", "project_run_check"}.issubset(names))

    def test_project_agent_write_tool_rejects_path_traversal_and_secrets(self):
        main.workspace.create_project("SafeProject")
        with self.assertRaises(ValueError):
            main._tool_handler("project_write_file", {"path":"../outside.txt", "content":"bad"}, "SafeProject")
        for secret_path in (".env", ".env.production", "config/.env.local", "secrets.json", "id_rsa", ".ssh/id_ed25519", "tls/server.pem", ".npmrc", ".git/config"):
            with self.subTest(path=secret_path), self.assertRaises(ValueError):
                main._tool_handler("project_write_file", {"path":secret_path, "content":"API_KEY=bad"}, "SafeProject")

    def test_tool_key_rotation_stops_after_a_project_mutation(self):
        from app.ai_provider import ProviderError
        profile = {"id": "profile-test", "provider": "openai", "model": "gpt-test"}
        side_effects = set()
        calls = []
        def handler(name, args):
            side_effects.add(name)
            return {"ok": True, "summary": "Saved"}
        def invoke(_profile, _secret, _messages, _tools, tool_handler):
            calls.append("called")
            tool_handler("project_write_file", {"path":"main.py", "content":"print('done')"})
            raise ProviderError("Provider rejected the next turn", 401)
        handler.side_effects = side_effects
        with patch.object(main, "profile_key_candidates", return_value=[("key-one", "secret-one"), ("key-two", "secret-two")]), \
             patch.object(main.ai_client, "complete_with_tools", side_effect=invoke):
            with self.assertRaises(ProviderError):
                main._complete_with_profile_tools(profile, [], [], handler)
        self.assertEqual(len(calls), 1, "Do not replay a task on another key after a successful write")
        self.assertEqual(side_effects, {"project_write_file"})

    def test_project_agent_read_tool_rejects_common_secret_file_patterns(self):
        main.workspace.create_project("ReadSecrets")
        for secret_path in (".env.production", "credentials.json", "private.key", ".ssh/id_rsa", ".aws/credentials", ".git/config"):
            target = main.workspace.safe_path("ReadSecrets", secret_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("secret-value", encoding="utf-8")
            with self.subTest(path=secret_path), self.assertRaises(ValueError):
                main._tool_handler("project_read_file", {"path":secret_path}, "ReadSecrets")

    def test_project_context_attaches_source_but_filters_common_secrets(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        main.workspace.write_file("Demo", "main.py", "API_KEY = 'sk-123456789012345678901234'\nprint('hello')")
        main.workspace.write_file("Demo", ".env", "OPENAI_API_KEY=should-not-appear")
        main.workspace.write_file("Demo", "node_modules/pkg/index.js", "should-not-appear")
        profile = self.client.post("/api/providers", json={
            "name":"Local model", "provider":"ollama", "base_url":"http://127.0.0.1:11434",
            "model":"qwen-local", "key_id":None,
        }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        chat = self.client.post("/api/chats", json={"title":"New chat"}, headers=headers)
        captured = {}
        def fake_stream(_profile, _secret, messages):
            captured["messages"] = messages
            return iter(["Reviewed."])
        with patch.object(main.ai_client, "stream_chat", side_effect=fake_stream):
            response = self.client.post(
                f"/api/chats/{chat.json()['id']}/messages",
                json={"content":"Review my project", "project":"Demo"}, headers=headers,
            )
        self.assertEqual(response.status_code, 200)
        prompt = captured["messages"][0]["content"]
        self.assertIn("main.py", prompt)
        self.assertIn("print('hello')", prompt)
        self.assertIn("[REDACTED]", prompt)
        self.assertNotIn("should-not-appear", prompt)
        self.assertNotIn("node_modules", prompt)


    def test_open_project_in_vscode_uses_selected_project_path(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        with patch("app.main.subprocess.Popen") as popen:
            response = self.client.post("/api/open-vscode", json={"project":"Demo"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        args, kwargs = popen.call_args
        self.assertEqual(args[0][0], "code")
        self.assertTrue(args[0][1].endswith("Demo"))
        self.assertEqual(kwargs["cwd"], args[0][1])


    def test_open_folder_launches_the_selected_project_directory(self):
        headers = {"X-Spaceline-Token":"test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name":"Demo"}, headers=headers)
        with patch("app.main.subprocess.Popen") as popen:
            response = self.client.post("/api/open-folder", json={"project":"Demo"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        popen.assert_called_once()

    def test_open_folder_requires_session_token(self):
        response = self.client.post("/api/open-folder", json={"project":"Demo"})
        self.assertEqual(response.status_code, 401)
    def test_gateway_connection_persists_custom_auth_mode_without_a_key_when_none(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        response = self.client.post("/api/providers", json={
            "name": "Unauthenticated local gateway", "provider": "freellm",
            "base_url": "http://127.0.0.1:31415/v1", "model": "model-a",
            "auth_mode": "none", "key_ids": [],
        }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["auth_mode"], "none")
        self.assertFalse(response.json()["has_key"])

    def test_free_llm_auth_failure_explains_gateway_key_and_header_mode(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key_rows = [{"id":"free-key", "provider":"FreeLLM API", "label":"Gateway key"}]
        with patch.object(main.key_vault, "list_keys", return_value=key_rows):
            profile = self.client.post("/api/providers", json={
                "name":"FreeLLM local", "provider":"freellm", "model":"model-a",
                "key_ids":["free-key"], "auth_mode":"bearer",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        with patch.object(main.key_vault, "list_keys", return_value=key_rows), \
             patch.object(main.key_vault, "get_secret", return_value="hidden-secret"), \
             patch.object(main.ai_client, "list_models", side_effect=main.ProviderError("upstream auth rejected", 401)):
            response = self.client.get(f"/api/providers/{profile.json()['id']}/models", headers=headers)
        self.assertEqual(response.status_code, 502)
        self.assertIn("FreeLLM gateway's own access key", response.json()["detail"])
        self.assertIn("Bearer, X-API-Key, API-Key, or No authentication", response.json()["detail"])
        self.assertNotIn("hidden-secret", response.json()["detail"])

    def test_model_picker_controls_exist_and_refresh_live_models_in_chat(self):
        source = (main.STATIC_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="openModelPicker"', source)
        self.assertIn('id="refreshModelList"', source)
        self.assertIn('id="modelSearch"', source)
        self.assertIn("models.length", source)

    def test_unselected_provider_key_is_not_used_as_an_implicit_backup(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key_rows = [
            {"id":"key-primary", "provider":"FreeLLM API", "label":"Primary"},
            {"id":"key-backup", "provider":"FreeLLM", "label":"Not assigned to this connection"},
        ]
        with patch.object(main.key_vault, "list_keys", return_value=key_rows):
            profile = self.client.post("/api/providers", json={
                "name":"FreeLLM primary", "provider":"freellm", "model":"model-a", "key_id":"key-primary",
            }, headers=headers)
        self.assertEqual(profile.status_code, 200)
        attempted = []
        def fake_secret(key_id):
            return {"key-primary":"bad-secret", "key-backup":"unselected-secret"}[key_id]
        def fake_stream(settings, secret, messages):
            attempted.append(secret)
            raise main.ProviderError("auth failed", 401)
            yield "unreachable"
        with patch.object(main.key_vault, "list_keys", return_value=key_rows), \
             patch.object(main.key_vault, "get_secret", side_effect=fake_secret), \
             patch.object(main.ai_client, "stream_chat", side_effect=fake_stream):
            chat = self.client.post("/api/chats", json={"title":"Key scope"}, headers=headers)
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                "content":"Hello", "profile_id":profile.json()["id"]
            }, headers=headers)
        self.assertEqual(attempted, ["bad-secret"])
        self.assertNotIn("unselected-secret", response.text)
        self.assertIn("tried 1 saved key", response.text)
        self.assertEqual(main.workspace.get_profile_key_ids(profile.json()["id"]), ["key-primary"])


    def test_web_research_modes_use_direct_http_tools_without_chromium(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Local research model", "provider": "ollama", "model": "qwen3:8b",
        }, headers=headers)
        captured = []

        def fake_complete(_profile, messages, tools, _handler, max_tool_rounds=5):
            captured.append((messages, tools, max_tool_rounds))
            return "Research workflow complete.", []

        def fake_search(query):
            return {"ok": True, "query": query, "results": [{"title": "Official source", "url": "https://example.com/docs"}],
                    "text": "Independent search evidence", "search_engine": "test"}

        with patch.object(main.web_research, "search", side_effect=fake_search) as search, \
             patch.object(main.browser, "search_web", side_effect=AssertionError("Research must not start Chromium")), \
             patch.object(main.browser, "snapshot", side_effect=AssertionError("Research must not snapshot Chromium")), \
             patch.object(main, "_complete_with_profile_tools", side_effect=fake_complete):
            for task_mode in ("web_search", "deep_research"):
                chat = self.client.post("/api/chats", json={"title": task_mode}, headers=headers)
                response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                    "content": "Explain the current landscape of UI animation libraries.",
                    "profile_id": profile.json()["id"], "task_mode": task_mode,
                }, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertIn("Research workflow complete.", response.text)

        self.assertEqual(len(captured), 2)
        self.assertEqual([rounds for _messages, _tools, rounds in captured], [8, 14])
        self.assertGreaterEqual(search.call_count, 5)
        for messages, tools, _rounds in captured:
            names = {item["function"]["name"] for item in tools}
            self.assertTrue({"web_search", "web_open_source"}.issubset(names))
            self.assertFalse({"browser_search_web", "browser_open", "browser_read_page"} & names)
            system = "\n".join(item["content"] for item in messages if item["role"] == "system").lower()
            self.assertIn("direct", system)
            self.assertIn("research", system)

    def test_deep_think_is_structured_problem_solving_without_forced_web_browsing(self):
        self.assertFalse(main._uses_tool_chat(
            "Explain the trade-offs in this algorithm.", "cowork", "deep_think", None
        ))
        instruction = main.TASK_MODE_INSTRUCTIONS["deep_think"].lower()
        self.assertIn("break the task into manageable parts", instruction)
        self.assertIn("do not browse by default", instruction)
        self.assertIn("exact model and provider selected", instruction)

    def test_chat_mode_does_not_force_browser_tools(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Local chat model", "provider": "ollama", "model": "qwen3:8b",
        }, headers=headers)
        chat = self.client.post("/api/chats", json={"title": "Chat"}, headers=headers)
        with patch.object(main.ai_client, "stream_chat", return_value=iter(["Hello."])):
            response = self.client.post(f"/api/chats/{chat.json()['id']}/messages", json={
                "content": "Say hello.", "profile_id": profile.json()["id"], "task_mode": "chat",
            }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Hello.", response.text)

    def test_model_access_check_uses_saved_key_and_does_not_expose_it(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        key_rows = [{"id": "gemini-key", "provider": "Google Gemini", "label": "Gemini test key"}]
        with patch.object(main.key_vault, "list_keys", return_value=key_rows), \
             patch.object(main.key_vault, "get_secret", return_value="super-secret"), \
             patch.object(main.ai_client, "probe_model", return_value={"ok": True, "status": "verified", "model": "gemini-test", "message": "Access verified"}) as probe:
            profile = self.client.post("/api/providers", json={
                "name": "Gemini", "provider": "gemini", "model": "gemini-test", "key_id": "gemini-key",
            }, headers=headers)
            self.assertEqual(profile.status_code, 200, profile.text)
            response = self.client.post(f"/api/providers/{profile.json()['id']}/models/check",
                                        json={"model": "gemini-test"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("super-secret", response.text)
        self.assertNotIn("key_id", response.json())
        self.assertNotIn("working_key_id", response.json())
        self.assertEqual(probe.call_args.args[1], "super-secret")

    def test_model_access_check_requires_local_session_token(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Local", "provider": "ollama", "model": "qwen3:8b",
        }, headers=headers)
        response = self.client.post(f"/api/providers/{profile.json()['id']}/models/check",
                                    json={"model": "qwen3:8b"})
        self.assertEqual(response.status_code, 401)

    def test_chat_can_be_deleted_and_messages_are_cascaded(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        chat = self.client.post("/api/chats", json={"title": "Delete me"}, headers=headers)
        chat_id = chat.json()["id"]
        self.client.post(f"/api/chats/{chat_id}/messages", json={"content": "Test message"}, headers=headers)
        deleted = self.client.delete(f"/api/chats/{chat_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])
        self.assertNotIn(chat_id, [item["id"] for item in self.client.get("/api/chats", headers=headers).json()["chats"]])
        with main.workspace._connect() as db:
            remaining_messages = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (chat_id,)).fetchone()[0]
        self.assertEqual(remaining_messages, 0, "Deleting a conversation must cascade to its messages")
        self.assertEqual(self.client.get(f"/api/chats/{chat_id}", headers=headers).status_code, 404)

    def test_chat_delete_requires_local_session_token(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        chat = self.client.post("/api/chats", json={"title": "Protected delete"}, headers=headers)
        response = self.client.delete(f"/api/chats/{chat.json()['id']}")
        self.assertEqual(response.status_code, 401)

    def test_run_endpoint_rejects_shell_chaining(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name": "Run Test"}, headers=headers)
        response = self.client.post("/api/run", json={
            "project": "Run Test", "command": "python -c \"print(1)\" && whoami",
        }, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_run_endpoint_invokes_allowlisted_command_without_shell(self):
        from types import SimpleNamespace
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name": "Run Test"}, headers=headers)
        with patch("app.main.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="ok", stderr="")) as run:
            response = self.client.post("/api/run", json={
                "project": "Run Test", "command": "python -m pytest",
            }, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertIsInstance(run.call_args.args[0], list)


    def test_failed_project_check_still_blocks_task_replay(self):
        self.assertTrue(main._tool_execution_has_side_effect("project_run_check", {"ok": False, "returncode": 1}))
        self.assertTrue(main._tool_execution_has_side_effect("project_write_file", {"ok": True}))
        self.assertFalse(main._tool_execution_has_side_effect("project_write_file", {"ok": False}))
        self.assertFalse(main._tool_execution_has_side_effect("project_read_file", {"ok": True}))


    def test_document_upload_extracts_docx_text_without_saving_upload(self):
        import io
        import zipfile
        output = io.BytesIO()
        xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Uploaded contract summary</w:t></w:r></w:p></w:body></w:document>'''
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('word/document.xml', xml)
        response = self.client.post('/api/files/analyze-upload', files={
            'file': ('contract.docx', output.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        }, headers={'X-Spaceline-Token':'test-token', 'Authorization':'Bearer test-id-token'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('Uploaded contract summary', response.json()['content'])
        self.assertEqual(response.json()['format'], 'DOCX')

    def test_document_upload_blocks_secret_like_names(self):
        response = self.client.post('/api/files/analyze-upload', files={
            'file': ('.env.production', b'SECRET=abc', 'text/plain')
        }, headers={'X-Spaceline-Token':'test-token', 'Authorization':'Bearer test-id-token'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('credential', response.json()['detail'].lower())

    def test_project_document_endpoint_uses_safe_path_and_extracts_text(self):
        import zipfile
        headers = {'X-Spaceline-Token':'test-token', 'Authorization':'Bearer test-id-token'}
        main.workspace.create_project('Docs')
        path = main.workspace.project_path('Docs') / 'brief.docx'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Scope and timeline</w:t></w:r></w:p></w:body></w:document>')
        result = self.client.get('/api/file/analyze', params={'project':'Docs','path':'brief.docx'}, headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn('Scope and timeline', result.json()['content'])
        traversal = self.client.get('/api/file/analyze', params={'project':'Docs','path':'../secret.docx'}, headers=headers)
        self.assertNotEqual(traversal.status_code, 200)

    def test_project_file_search_returns_document_matches_and_skips_protected_files(self):
        import zipfile
        headers = {'X-Spaceline-Token':'test-token', 'Authorization':'Bearer test-id-token'}
        main.workspace.create_project('Search Lab')
        main.workspace.write_file('Search Lab', 'notes.md', 'Important milestone is November 20.')
        main.workspace.write_file('Search Lab', '.env.production', 'Important milestone SECRET=abc')
        found = self.client.get('/api/files/search', params={'project':'Search Lab','q':'milestone'}, headers=headers)
        self.assertEqual(found.status_code, 200, found.text)
        self.assertTrue(any(item['path']=='notes.md' for item in found.json()['matches']))
        self.assertFalse(any('.env' in item['path'] for item in found.json()['matches']))

    def test_project_file_search_redacts_secrets_from_returned_excerpts(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        main.workspace.create_project("Search Redaction")
        secret = "sk-proj-abcdefghijklmnop123456"
        main.workspace.write_file("Search Redaction", "settings.txt", f"API_KEY={secret}\nservice uses API_KEY in production")
        response = self.client.get("/api/files/search", params={"project": "Search Redaction", "q": "API_KEY"}, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["matches"])
        self.assertEqual(len(response.json()["matches"]), 1, "Search should show one best excerpt per matching file")
        self.assertNotIn(secret, response.text)
        self.assertIn("[REDACTED]", response.text)


    def test_preview_endpoint_blocks_protected_secret_paths(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name": "Demo"}, headers=headers)
        main.workspace.write_file("Demo", ".env", "API_KEY=secret-value")
        response = self.client.get("/preview/Demo/.env")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("secret-value", response.text)

    def test_extensionless_project_files_are_visible_readable_and_searchable(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        main.workspace.create_project("Extensionless Files")
        main.workspace.write_file("Extensionless Files", "Dockerfile", "FROM python:3.13\nRUN pip install fastapi")
        main.workspace.write_file("Extensionless Files", ".gitignore", ".venv/\n__pycache__/")
        listed = self.client.get("/api/files", params={"project": "Extensionless Files"}, headers=headers)
        paths = [item["path"] for item in listed.json()["files"]]
        self.assertIn("Dockerfile", paths)
        self.assertIn(".gitignore", paths)
        loaded = self.client.get("/api/file", params={"project": "Extensionless Files", "path": "Dockerfile"}, headers=headers)
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertIn("FROM python", loaded.json()["content"])
        found = self.client.get("/api/files/search", params={"project": "Extensionless Files", "q": "fastapi"}, headers=headers)
        self.assertTrue(any(item["path"] == "Dockerfile" for item in found.json()["matches"]))

    def test_text_read_endpoint_rejects_binary_and_protected_files(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        main.workspace.create_project("Read Guard")
        main.workspace.write_file("Read Guard", "report.pdf", "%PDF fake")
        main.workspace.write_file("Read Guard", "credentials.json", '{"token":"do-not-read"}')
        binary = self.client.get("/api/file", params={"project": "Read Guard", "path": "report.pdf"}, headers=headers)
        secret = self.client.get("/api/file", params={"project": "Read Guard", "path": "credentials.json"}, headers=headers)
        self.assertEqual(binary.status_code, 400)
        self.assertIn("document analysis", binary.json()["detail"].lower())
        self.assertEqual(secret.status_code, 400)
        self.assertNotIn("do-not-read", secret.text)

    def test_project_file_listing_omits_named_secret_files(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        main.workspace.create_project("Listing Guard")
        main.workspace.write_file("Listing Guard", "notes.md", "ordinary text")
        main.workspace.write_file("Listing Guard", "credentials.json", '{"token":"secret"}')
        response = self.client.get("/api/files", params={"project": "Listing Guard"}, headers=headers)
        self.assertEqual(response.status_code, 200)
        paths = [item["path"] for item in response.json()["files"]]
        self.assertIn("notes.md", paths)
        self.assertNotIn("credentials.json", paths)

    def test_project_read_tool_does_not_decode_binary_documents_as_text(self):
        main.workspace.create_project("Tool Read Guard")
        main.workspace.write_file("Tool Read Guard", "brief.pdf", "%PDF-1.7")
        with self.assertRaisesRegex(ValueError, "document analysis"):
            main._tool_handler("project_read_file", {"path": "brief.pdf"}, "Tool Read Guard")


    def test_uploaded_document_masks_common_secrets_before_ai_use(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        payload = b'OPENAI_API_KEY=sk-proj-abcdefghijklmnop123456\nordinary=keep-me'
        response = self.client.post("/api/files/analyze-upload", files={"file": ("notes.txt", payload, "text/plain")}, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("sk-proj-abcdefghijklmnop123456", response.json()["content"])
        self.assertIn("keep-me", response.json()["content"])
        self.assertTrue(any("masked" in warning.lower() for warning in response.json()["warnings"]))

    def test_agent_file_read_masks_credentials_embedded_in_source(self):
        main.workspace.create_project("Redaction Lab")
        main.workspace.write_file("Redaction Lab", "settings.py", 'API_KEY = "sk-proj-abcdefghijklmnop123456"\nMODE = "safe"')
        result = main._tool_handler("project_read_file", {"path": "settings.py"}, "Redaction Lab")
        self.assertNotIn("sk-proj-abcdefghijklmnop123456", result["content"])
        self.assertIn("safe", result["content"])
        self.assertGreaterEqual(result["redactions"], 1)

    def test_new_document_and_analysis_skills_are_discoverable(self):
        from app.skills import discover_skills
        skills = discover_skills(main.workspace.root)
        names = {item["id"] for item in skills}
        self.assertGreaterEqual(len(skills), 18)
        self.assertTrue({"document-analysis", "spreadsheet-analysis", "presentation-analysis", "data-analysis", "web-research", "security-review"}.issubset(names))


    def test_bulk_model_verification_stream_returns_only_successful_models(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Local models", "provider": "ollama", "model": "small-model",
        }, headers=headers)
        profile_id = profile.json()["id"]
        catalog = [
            {"id": "small-model", "name": "Small"},
            {"id": "paid-model", "name": "Paid"},
            {"id": "large-model", "name": "Large"},
        ]

        def fake_probe(settings, secret):
            model = settings["model"]
            if model == "paid-model":
                raise main.ProviderError("This key or account cannot use this model.", 403)
            return {"ok": True, "status": "verified", "model": model,
                    "message": "Access verified with a minimal request."}

        with patch.object(main.ai_client, "list_model_catalog", return_value=catalog), \
             patch.object(main.ai_client, "probe_model", side_effect=fake_probe) as probe:
            response = self.client.post(f"/api/providers/{profile_id}/models/verify-all", json={"models": ["small-model", "paid-model", "large-model"]}, headers=headers)

        self.assertEqual(response.status_code, 200)
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        summary = next(event for event in events if event["type"] == "complete")
        self.assertEqual(summary["tested"], 3)
        self.assertEqual([item["id"] for item in summary["working_models"]], ["small-model", "large-model"])
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(probe.call_count, 3)

    def test_bulk_model_verification_continues_after_unexpected_probe_failure(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Local models", "provider": "ollama", "model": "good-model",
        }, headers=headers)
        profile_id = profile.json()["id"]

        def fake_probe(settings, secret):
            if settings["model"] == "broken-model":
                raise RuntimeError("private-secret diagnostic must not be exposed")
            return {"ok": True, "message": "Working."}

        with patch.object(main.ai_client, "probe_model", side_effect=fake_probe) as probe:
            response = self.client.post(
                f"/api/providers/{profile_id}/models/verify-all",
                json={"models": ["broken-model", "good-model"]}, headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        summary = next(event for event in events if event["type"] == "complete")
        self.assertEqual(summary["tested"], 2)
        self.assertEqual([item["id"] for item in summary["working_models"]], ["good-model"])
        self.assertEqual(summary["failed_count"], 1)
        self.assertNotIn("private-secret", response.text)
        self.assertEqual(probe.call_count, 2)

    def test_bulk_model_verification_requires_local_token(self):
        profile = self.client.post("/api/providers", json={"name": "Local", "provider": "ollama", "model": "m"}, headers={"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"})
        response = self.client.post(f"/api/providers/{profile.json()['id']}/models/verify-all")
        self.assertEqual(response.status_code, 401)

    def test_browser_tool_schema_exposes_safe_element_controls(self):
        tools = main._tool_schemas("deep_research", None, True)
        names = {item["function"]["name"] for item in tools}
        self.assertTrue({"browser_click_element", "browser_fill_field", "browser_select_option", "browser_set_checkbox"}.issubset(names))

    def test_browser_checkbox_tool_routes_only_check_or_uncheck(self):
        with patch.object(main.browser, "command", return_value={"ok": True, "action": "check"}) as command:
            result = main._tool_handler("browser_set_checkbox", {"label": "Remember me", "checked": True}, None)
        self.assertTrue(result["ok"])
        command.assert_called_once_with("check Remember me")

    def test_browser_command_requires_local_token_and_forwards_command(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        with patch.object(main.browser, "command", return_value={"ok": True, "action": "scroll", "title": "Example"}) as browser_command:
            unauthorized = self.client.post("/api/browser/command", json={"command": "scroll down"})
            response = self.client.post("/api/browser/command", json={"command": "scroll down"}, headers=headers)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(response.status_code, 200)
        browser_command.assert_called_once_with("scroll down")


    def test_bulk_model_verification_reports_failure_categories_without_raw_errors(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "Model diagnostics", "provider": "ollama", "model": "ok-model",
        }, headers=headers)
        profile_id = profile.json()["id"]

        def fake_probe(settings, secret):
            model = settings["model"]
            if model == "quota-model":
                raise main.ProviderError("provider diagnostic includes internal details", 429)
            if model == "premium-model":
                raise main.ProviderError("model denied", 403)
            if model == "offline-model":
                raise main.ProviderError("endpoint unavailable", 503)
            return {"ok": True, "message": "Working."}

        with patch.object(main.ai_client, "probe_model", side_effect=fake_probe):
            response = self.client.post(
                f"/api/providers/{profile_id}/models/verify-all",
                json={"models": ["ok-model", "quota-model", "premium-model", "offline-model"]},
                headers=headers,
            )

        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        summary = next(event for event in events if event["type"] == "complete")
        self.assertEqual(summary["failure_categories"], {
            "quota": 1, "access_denied": 1, "provider_unavailable": 1,
        })
        self.assertNotIn("provider diagnostic", response.text)
        failed = [event for event in events if event["type"] == "progress" and not event["ok"]]
        self.assertEqual({event["failure_category"] for event in failed}, {
            "quota", "access_denied", "provider_unavailable",
        })

    def test_bulk_model_verification_classifies_missing_key_as_authentication_problem(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        profile = self.client.post("/api/providers", json={
            "name": "No key connection", "provider": "ollama", "model": "local-example",
        }, headers=headers)
        self.assertEqual(profile.status_code, 200, profile.text)
        profile_id = profile.json()["id"]
        with patch.object(main, "profile_key_candidates", return_value=[]), \
             patch.object(main, "profile_requires_key", return_value=True):
            response = self.client.post(
                f"/api/providers/{profile_id}/models/verify-all",
                json={"models": ["gpt-example"]}, headers=headers,
            )
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        summary = next(event for event in events if event["type"] == "complete")
        self.assertEqual(summary["failure_categories"], {"missing_key": 1})


    def test_preview_endpoint_serves_saved_html_for_live_iframe(self):
        headers = {"X-Spaceline-Token": "test-token", "Authorization":"Bearer test-id-token"}
        self.client.post("/api/projects", json={"name": "Preview Lab"}, headers=headers)
        main.workspace.write_file("Preview Lab", "index.html", "<!doctype html><title>Live preview check</title><h1>It works</h1>")
        response = self.client.get("/preview/Preview%20Lab/index.html")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn(b"<h1>It works</h1>", response.content)


if __name__ == "__main__":
    unittest.main()
