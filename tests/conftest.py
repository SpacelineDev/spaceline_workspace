"""Shared local Firebase identity fixture for API integration tests.

The production middleware always verifies real Firebase ID tokens. These tests
replace only the verifier/config readiness and supply a synthetic bearer token
through TestClient's default headers.
"""
from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.user_storage import UserStorageManager


class _TestFirebaseAuth:
    @staticmethod
    def verify_id_token(token, check_revoked=True):
        if not token or token == "invalid-test-token":
            raise ValueError("Invalid test token")
        return {"uid": "pytest-test-user", "email": "spaceline-tests@example.invalid"}


@pytest.fixture(autouse=True)
def _firebase_ready_for_api_tests(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "FIREBASE_WEB_CONFIGURED", True)
    monkeypatch.setattr(main, "FIREBASE_ADMIN_READY", True)
    monkeypatch.setattr(main, "firebase_auth", _TestFirebaseAuth())
    monkeypatch.setattr(main, "_user_storage", UserStorageManager(tmp_path / "isolated-test-storage"))
    monkeypatch.setattr(main, "_user_resources", {})

    original_init = TestClient.__init__

    def init_with_test_identity(self, app, *args, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        headers.setdefault("Authorization", "Bearer pytest-test-id-token")
        kwargs["headers"] = headers
        original_init(self, app, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", init_with_test_identity)
