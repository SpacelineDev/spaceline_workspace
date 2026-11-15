import tempfile
import unittest
from pathlib import Path

from app.workspace import Workspace


class AISettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_settings_round_trip_and_survive_workspace_reopen(self):
        expected = {
            "provider": "openai-compatible",
            "base_url": "https://api.example.test/v1",
            "model": "model-a",
            "key_id": "key-123",
        }
        self.workspace.save_ai_settings(expected)
        reopened = Workspace(Path(self.temp.name))
        actual = reopened.get_ai_settings()
        for key, value in expected.items():
            self.assertEqual(actual[key], value)

    def test_default_settings_are_local_and_keyless(self):
        settings = self.workspace.get_ai_settings()
        self.assertEqual(settings["provider"], "ollama")
        self.assertEqual(settings["base_url"], "http://127.0.0.1:11434")
        self.assertIsNone(settings["key_id"])
        self.assertEqual(settings["model"], "")


if __name__ == "__main__":
    unittest.main()
