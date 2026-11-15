from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path


class UserStorageManager:
    """Resolve a verified Firebase UID to a private workspace directory.

    The first authenticated UID claims any legacy, installation-wide data by
    moving it into that user's directory. Later UIDs receive clean directories.
    Only a SHA-256 UID fingerprint is written to the ownership marker/path.
    """

    OWNER_MARKER = ".spaceline-user-owner.json"

    def __init__(self, base_root: Path):
        self.base_root = Path(base_root).expanduser().resolve()
        self.users_root = self.base_root / ".spaceline-users"
        self.marker_path = self.base_root / self.OWNER_MARKER
        self._lock = threading.RLock()

    @staticmethod
    def uid_key(uid: str) -> str:
        value = str(uid or "").strip()
        if not value:
            raise ValueError("A verified Firebase user ID is required for workspace storage.")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]

    @contextmanager
    def _interprocess_lock(self):
        """Serialize claims across multiple Spaceline processes sharing a root."""
        self.base_root.mkdir(parents=True, exist_ok=True)
        lock_path = self.base_root / ".spaceline-users.lock"
        with lock_path.open("a+b") as handle:
            if os.name == "nt":
                import msvcrt
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_owner(self) -> str | None:
        try:
            payload = json.loads(self.marker_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError):
            raise RuntimeError("Spaceline's workspace ownership marker is unreadable. Stop the app and inspect the workspace before continuing.") from None
        if not isinstance(payload, dict):
            raise RuntimeError("Spaceline's workspace ownership marker is invalid. Stop the app and inspect the workspace before continuing.")
        owner = payload.get("uid_sha256")
        status = payload.get("status", "claimed")
        if not isinstance(owner, str) or len(owner) != 32 or status != "claimed":
            raise RuntimeError("Spaceline workspace migration is incomplete or the ownership marker is invalid. Restore from backup or inspect the migration before signing in.")
        return owner

    def _claim_legacy_data(self, uid_key: str, destination: Path) -> None:
        self.base_root.mkdir(parents=True, exist_ok=True)
        self.users_root.mkdir(parents=True, exist_ok=True)
        destination.mkdir(parents=True, exist_ok=True)

        # Write a pending marker before moving anything. If the process stops
        # mid-migration, the next login fails closed instead of allowing another
        # account to claim whatever data remains at the legacy root.
        marker_tmp = self.marker_path.with_suffix(".tmp")
        marker_tmp.write_text(json.dumps({"uid_sha256": uid_key, "status": "migrating"}, separators=(",", ":")), encoding="utf-8")
        marker_tmp.replace(self.marker_path)

        # Move all legacy workspace contents except the new user directory and
        # the ownership marker. This preserves projects, SQLite state, images,
        # browser profile and imported skills for the first verified account.
        for child in list(self.base_root.iterdir()):
            if child.name in {".spaceline-users", ".spaceline-users.lock", self.OWNER_MARKER}:
                continue
            target = destination / child.name
            if target.exists():
                raise RuntimeError(f"Cannot safely assign legacy workspace data: '{child.name}' already exists in the new user folder.")
            shutil.move(str(child), str(target))

        marker_tmp.write_text(json.dumps({"uid_sha256": uid_key, "status": "claimed"}, separators=(",", ":")), encoding="utf-8")
        marker_tmp.replace(self.marker_path)

    def root_for(self, uid: str) -> Path:
        key = self.uid_key(uid)
        destination = self.users_root / key
        with self._lock, self._interprocess_lock():
            owner = self._read_owner()
            if owner is None:
                self._claim_legacy_data(key, destination)
            else:
                self.users_root.mkdir(parents=True, exist_ok=True)
                destination.mkdir(parents=True, exist_ok=True)
            return destination.resolve()
