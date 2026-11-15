from __future__ import annotations

import ctypes
import os
import re
import sqlite3
from ctypes import wintypes
from typing import Any
from uuid import uuid4

from app.workspace import Workspace, utc_now

SERVICE_NAME = "Spaceline.APIKeys"
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """Thin wrapper around Windows Credential Manager generic credentials."""

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("The secure API-key vault currently requires Windows Credential Manager.")
        self.advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self.advapi.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIALW), wintypes.DWORD]
        self.advapi.CredWriteW.restype = wintypes.BOOL
        self.advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
        self.advapi.CredReadW.restype = wintypes.BOOL
        self.advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self.advapi.CredDeleteW.restype = wintypes.BOOL
        self.advapi.CredFree.argtypes = [ctypes.c_void_p]
        self.advapi.CredFree.restype = None

    @staticmethod
    def _target(key_id: str) -> str:
        return f"{SERVICE_NAME}/{key_id}"

    def set_password(self, key_id: str, secret: str) -> None:
        encoded = secret.encode("utf-8")
        if len(encoded) > 2500:
            raise ValueError("Windows Credential Manager supports API secrets up to 2,500 bytes here.")
        blob = ctypes.create_string_buffer(encoded)
        credential = _CREDENTIALW()
        credential.Flags = 0
        credential.Type = CRED_TYPE_GENERIC
        credential.TargetName = self._target(key_id)
        credential.Comment = "Stored by Spaceline"
        credential.CredentialBlobSize = len(encoded)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))
        credential.Persist = CRED_PERSIST_LOCAL_MACHINE
        credential.AttributeCount = 0
        credential.Attributes = None
        credential.TargetAlias = None
        credential.UserName = "Spaceline"
        if not self.advapi.CredWriteW(ctypes.byref(credential), 0):
            error = ctypes.get_last_error()
            raise OSError(error, ctypes.FormatError(error))

    def get_password(self, key_id: str) -> str | None:
        pointer = ctypes.POINTER(_CREDENTIALW)()
        ok = self.advapi.CredReadW(self._target(key_id), CRED_TYPE_GENERIC, 0, ctypes.byref(pointer))
        if not ok:
            error = ctypes.get_last_error()
            if error == ERROR_NOT_FOUND:
                return None
            raise OSError(error, ctypes.FormatError(error))
        try:
            item = pointer.contents
            raw = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
            return raw.decode("utf-8")
        finally:
            self.advapi.CredFree(pointer)

    def delete_password(self, key_id: str) -> None:
        if not self.advapi.CredDeleteW(self._target(key_id), CRED_TYPE_GENERIC, 0):
            error = ctypes.get_last_error()
            if error != ERROR_NOT_FOUND:
                raise OSError(error, ctypes.FormatError(error))


def _create_store():
    return WindowsCredentialStore()


class KeyVault:
    """Stores API-key metadata in SQLite and secret values in Windows Credential Manager."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self._store_instance = None

    def _store(self):
        if self._store_instance is None:
            self._store_instance = _create_store()
        return self._store_instance

    def add_key(self, provider: str, label: str, secret: str, base_url: str = "") -> dict[str, Any]:
        provider = (provider or "").strip()
        label = (label or "").strip()
        secret = (secret or "").strip()
        base_url = (base_url or "").strip()
        if not provider or len(provider) > 40:
            raise ValueError("Provider is required (maximum 40 characters).")
        if not label or len(label) > 80:
            raise ValueError("Give this key a name (maximum 80 characters).")
        if not secret:
            raise ValueError("API key cannot be empty.")
        if len(secret.encode("utf-8")) > 2500 or len(base_url) > 300:
            raise ValueError("Key or base URL is too long. API secrets are limited to 2,500 bytes.")
        key_id = uuid4().hex[:16]
        store = self._store()
        try:
            store.set_password(key_id, secret)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError(f"Windows secure storage could not save this key: {exc}") from exc
        try:
            with self.workspace._connect() as db:
                db.execute(
                    "INSERT INTO key_metadata (id, provider, label, base_url, created_at) VALUES (?, ?, ?, ?, ?)",
                    (key_id, provider, label, base_url, utc_now()),
                )
        except Exception:
            try:
                store.delete_password(key_id)
            except Exception:
                pass
            raise
        return {"id": key_id, "provider": provider, "label": label, "base_url": base_url}

    def list_keys(self) -> list[dict[str, Any]]:
        with self.workspace._connect() as db:
            rows = db.execute(
                "SELECT id, provider, label, base_url, created_at FROM key_metadata ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]


    @staticmethod
    def _provider_id(value: str) -> str:
        raw = (value or "").strip().lower()
        squashed = re.sub(r"[^a-z0-9]+", "", raw)
        # Users commonly label a gateway key with the service name rather than
        # the internal preset id. Canonicalize those labels to the same pool.
        alias_groups = {
            "freellm": {"freellm", "freellmapi", "freellmlocalgateway", "freellmapilocalgateway", "freellmgateway", "freellmopenai-compatible"},
            "nvidia": {"nvidia", "nvidianim"},
            "anthropic": {"anthropic", "anthropicclaude", "claude"},
            "gemini": {"gemini", "googlegemini", "googleai"},
            "edenai": {"edenai", "edenaiapi", "edenaiimages"},
            "aihorde": {"aihorde", "aihordeimages", "stablehorde", "stablehordeimages"},
            "kimi": {"kimi", "moonshot", "moonshotai", "kimimoonshotai"},
            "huggingface": {"huggingface", "huggingfaceinference"},
            "xai": {"xai", "grok", "xaigrok"},
            "qwen": {"qwen", "alibabadashscope", "qwenalibabadashscope"},
            "cohere": {"cohere", "coherecompatibilityapi"},
        }
        for canonical, aliases in alias_groups.items():
            if squashed in aliases:
                return canonical
        aliases = {
            "openai compatible freellm": "openai-compatible",
            "openai compatible": "openai-compatible",
            "custom openai compatible": "openai-compatible",
            "free llm api local gateway": "freellm",
            "free llm api": "freellm",
        }
        spaced = re.sub(r"[^a-z0-9]+", " ", raw).strip()
        if spaced in aliases:
            return aliases[spaced]
        return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")

    def provider_key_ids(self, provider: str, preferred_ids: list[str] | None = None) -> list[str]:
        """Return selected keys when a profile supplies an explicit list.

        Passing ``None`` is a discovery query and returns every matching key.
        Passing an empty list is an explicit choice of no keys; it must not
        silently expand into every credential saved for that provider.
        """
        keys = self.list_keys()
        available = {item["id"]: item for item in keys}
        if preferred_ids is not None:
            ordered: list[str] = []
            for key_id in preferred_ids:
                if key_id in available and key_id not in ordered:
                    ordered.append(key_id)
            return ordered
        wanted = self._provider_id(provider)
        return [item["id"] for item in keys if self._provider_id(item["provider"]) == wanted]

    def get_secret(self, key_id: str) -> str:
        with self.workspace._connect() as db:
            row = db.execute("SELECT id FROM key_metadata WHERE id=?", (key_id,)).fetchone()
        if row is None:
            raise KeyError("Saved API key not found.")
        secret = self._store().get_password(key_id)
        if secret is None:
            raise RuntimeError("The key's Windows Credential Manager entry is missing. Please add the key again.")
        return secret

    def delete_key(self, key_id: str) -> bool:
        with self.workspace._connect() as db:
            row = db.execute("SELECT id FROM key_metadata WHERE id=?", (key_id,)).fetchone()
        if row is None:
            return False
        try:
            self._store().delete_password(key_id)
        except Exception as exc:
            raise RuntimeError(f"Could not remove the secret from Windows Credential Manager: {exc}") from exc
        with self.workspace._connect() as db:
            db.execute("DELETE FROM key_metadata WHERE id=?", (key_id,))
        return True
