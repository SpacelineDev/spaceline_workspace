from pathlib import Path
import tempfile
import unittest

from app.user_storage import UserStorageManager
from app.workspace import Workspace


class UserStorageIsolationTests(unittest.TestCase):
    def test_first_verified_user_claims_legacy_workspace_and_second_user_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            legacy_project = base / "Old Project"
            legacy_project.mkdir()
            (legacy_project / "notes.txt").write_text("legacy user's data", encoding="utf-8")
            manager = UserStorageManager(base)

            first_root = manager.root_for("firebase-user-one")
            self.assertTrue((first_root / "Old Project" / "notes.txt").is_file())
            self.assertFalse(legacy_project.exists())

            second_root = manager.root_for("firebase-user-two")
            self.assertNotEqual(first_root, second_root)
            self.assertFalse((second_root / "Old Project").exists())

            first_workspace = Workspace(first_root)
            second_workspace = Workspace(second_root)
            first_workspace.create_project("Private One")
            self.assertIn("Private One", first_workspace.list_projects())
            self.assertNotIn("Private One", second_workspace.list_projects())

    def test_uid_is_never_used_as_a_path_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = UserStorageManager(Path(tmp))
            path = manager.root_for("../../somewhere/else")
            self.assertTrue(path.is_relative_to(Path(tmp).resolve()))

    def test_empty_uid_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                UserStorageManager(Path(tmp)).root_for("")


    def test_incomplete_migration_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manager = UserStorageManager(base)
            manager.marker_path.write_text('{"uid_sha256":"' + ('a' * 32) + '","status":"migrating"}', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                manager.root_for("firebase-user-two")


if __name__ == "__main__":
    unittest.main()
