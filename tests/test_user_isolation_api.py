from fastapi.testclient import TestClient

import app.main as main
from app.user_storage import UserStorageManager


def test_api_workspace_is_separated_by_verified_firebase_uid(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "_user_storage", UserStorageManager(tmp_path / "isolated-workspaces"))
    monkeypatch.setattr(main, "_user_resources", {})
    monkeypatch.setattr(main, "app_token", "user-isolation-test-token")

    class AuthByToken:
        @staticmethod
        def verify_id_token(token, check_revoked=True):
            if token == "account-one":
                return {"uid": "account-one"}
            if token == "account-two":
                return {"uid": "account-two"}
            raise ValueError("invalid token")

    monkeypatch.setattr(main, "firebase_auth", AuthByToken())
    with TestClient(main.app) as client:
        one = {"X-Spaceline-Token": "user-isolation-test-token", "Authorization": "Bearer account-one"}
        two = {"X-Spaceline-Token": "user-isolation-test-token", "Authorization": "Bearer account-two"}

        created = client.post("/api/projects", json={"name": "Only Account One"}, headers=one)
        assert created.status_code == 200, created.text
        visible_to_one = client.get("/api/projects", headers=one)
        visible_to_two = client.get("/api/projects", headers=two)

    assert "Only Account One" in visible_to_one.json()["projects"]
    assert "Only Account One" not in visible_to_two.json()["projects"]
