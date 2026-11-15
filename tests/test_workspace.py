import tempfile
import unittest
from pathlib import Path

from app.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_create_project_and_list_projects(self):
        project = self.workspace.create_project("Study Lab")
        self.assertTrue(project.is_dir())
        self.assertEqual(self.workspace.list_projects(), ["Study Lab"])

    def test_file_round_trip(self):
        self.workspace.create_project("Study Lab")
        self.workspace.write_file("Study Lab", "main.py", "print('hello')")
        self.assertEqual(self.workspace.read_file("Study Lab", "main.py"), "print('hello')")

    def test_rejects_path_traversal(self):
        self.workspace.create_project("Study Lab")
        with self.assertRaises(ValueError):
            self.workspace.write_file("Study Lab", "../outside.txt", "bad")

    def test_create_file_does_not_overwrite_existing_data(self):
        self.workspace.create_project("Study Lab")
        self.workspace.write_file("Study Lab", "main.py", "keep me")
        with self.assertRaises(FileExistsError):
            self.workspace.create_file("Study Lab", "main.py")
        self.assertEqual(self.workspace.read_file("Study Lab", "main.py"), "keep me")


    def test_file_listing_skips_dependency_and_hidden_folders(self):
        self.workspace.create_project("Demo")
        self.workspace.write_file("Demo", "main.py", "print('ok')")
        self.workspace.write_file("Demo", "node_modules/pkg/index.js", "not project source")
        self.workspace.write_file("Demo", ".hidden/config.json", "hidden")
        listed = [item["path"] for item in self.workspace.list_files("Demo")]
        self.assertIn("main.py", listed)
        self.assertFalse(any("node_modules" in item for item in listed))
        self.assertFalse(any(".hidden" in item for item in listed))


    def test_safe_path_rejects_symlinks_even_when_the_target_is_inside_project(self):
        self.workspace.create_project("Demo")
        self.workspace.write_file("Demo", ".env", "SECRET=do-not-read")
        project = self.workspace.project_path("Demo")
        alias = project / "notes.txt"
        try:
            alias.symlink_to(project / ".env")
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is unavailable on this platform")
        with self.assertRaises(ValueError):
            self.workspace.safe_path("Demo", "notes.txt")

    def test_file_listing_omits_symlinked_files(self):
        self.workspace.create_project("Demo")
        self.workspace.write_file("Demo", "actual.txt", "safe")
        project = self.workspace.project_path("Demo")
        alias = project / "alias.txt"
        try:
            alias.symlink_to(project / "actual.txt")
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation is unavailable on this platform")
        listed = [item["path"] for item in self.workspace.list_files("Demo")]
        self.assertIn("actual.txt", listed)
        self.assertNotIn("alias.txt", listed)

    def test_rejects_invalid_project_names(self):
        with self.assertRaises(ValueError):
            self.workspace.create_project("../outside")

    def test_notes_persist_and_search(self):
        first = self.workspace.save_note("Python basics", "Variables and loops")
        self.assertEqual(first["title"], "Python basics")
        results = self.workspace.list_notes("loops")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], first["id"])

    def test_note_can_be_deleted(self):
        note = self.workspace.save_note("Temporary", "Delete me")
        self.assertTrue(self.workspace.delete_note(note["id"]))
        self.assertEqual(self.workspace.list_notes(), [])


    def test_provider_profiles_and_active_selection_persist(self):
        profile = self.workspace.create_profile({
            "name":"Local Qwen", "provider":"ollama", "base_url":"http://127.0.0.1:11434",
            "model":"qwen2.5:7b", "key_id":None,
        })
        self.workspace.set_active_profile(profile["id"])
        reopened = Workspace(Path(self.temp.name))
        self.assertEqual(reopened.get_active_profile_id(), profile["id"])
        self.assertEqual(reopened.get_profile(profile["id"])["model"], "qwen2.5:7b")


    def test_provider_profiles_have_enabled_state_and_can_be_toggled(self):
        profile = self.workspace.create_profile({
            "name": "Groq enabled", "provider": "groq", "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-test", "key_id": "key-a",
        })
        self.assertTrue(profile["enabled"])
        self.workspace.set_profile_enabled(profile["id"], False)
        self.assertFalse(self.workspace.get_profile(profile["id"])["enabled"])

    def test_chat_history_persists_across_reopen(self):
        chat = self.workspace.create_conversation("New chat")
        self.workspace.add_message(chat["id"], "user", "Build a FastAPI app")
        self.workspace.add_message(chat["id"], "assistant", "Let's start with a route.")
        reopened = Workspace(Path(self.temp.name))
        loaded = reopened.get_conversation(chat["id"])
        self.assertEqual(loaded["title"], "Build a FastAPI app")
        self.assertEqual([m["role"] for m in loaded["messages"]], ["user", "assistant"])

    def test_provider_profile_key_pool_persists_multiple_keys_and_primary(self):
        profile = self.workspace.create_profile({
            "name": "Groq fast", "provider": "groq", "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-test", "key_id": "key-primary",
        })
        self.assertEqual(self.workspace.get_profile_key_ids(profile["id"]), ["key-primary"])
        self.workspace.set_profile_key_ids(profile["id"], ["key-backup", "key-primary"])
        self.assertEqual(self.workspace.get_profile_key_ids(profile["id"]), ["key-backup", "key-primary"])
        self.assertEqual(self.workspace.get_profile(profile["id"])["key_id"], "key-backup")
        reopened = Workspace(Path(self.temp.name))
        self.assertEqual(reopened.get_profile_key_ids(profile["id"]), ["key-backup", "key-primary"])
    def test_provider_auth_mode_persists_and_defaults_for_existing_profiles(self):
        profile = self.workspace.create_profile({
            "name": "Gateway", "provider": "freellm", "base_url": "http://127.0.0.1:31415/v1",
            "model": "model-a", "key_id": "key-a", "auth_mode": "x-api-key",
        })
        self.assertEqual(profile["auth_mode"], "x-api-key")
        self.workspace.update_profile(profile["id"], {
            "name": "Gateway", "provider": "freellm", "base_url": "http://127.0.0.1:31415/v1",
            "model": "model-b", "key_id": "key-a", "auth_mode": "none",
        })
        reopened = Workspace(Path(self.temp.name))
        self.assertEqual(reopened.get_profile(profile["id"])["auth_mode"], "none")

    def test_old_provider_profiles_table_is_migrated_without_losing_rows(self):
        import sqlite3
        root = Path(self.temp.name) / "legacy"
        root.mkdir()
        db_path = root / ".spaceline-data.sqlite3"
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE provider_profiles (id TEXT PRIMARY KEY, name TEXT NOT NULL, provider TEXT NOT NULL, base_url TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', key_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            db.execute("INSERT INTO provider_profiles VALUES ('legacy-id','Old','freellm','http://127.0.0.1:31415/v1','old-model','key-old','now','now')")
        reopened = Workspace(root)
        profile = reopened.get_profile("legacy-id")
        self.assertEqual(profile["model"], "old-model")
        self.assertEqual(profile["auth_mode"], "bearer")


if __name__ == "__main__":
    unittest.main()
