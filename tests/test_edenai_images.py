import base64
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app.ai_provider import AIProviderClient, DEFAULT_ENDPOINTS, PROVIDER_CATALOG


class FakeResponse:
    def __init__(self, payload: bytes, headers=None):
        self.payload = payload
        self.headers = headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, size=-1): return self.payload if size < 0 else self.payload[:size]
    def getheader(self, name, default=None): return self.headers.get(name, default)
    def geturl(self): return "https://cdn.example.test/generated.png"


class EdenAIImageProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = AIProviderClient()
        self.settings = {
            "name": "Eden AI Images", "provider": "edenai",
            "base_url": "https://api.edenai.run/v3", "model": "google/gemini-3.1-flash-image",
        }

    def test_edenai_is_a_first_class_secure_provider_preset(self):
        self.assertEqual(DEFAULT_ENDPOINTS["edenai"], "https://api.edenai.run/v3")
        preset = next(row for row in PROVIDER_CATALOG if row["id"] == "edenai")
        self.assertEqual(preset["label"], "Eden AI")
        self.assertTrue(preset["key_required"])
        self.assertEqual(preset["protocol"], "openai-compatible")

    def test_list_image_models_uses_dedicated_v3_image_catalog(self):
        payload = json.dumps({"data": [
            {"id": "google/gemini-3.1-flash-image", "name": "Gemini Flash Image"},
            {"id": "openai/gpt-image-1-mini", "name": "GPT Image Mini"},
        ]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = self.client.list_image_models(self.settings, "eden-secret")
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.edenai.run/v3/images/models")
        self.assertEqual(request.get_header("Authorization"), "Bearer eden-secret")
        self.assertEqual([m["id"] for m in models], ["google/gemini-3.1-flash-image", "openai/gpt-image-1-mini"])

    def test_edenai_image_generation_uses_openai_compatible_v3_images_endpoint(self):
        png = b"eden-image-png"
        payload = json.dumps({"data": [{"b64_json": base64.b64encode(png).decode(), "url": None}],
                              "provider": "google", "cost": 0.01}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = self.client.generate_image(
                self.settings, "eden-secret", "A cinematic forest-green robot",
                model="google/gemini-3.1-flash-image", aspect_ratio="16:9", quality="high",
            )
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.edenai.run/v3/images/generations")
        self.assertEqual(request.get_header("Authorization"), "Bearer eden-secret")
        body = json.loads(request.data.decode())
        self.assertEqual(body["model"], "google/gemini-3.1-flash-image")
        self.assertEqual(body["prompt"], "A cinematic forest-green robot")
        self.assertEqual(body["n"], 1)
        self.assertEqual(body["size"], "1536x864")
        self.assertNotIn("quality", body)  # not supported by every Eden image model
        self.assertEqual(body["response_format"], "b64_json")
        self.assertEqual(result, (png, "image/png", "png"))

    def test_edenai_rejects_model_ids_without_provider_prefix(self):
        with self.assertRaisesRegex(ValueError, "provider/model"):
            self.client.generate_image(self.settings, "eden-secret", "test", model="gemini-2.5-flash-image")

    def test_edenai_requires_a_saved_api_key(self):
        from app.ai_provider import ProviderError
        with self.assertRaisesRegex(ProviderError, "saved provider API key"):
            self.client.generate_image(self.settings, None, "test", model="google/gemini-3.1-flash-image")


def test_image_studio_offers_edenai_and_loads_its_account_specific_image_catalog():
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
    main_py = (root / "app" / "main.py").read_text(encoding="utf-8")
    assert "edenai" in app_js
    assert "/api/images/models/" in app_js
    assert "data:image-model-provider" in app_js or "imageModelsByProfile" in app_js
    assert "@app.get(\"/api/images/models/{profile_id}\")" in main_py


def test_edenai_image_download_rejects_private_network_targets_before_request():
    from app.ai_provider import ProviderError
    with patch("app.ai_provider.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]), \
         patch("urllib.request.build_opener") as build_opener:
        with unittest.TestCase().assertRaisesRegex(ProviderError, "non-public"):
            AIProviderClient()._download_eden_image("https://internal.example/image.png")
    build_opener.assert_not_called()


def test_edenai_image_download_rejects_non_https_urls():
    from app.ai_provider import ProviderError
    with unittest.TestCase().assertRaisesRegex(ProviderError, "HTTPS"):
        AIProviderClient()._download_eden_image("http://cdn.example.test/image.png")
