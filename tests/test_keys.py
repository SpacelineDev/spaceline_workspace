import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.workspace import Workspace
from app.key_vault import KeyVault


class FakeCredentialStore:
    def __init__(self):
        self.values = {}

    def set_password(self, key_id, secret):
        self.values[key_id] = secret

    def get_password(self, key_id):
        return self.values.get(key_id)

    def delete_password(self, key_id):
        self.values.pop(key_id, None)


class KeyVaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name))
        self.fake = FakeCredentialStore()
        self.patch = patch("app.key_vault._create_store", return_value=self.fake)
        self.patch.start()
        self.vault = KeyVault(self.workspace)

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_secret_is_stored_outside_metadata_and_not_returned(self):
        created = self.vault.add_key("OpenAI", "Main key", "sk-test-secret", "https://api.openai.com/v1")
        self.assertNotIn("secret", created)
        self.assertEqual(self.vault.get_secret(created["id"]), "sk-test-secret")
        self.assertEqual(self.vault.list_keys()[0]["label"], "Main key")

    def test_delete_removes_secret_and_metadata(self):
        created = self.vault.add_key("Gemini", "Personal", "secret-value")
        self.assertTrue(self.vault.delete_key(created["id"]))
        self.assertEqual(self.vault.list_keys(), [])
        with self.assertRaises(KeyError):
            self.vault.get_secret(created["id"])


    def test_multiple_keys_for_one_provider_can_be_saved_independently(self):
        primary = self.vault.add_key("FreeLLM", "Primary", "secret-primary")
        backup = self.vault.add_key("FreeLLM", "Backup", "secret-backup")
        keys = self.vault.list_keys()
        self.assertEqual({item["label"] for item in keys}, {"Primary", "Backup"})
        self.assertEqual(self.vault.get_secret(primary["id"]), "secret-primary")
        self.assertEqual(self.vault.get_secret(backup["id"]), "secret-backup")

    def test_edenai_api_key_alias_matches_edenai_connection_pool(self):
        key = self.vault.add_key("Eden AI API", "Image gateway", "eden-secret")
        self.assertEqual(self.vault.provider_key_ids("edenai"), [key["id"]])
        self.assertEqual(self.vault.provider_key_ids("Eden AI Images"), [key["id"]])

    def test_rejects_empty_secret(self):
        with self.assertRaises(ValueError):
            self.vault.add_key("OpenAI", "Main", "")

    def test_free_llm_provider_aliases_match_same_key_pool(self):
        key = self.vault.add_key("FreeLLM API", "Gateway main", "gateway-secret")
        self.assertEqual(self.vault.provider_key_ids("freellm"), [key["id"]])
        self.assertEqual(self.vault.provider_key_ids("FreeLLM API (local gateway)"), [key["id"]])


if __name__ == "__main__":
    unittest.main()
