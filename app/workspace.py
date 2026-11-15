from __future__ import annotations

import os
import re
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,49}$")
MAX_FILE_BYTES = 1_500_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Workspace:
    """Filesystem-backed projects and a local SQLite database for workspace state."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / ".spaceline-data.sqlite3"
        self._init_db()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS key_metadata (
                id TEXT PRIMARY KEY, provider TEXT NOT NULL, label TEXT NOT NULL,
                base_url TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS ai_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1), provider TEXT NOT NULL,
                base_url TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', key_id TEXT,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS provider_profiles (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, provider TEXT NOT NULL,
                base_url TEXT NOT NULL, model TEXT NOT NULL DEFAULT '', key_id TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                auth_mode TEXT NOT NULL DEFAULT 'bearer')""")
            # Upgrade workspaces created by earlier Spaceline versions without resetting data.
            profile_columns = {row[1] for row in db.execute("PRAGMA table_info(provider_profiles)").fetchall()}
            if "auth_mode" not in profile_columns:
                db.execute("ALTER TABLE provider_profiles ADD COLUMN auth_mode TEXT NOT NULL DEFAULT 'bearer'")
            if "enabled" not in profile_columns:
                db.execute("ALTER TABLE provider_profiles ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
            db.execute("""CREATE TABLE IF NOT EXISTS provider_profile_keys (
                profile_id TEXT NOT NULL, key_id TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(profile_id, key_id),
                FOREIGN KEY(profile_id) REFERENCES provider_profiles(id) ON DELETE CASCADE)""")
            db.execute("""CREATE TABLE IF NOT EXISTS workspace_preferences (
                id INTEGER PRIMARY KEY CHECK (id = 1), active_profile_id TEXT,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS personalization_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1), settings_json TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, profile_id TEXT,
                model TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'complete',
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)")

    # --- Projects and files -------------------------------------------------
    def _validate_project_name(self, name: str) -> str:
        clean = (name or "").strip()
        if clean in {".", ".."} or not PROJECT_NAME_RE.fullmatch(clean):
            raise ValueError("Use 1–50 letters, numbers, spaces, dots, dashes or underscores for the project name.")
        return clean

    def create_project(self, name: str) -> Path:
        clean = self._validate_project_name(name)
        target = (self.root / clean).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Invalid project path.")
        if target.exists():
            raise ValueError("A project with that name already exists.")
        target.mkdir(parents=True)
        (target / "README.md").write_text(f"# {clean}\n\nYour project workspace.\n", encoding="utf-8")
        return target

    def list_projects(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir()
                      if p.is_dir() and not p.name.startswith(".") and PROJECT_NAME_RE.fullmatch(p.name))

    def project_path(self, project: str) -> Path:
        clean = self._validate_project_name(project)
        target = (self.root / clean).resolve()
        if not target.is_relative_to(self.root) or not target.is_dir():
            raise FileNotFoundError("Project not found.")
        return target

    def safe_path(self, project: str, relative_path: str) -> Path:
        base = self.project_path(project)
        raw = (relative_path or "").strip()
        normalised = raw.replace("\\", "/")
        if not normalised or normalised.startswith("/") or "\x00" in normalised:
            raise ValueError("Choose a valid path inside the project.")
        parts = normalised.split("/")
        if any(part in {"", ".", ".."} for part in parts) or ":" in parts[0]:
            raise ValueError("Path traversal is not allowed.")
        candidate = base
        for part in parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("Symbolic links are not allowed in project file paths.")
        target = candidate.resolve()
        if not target.is_relative_to(base):
            raise ValueError("Path must stay inside the project.")
        return target

    def list_files(self, project: str) -> list[dict[str, Any]]:
        base = self.project_path(project)
        result: list[dict[str, Any]] = []
        ignored = {"node_modules", "vendor", ".git", ".venv", "venv", "env",
                   "__pycache__", "dist", "build", "target", ".next", ".cache", "coverage"}
        visible_hidden_dirs = {".github", ".vscode", ".husky", ".devcontainer"}
        visible_hidden_files = {".gitignore", ".dockerignore", ".gitattributes", ".editorconfig",
                                ".prettierrc", ".prettierignore", ".eslintignore", ".watchmanconfig"}
        for current, directories, filenames in os.walk(base, followlinks=False):
            current_path = Path(current)
            relative_dir = current_path.relative_to(base)
            depth = len(relative_dir.parts)
            directories[:] = [name for name in directories
                              if (not name.startswith(".") or name.lower() in visible_hidden_dirs)
                              and name.lower() not in ignored and depth < 6
                              and not (current_path / name).is_symlink()]
            for name in directories:
                path = current_path / name
                relative = path.relative_to(base).as_posix()
                result.append({"path": relative, "type": "folder", "size": 0})
            for name in filenames:
                if name.startswith(".") and name.lower() not in visible_hidden_files:
                    continue
                path = current_path / name
                if path.is_symlink():
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                relative = path.relative_to(base).as_posix()
                result.append({"path": relative, "type": "file", "size": size})
        return sorted(result, key=lambda item: (item["type"] == "file", item["path"].lower()))

    def read_file(self, project: str, relative_path: str) -> str:
        target = self.safe_path(project, relative_path)
        if not target.is_file():
            raise FileNotFoundError("File not found.")
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("This file is too large to open in the editor (1.5 MB limit).")
        return target.read_text(encoding="utf-8", errors="replace")

    def write_file(self, project: str, relative_path: str, content: str) -> None:
        target = self.safe_path(project, relative_path)
        data = content.encode("utf-8")
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Files are limited to 1.5 MB in the editor.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".spaceline-tmp")
        temp.write_bytes(data)
        temp.replace(target)

    def create_folder(self, project: str, relative_path: str) -> None:
        self.safe_path(project, relative_path).mkdir(parents=True, exist_ok=True)

    def create_file(self, project: str, relative_path: str) -> None:
        target = self.safe_path(project, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError("A file or folder already exists at that path.")
        target.touch()

    def delete_file(self, project: str, relative_path: str) -> None:
        target = self.safe_path(project, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("File not found.")
        target.unlink()

    # --- Notes / artifacts -------------------------------------------------
    def save_note(self, title: str, content: str, note_id: str | None = None) -> dict[str, str]:
        title = (title or "").strip()
        if not title or len(title) > 120:
            raise ValueError("Give this saved item a title (maximum 120 characters).")
        if len(content) > 200_000:
            raise ValueError("Saved items are limited to 200,000 characters.")
        now = utc_now()
        with self._connect() as db:
            if note_id:
                cur = db.execute("UPDATE notes SET title=?, content=?, updated_at=? WHERE id=?",
                                 (title, content, now, note_id))
                if cur.rowcount == 0:
                    raise FileNotFoundError("Saved item not found.")
                row = db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
            else:
                note_id = uuid4().hex[:12]
                db.execute("INSERT INTO notes (id,title,content,created_at,updated_at) VALUES (?,?,?,?,?)",
                           (note_id, title, content, now, now))
                row = db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        return dict(row)

    def list_notes(self, query: str = "") -> list[dict[str, str]]:
        with self._connect() as db:
            if query.strip():
                term = f"%{query.strip()}%"
                rows = db.execute("SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
                                  (term, term)).fetchall()
            else:
                rows = db.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def delete_note(self, note_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM notes WHERE id=?", (note_id,))
        return cur.rowcount > 0

    # --- Provider profiles -------------------------------------------------
    def create_profile(self, values: dict[str, Any]) -> dict[str, Any]:
        profile_id = uuid4().hex[:16]
        now = utc_now()
        key_ids = list(dict.fromkeys(values.get("key_ids") or ([values.get("key_id")] if values.get("key_id") else [])))
        primary_key = values.get("key_id") or (key_ids[0] if key_ids else None)
        if primary_key and primary_key not in key_ids:
            key_ids.insert(0, primary_key)
        with self._connect() as db:
            db.execute("INSERT INTO provider_profiles (id,name,provider,base_url,model,key_id,created_at,updated_at,auth_mode,enabled) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (profile_id, values["name"], values["provider"], values["base_url"], values.get("model", ""),
                        primary_key, now, now, values.get("auth_mode", "bearer"), 1 if values.get("enabled", True) else 0))
            for position, key_id in enumerate(key_ids):
                db.execute("INSERT OR IGNORE INTO provider_profile_keys (profile_id,key_id,position) VALUES (?,?,?)",
                           (profile_id, key_id, position))
        return self.get_profile(profile_id)

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM provider_profiles ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM provider_profiles WHERE id=?", (profile_id,)).fetchone()
        if row is None:
            raise KeyError("Provider profile not found.")
        return dict(row)

    def update_profile(self, profile_id: str, values: dict[str, Any]) -> dict[str, Any]:
        key_ids = list(dict.fromkeys(values.get("key_ids") or ([values.get("key_id")] if values.get("key_id") else [])))
        primary_key = values.get("key_id") or (key_ids[0] if key_ids else None)
        if primary_key and primary_key not in key_ids:
            key_ids.insert(0, primary_key)
        with self._connect() as db:
            cur = db.execute("UPDATE provider_profiles SET name=?,provider=?,base_url=?,model=?,key_id=?,updated_at=?,auth_mode=?,enabled=? WHERE id=?",
                             (values["name"], values["provider"], values["base_url"], values.get("model", ""),
                              primary_key, utc_now(), values.get("auth_mode", "bearer"),
                              1 if values.get("enabled", True) else 0, profile_id))
            if cur.rowcount == 0:
                raise KeyError("Provider profile not found.")
            db.execute("DELETE FROM provider_profile_keys WHERE profile_id=?", (profile_id,))
            for position, key_id in enumerate(key_ids):
                db.execute("INSERT OR IGNORE INTO provider_profile_keys (profile_id,key_id,position) VALUES (?,?,?)",
                           (profile_id, key_id, position))
        return self.get_profile(profile_id)

    def set_profile_enabled(self, profile_id: str, enabled: bool) -> dict[str, Any]:
        self.get_profile(profile_id)
        with self._connect() as db:
            db.execute("UPDATE provider_profiles SET enabled=?,updated_at=? WHERE id=?",
                       (1 if enabled else 0, utc_now(), profile_id))
        return self.get_profile(profile_id)

    def get_profile_key_ids(self, profile_id: str) -> list[str]:
        profile = self.get_profile(profile_id)
        with self._connect() as db:
            rows = db.execute("SELECT key_id FROM provider_profile_keys WHERE profile_id=? ORDER BY position ASC",
                              (profile_id,)).fetchall()
        ids = [row[0] for row in rows]
        # Migrate older profiles that predate the key-pool table.
        if not ids and profile.get("key_id"):
            ids = [profile["key_id"]]
        return ids

    def set_profile_key_ids(self, profile_id: str, key_ids: list[str]) -> None:
        self.get_profile(profile_id)
        unique_ids = list(dict.fromkeys(str(value) for value in key_ids if value))
        with self._connect() as db:
            db.execute("DELETE FROM provider_profile_keys WHERE profile_id=?", (profile_id,))
            for position, key_id in enumerate(unique_ids):
                db.execute("INSERT INTO provider_profile_keys (profile_id,key_id,position) VALUES (?,?,?)",
                           (profile_id, key_id, position))
            db.execute("UPDATE provider_profiles SET key_id=?,updated_at=? WHERE id=?",
                       (unique_ids[0] if unique_ids else None, utc_now(), profile_id))

    def delete_profile(self, profile_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM provider_profiles WHERE id=?", (profile_id,))
            if cur.rowcount:
                db.execute("UPDATE workspace_preferences SET active_profile_id=NULL WHERE active_profile_id=?", (profile_id,))
        return cur.rowcount > 0

    def get_active_profile_id(self) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT active_profile_id FROM workspace_preferences WHERE id=1").fetchone()
        return row[0] if row else None

    def set_active_profile(self, profile_id: str | None) -> None:
        if profile_id:
            self.get_profile(profile_id)
        with self._connect() as db:
            db.execute("INSERT INTO workspace_preferences (id,active_profile_id,updated_at) VALUES (1,?,?) "
                       "ON CONFLICT(id) DO UPDATE SET active_profile_id=excluded.active_profile_id, updated_at=excluded.updated_at",
                       (profile_id, utc_now()))

    # --- Persistent chat history ------------------------------------------
    def create_conversation(self, title: str = "New chat", profile_id: str | None = None, model: str = "") -> dict[str, Any]:
        conversation_id = uuid4().hex[:20]
        now = utc_now()
        with self._connect() as db:
            db.execute("INSERT INTO conversations (id,title,profile_id,model,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                       (conversation_id, title[:120], profile_id, model, now, now))
        return self.get_conversation(conversation_id)

    def list_conversations(self, query: str = "", limit: int = 80) -> list[dict[str, Any]]:
        with self._connect() as db:
            if query.strip():
                term = f"%{query.strip()}%"
                rows = db.execute("SELECT c.*, (SELECT substr(m.content,1,180) FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS preview "
                                  "FROM conversations c WHERE c.title LIKE ? OR EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id=c.id AND m.content LIKE ?) "
                                  "ORDER BY c.updated_at DESC LIMIT ?", (term, term, limit)).fetchall()
            else:
                rows = db.execute("SELECT c.*, (SELECT substr(m.content,1,180) FROM messages m WHERE m.conversation_id=c.id ORDER BY m.id DESC LIMIT 1) AS preview "
                                  "FROM conversations c ORDER BY c.updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if row is None:
                raise KeyError("Conversation not found.")
            messages = db.execute("SELECT id,role,content,status,created_at FROM messages WHERE conversation_id=? ORDER BY id",
                                  (conversation_id,)).fetchall()
        result = dict(row)
        result["messages"] = [dict(message) for message in messages]
        return result

    def add_message(self, conversation_id: str, role: str, content: str, status: str = "complete") -> dict[str, Any]:
        if role not in {"user", "assistant", "system", "tool"}:
            raise ValueError("Invalid message role.")
        if len(content) > 200_000:
            raise ValueError("Chat messages are limited to 200,000 characters.")
        now = utc_now()
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
                raise KeyError("Conversation not found.")
            cur = db.execute("INSERT INTO messages (conversation_id,role,content,status,created_at) VALUES (?,?,?,?,?)",
                             (conversation_id, role, content, status, now))
            if role == "user":
                first = db.execute("SELECT count(*) FROM messages WHERE conversation_id=? AND role='user'", (conversation_id,)).fetchone()[0]
                if first == 1:
                    title = re.sub(r"\s+", " ", content).strip()[:72] or "New chat"
                    db.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=?", (title, now, conversation_id))
                else:
                    db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
            else:
                db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
            row = db.execute("SELECT id,role,content,status,created_at FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def update_conversation_profile(self, conversation_id: str, profile_id: str | None, model: str) -> None:
        with self._connect() as db:
            cur = db.execute("UPDATE conversations SET profile_id=?,model=?,updated_at=? WHERE id=?",
                             (profile_id, model, utc_now(), conversation_id))
            if cur.rowcount == 0:
                raise KeyError("Conversation not found.")

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as db:
            cur = db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        return cur.rowcount > 0

    # --- Personal response preferences ------------------------------------
    @staticmethod
    def default_personalization_settings() -> dict[str, Any]:
        return {
            "name": "", "about": "", "tone": "direct", "detail": "balanced",
            "format": "adaptive", "thinking_style": "balanced", "challenge_assumptions": True, "explain_steps": True,
            "include_examples": True, "ask_when_ambiguous": True, "custom_instructions": "",
        }

    def get_personalization_settings(self) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT settings_json FROM personalization_settings WHERE id=1").fetchone()
        if row is None:
            return self.default_personalization_settings()
        try:
            stored = json.loads(row["settings_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        # Unknown future keys are ignored; missing keys receive safe defaults.
        result = self.default_personalization_settings()
        result.update({key: value for key, value in stored.items() if key in result})
        return result

    def save_personalization_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        clean = self.default_personalization_settings()
        clean.update({key: value for key, value in settings.items() if key in clean})
        now = utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO personalization_settings (id,settings_json,updated_at) VALUES (1,?,?) "
                "ON CONFLICT(id) DO UPDATE SET settings_json=excluded.settings_json,updated_at=excluded.updated_at",
                (json.dumps(clean, ensure_ascii=False), now),
            )
        return self.get_personalization_settings()

    # --- Legacy single-provider settings (kept for old workspaces) --------
    def get_ai_settings(self) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT provider,base_url,model,key_id,updated_at FROM ai_settings WHERE id=1").fetchone()
        if row is None:
            return {"provider": "ollama", "base_url": "http://127.0.0.1:11434", "model": "", "key_id": None, "updated_at": None}
        return dict(row)

    def save_ai_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as db:
            db.execute("INSERT INTO ai_settings (id,provider,base_url,model,key_id,updated_at) VALUES (1,?,?,?,?,?) "
                       "ON CONFLICT(id) DO UPDATE SET provider=excluded.provider,base_url=excluded.base_url,model=excluded.model,key_id=excluded.key_id,updated_at=excluded.updated_at",
                       (settings["provider"], settings["base_url"], settings["model"], settings.get("key_id"), now))
        return self.get_ai_settings()
