import json
import unittest
from unittest.mock import patch
from urllib.request import Request

from app.ai_provider import AIProviderClient, DEFAULT_ENDPOINTS, PROVIDER_CATALOG, ProviderError, normalize_settings


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, size=-1): return self.payload if size < 0 else self.payload[:size]
    def getheader(self, name, default=None): return self.headers.get(name, default)
    def geturl(self): return "https://cdn.example.test/generated.png"


class AIHordeImageProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = AIProviderClient(timeout=2)
        self.settings = {
            "name": "AI Horde Free Images", "provider": "aihorde",
            "base_url": "https://aihorde.net/api", "model": "stable_diffusion",
        }

    def test_ai_horde_is_a_first_class_provider_preset(self):
        self.assertEqual(DEFAULT_ENDPOINTS["aihorde"], "https://aihorde.net/api")
        preset = next(row for row in PROVIDER_CATALOG if row["id"] == "aihorde")
        self.assertEqual(preset["label"], "AI Horde (Free Community Images)")
        self.assertFalse(preset["key_required"])
        self.assertEqual(preset["protocol"], "aihorde")

    def test_lists_current_active_image_models(self):
        payload = json.dumps([
            {"name": "stable_diffusion", "count": 12, "queued": 2},
            {"name": "Deliberate", "count": 4, "queued": 0},
        ]).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = self.client.list_image_models(self.settings, "0000000000")
        req = open_url.call_args.args[0]
        self.assertEqual(req.full_url, "https://aihorde.net/api/v2/status/models")
        self.assertEqual(req.get_header("Apikey"), "0000000000")
        self.assertEqual([row["id"] for row in models], ["Deliberate", "stable_diffusion"])

    def test_generation_submits_async_job_polls_and_downloads_result(self):
        accepted = {"id": "job-123", "message": "Request submitted"}
        check = {"done": True, "faulted": False, "queue_position": 0}
        status = {"generations": [{"img": "https://cdn.example.test/generated.png", "seed": 42}]}
        responses = [accepted, check, status]
        image = b"fake-png-bytes"
        with patch.object(self.client, "_request_json", side_effect=responses) as request_json, \
             patch.object(self.client, "_download_provider_image", return_value=(image, "image/png")) as download, \
             patch("app.ai_provider.time.sleep"):
            result = self.client.generate_image(
                self.settings, "registered-free-key", "A friendly robot in a garden",
                model="stable_diffusion", aspect_ratio="16:9", quality="high",
            )
        submit = request_json.call_args_list[0].args[0]
        self.assertEqual(submit.full_url, "https://aihorde.net/api/v2/generate/async")
        self.assertEqual(submit.get_header("Apikey"), "registered-free-key")
        self.assertEqual(submit.get_header("Client-agent"), "Spaceline:0.9.6:personal-client")
        body = json.loads(submit.data.decode())
        self.assertEqual(body["prompt"], "A friendly robot in a garden")
        self.assertEqual(body["models"], ["stable_diffusion"])
        self.assertEqual(body["params"]["n"], 1)
        self.assertEqual((body["params"]["width"], body["params"]["height"]), (896, 512))
        self.assertFalse(body["nsfw"])
        self.assertEqual(result, (image, "image/png", "png"))
        self.assertEqual(request_json.call_count, 3)
        download.assert_called_once_with("https://cdn.example.test/generated.png", provider_name="AI Horde")

    def test_anonymous_access_uses_public_anonymous_api_key_when_no_saved_key(self):
        accepted = {"id": "job-anon"}
        with patch.object(self.client, "_request_json", side_effect=[accepted, {"done": True}, {"generations": []}]) as request_json:
            with self.assertRaisesRegex(ProviderError, "returned no image"):
                self.client.generate_image(self.settings, None, "test", model="stable_diffusion")
        submit = request_json.call_args.args[0]
        self.assertEqual(submit.get_header("Apikey"), "0000000000")

    def test_ai_horde_endpoint_is_pinned_to_official_hosts(self):
        with self.assertRaisesRegex(ValueError, "official AI Horde"):
            normalize_settings({"name": "Untrusted Horde", "provider": "aihorde",
                                "base_url": "https://attacker.example/api"})
        normalized = normalize_settings({"name": "AI Horde", "provider": "aihorde",
                                         "base_url": "https://aihorde.net/api"})
        self.assertEqual(normalized["base_url"], "https://aihorde.net/api")

    def test_anonymous_model_catalog_discovery_uses_public_key(self):
        payload = json.dumps([{"name": "Deliberate", "count": 2}]).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = self.client.list_image_models(self.settings, None)
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Apikey"), "0000000000")
        self.assertEqual(models[0]["id"], "Deliberate")

    def test_generation_refuses_unsafe_download_targets(self):
        with patch("app.ai_provider.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]), \
             patch("urllib.request.build_opener") as build_opener:
            with self.assertRaisesRegex(ProviderError, "non-public"):
                self.client._download_provider_image("https://internal.example/image.png", provider_name="AI Horde")
        build_opener.assert_not_called()

    def test_ai_horde_profile_is_image_only_and_rejects_chat_probe(self):
        from app.ai_provider import ProviderError
        with self.assertRaisesRegex(ProviderError, "image-only"):
            self.client.probe_model(self.settings, "0000000000")

    def test_ai_horde_profile_does_not_require_a_saved_key_but_can_use_one(self):
        from app import main
        anonymous_profile = {"id": "horde-profile", "provider": "aihorde", "key_id": None}
        with patch.object(main.workspace, "get_profile_key_ids", return_value=[]):
            self.assertFalse(main.profile_requires_key(anonymous_profile))
        registered_profile = {"id": "horde-profile", "provider": "aihorde", "key_id": "saved-key"}
        with patch.object(main.workspace, "get_profile_key_ids", return_value=["saved-key"]):
            self.assertTrue(main.profile_requires_key(registered_profile))

    def test_model_discovery_route_allows_anonymous_access(self):
        from app import main
        profile = {"id": "horde-profile", "provider": "aihorde", "base_url": "https://aihorde.net/api",
                   "name": "AI Horde", "enabled": 1, "model": ""}
        with patch.object(main, "require_local_token"), \
             patch.object(main.workspace, "get_profile", return_value=profile), \
             patch.object(main, "profile_key_candidates", return_value=[(None, None)]), \
             patch.object(main.ai_client, "list_image_models", return_value=[{"id": "Deliberate", "name": "Deliberate · 2 worker(s)"}]):
            result = main.list_image_models("horde-profile", "local-token")
        self.assertEqual(result["provider"], "aihorde")
        self.assertEqual(result["count"], 1)

    def test_generate_image_route_allows_anonymous_access(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from app import main
        from app.main import ImageGenerationBody
        profile = {"id": "horde-profile", "provider": "aihorde", "base_url": "https://aihorde.net/api",
                   "name": "AI Horde", "enabled": 1, "model": ""}
        with TemporaryDirectory() as temp_dir, \
             patch.object(main, "require_local_token"), \
             patch.object(main.workspace, "get_profile", return_value=profile), \
             patch.object(main.workspace, "root", Path(temp_dir)), \
             patch.object(main, "profile_key_candidates", return_value=[(None, None)]), \
             patch.object(main.ai_client, "generate_image", return_value=(b"fake-png", "image/png", "png")):
            result = main.generate_image(ImageGenerationBody(profile_id="horde-profile", prompt="test image", model="Deliberate"), "local-token")
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "aihorde")


if __name__ == "__main__":
    unittest.main()
