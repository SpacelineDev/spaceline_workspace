import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main as main
from app.key_vault import KeyVault
from app.workspace import Workspace


class PersonalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_workspace = main.workspace
        self.original_vault = main.key_vault
        self.original_token = main.app_token
        main.workspace = Workspace(Path(self.temp.name))
        main.key_vault = KeyVault(main.workspace)
        main.app_token = "personalization-test-token"
        self.client = TestClient(main.app)
        self.headers = {"X-Spaceline-Token": main.app_token}

    def tearDown(self):
        main.workspace = self.original_workspace
        main.key_vault = self.original_vault
        main.app_token = self.original_token
        self.temp.cleanup()

    def test_personalization_has_safe_defaults_and_requires_local_session(self):
        self.assertEqual(self.client.get("/api/personalization").status_code, 401)
        response = self.client.get("/api/personalization", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tone"], "direct")
        self.assertEqual(response.json()["thinking_style"], "balanced")
        self.assertEqual(self.client.put("/api/personalization", json={}).status_code, 401)
        self.assertEqual(response.json()["detail"], "balanced")
        self.assertEqual(response.json()["custom_instructions"], "")

    def test_personalization_saves_and_survives_workspace_restart(self):
        payload = {
            "name": "Koushik",
            "about": "First-year computer science student learning AI/ML.",
            "tone": "friendly",
            "detail": "detailed",
            "format": "step_by_step",
            "thinking_style": "analytical",
            "challenge_assumptions": True,
            "explain_steps": True,
            "include_examples": True,
            "ask_when_ambiguous": False,
            "custom_instructions": "Use practical examples and point out mistakes directly.",
        }
        response = self.client.put("/api/personalization", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        reopened = Workspace(Path(self.temp.name))
        self.assertEqual(reopened.get_personalization_settings(), payload)

    def test_personalization_rejects_oversized_custom_instructions(self):
        response = self.client.put("/api/personalization", json={
            "custom_instructions": "x" * 5001
        }, headers=self.headers)
        self.assertEqual(response.status_code, 422)

    def test_chat_personalization_is_added_to_system_context_without_changing_model_route(self):
        headers = self.headers
        with patch.object(main.key_vault, "list_keys", return_value=[]):
            profile = self.client.post("/api/providers", json={
                "name": "Local model", "provider": "ollama", "model": "test-model"
            }, headers=headers)
        self.assertEqual(profile.status_code, 200, profile.text)
        profile_id = profile.json()["id"]
        saved = self.client.put("/api/personalization", json={
            "name": "Koushik", "tone": "direct", "detail": "detailed",
            "format": "step_by_step", "thinking_style": "analytical", "custom_instructions": "Show concise working examples."
        }, headers=headers)
        self.assertEqual(saved.status_code, 200, saved.text)
        chat = self.client.post("/api/chats", json={"profile_id": profile_id}, headers=headers)
        self.assertEqual(chat.status_code, 200, chat.text)
        captured = {}

        def fake_stream(profile_arg, messages):
            captured["profile"] = profile_arg
            captured["messages"] = messages
            yield "ok"

        with patch.object(main, "stream_profile_chat", side_effect=fake_stream):
            response = self.client.post(
                f"/api/chats/{chat.json()['id']}/messages",
                json={"content": "Explain Python variables.", "profile_id": profile_id,
                      "model": "test-model", "task_mode": "chat"},
                headers=headers,
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.text
        self.assertIn('"delta": "ok"', body)
        self.assertEqual(captured["profile"]["model"], "test-model")
        system_message = captured["messages"][0]["content"]
        self.assertIn("Koushik", system_message)
        self.assertIn("Show concise working examples.", system_message)
        self.assertIn("Problem-solving style:", system_message)
        self.assertIn("decompose complex problems", system_message)


if __name__ == "__main__":
    unittest.main()
