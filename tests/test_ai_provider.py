import io
import json
import unittest
from unittest.mock import patch

from app.ai_provider import AIProviderClient, ProviderError, normalize_settings, DEFAULT_ENDPOINTS


class FakeResponse:
    def __init__(self, payload: bytes, lines=None):
        self.payload = payload
        self.lines = lines
        self.stream = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()

    def read(self):
        return self.payload

    def __iter__(self):
        return iter(self.lines if self.lines is not None else self.payload.splitlines(keepends=True))

    def close(self):
        self.stream.close()


class AIProviderTests(unittest.TestCase):
    def test_openai_image_generation_posts_to_images_endpoint_and_decodes_png(self):
        import base64
        png_bytes = b"fake-png-content"
        payload = json.dumps({"data":[{"b64_json":base64.b64encode(png_bytes).decode()}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().generate_image(
                {"provider":"openai", "base_url":"https://api.openai.com/v1", "model":"gpt-6"},
                "openai-secret", "A small green robot", model="gpt-image-2.5-flare", size="1024x1024", quality="medium"
            )
        self.assertEqual(result, (png_bytes, "image/png", "png"))
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/images/generations")
        self.assertEqual(request.get_header("Authorization"), "Bearer openai-secret")
        body = json.loads(request.data.decode())
        self.assertEqual(body["model"], "gpt-image-2.5-flare")
        self.assertEqual(body["prompt"], "A small green robot")


    def test_openrouter_model_catalog_uses_user_filtered_catalog_when_available(self):
        payload = json.dumps({"data": [
            {"id": "vendor/model:free", "name": "Free model", "context_length": 16384,
             "pricing": {"prompt": "0", "completion": "0"}}
        ]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            rows = AIProviderClient().list_model_catalog({"provider":"openrouter"}, "management-key")
        self.assertEqual(open_url.call_args.args[0].full_url, "https://openrouter.ai/api/v1/models/user")
        self.assertEqual(rows[0]["catalog_scope"], "user-filtered")
        self.assertTrue(rows[0]["free_variant"])

    def test_openrouter_model_catalog_falls_back_when_user_catalog_requires_management_key(self):
        from urllib.error import HTTPError
        first = HTTPError("https://openrouter.ai/api/v1/models/user", 403, "Forbidden", {}, io.BytesIO(b""))
        payload = json.dumps({"data": [
            {"id": "vendor/model:free", "name": "Free model", "context_length": 16384,
             "pricing": {"prompt": "0", "completion": "0"}}
        ]}).encode()
        with patch("app.ai_provider.urlopen", side_effect=[first, FakeResponse(payload)]) as open_url:
            rows = AIProviderClient().list_model_catalog({"provider":"openrouter"}, "regular-key")
        self.assertEqual(open_url.call_count, 2)
        self.assertEqual(open_url.call_args_list[0].args[0].full_url, "https://openrouter.ai/api/v1/models/user")
        self.assertEqual(open_url.call_args_list[1].args[0].full_url, "https://openrouter.ai/api/v1/models")
        self.assertEqual(rows[0]["catalog_scope"], "provider-catalog")

    def test_openai_image_generation_maps_widescreen_aspect_ratio_to_valid_dimensions(self):
        import base64
        payload = json.dumps({"data":[{"b64_json":base64.b64encode(b"wide-image").decode()}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            AIProviderClient().generate_image(
                {"provider":"openai", "base_url":"https://api.openai.com/v1", "model":"gpt-6"},
                "openai-secret", "Wide cinematic landscape", model="gpt-image-2.6-flare",
                aspect_ratio="16:9", quality="high",
            )
        body = json.loads(open_url.call_args.args[0].data.decode())
        self.assertEqual(body["size"], "1536x864")
        self.assertEqual(body["quality"], "high")

    def test_gemini_pro_image_accepts_four_k_output_and_ultrawide_ratio(self):
        import base64
        image_bytes = b"gemini-pro-image"
        payload = json.dumps({"steps": [{"type": "model_output", "content": [
            {"type": "image", "data":base64.b64encode(image_bytes).decode(), "mime_type":"image/png"}
        ]}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().generate_image(
                {"provider":"gemini", "base_url":"https://generativelanguage.googleapis.com/v1beta", "model":"gemini-3-pro-image"},
                "gemini-secret", "A detailed ultrawide mountain panorama", model="gemini-3-pro-image",
                aspect_ratio="21:9", quality="max",
            )
        self.assertEqual(result, (image_bytes, "image/png", "png"))
        body = json.loads(open_url.call_args.args[0].data.decode())
        self.assertEqual(body["response_format"]["aspect_ratio"], "21:9")
        self.assertEqual(body["response_format"]["image_size"], "4K")

    def test_gemini_flash_lite_rejects_quality_above_one_k(self):
        with self.assertRaisesRegex(ValueError, "1K output only"):
            AIProviderClient().generate_image(
                {"provider":"gemini", "model":"gemini-3.1-flash-lite-image"}, "gemini-secret",
                "A simple illustration", model="gemini-3.1-flash-lite-image", quality="high",
            )

    def test_gemini_image_generation_rejects_unverified_legacy_model_ids(self):
        with self.assertRaisesRegex(ValueError, "supported Gemini image model"):
            AIProviderClient().generate_image(
                {"provider":"gemini", "model":"gemini-2.5-flash-image"}, "gemini-secret",
                "test", model="gemini-2.5-flash-image"
            )

    def test_openrouter_model_catalog_marks_true_free_variants_and_pricing(self):
        payload = json.dumps({"data": [
            {"id": "vendor/free-model:free", "name": "Free Model", "context_length": 32768,
             "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "vendor/zero-price", "name": "Zero Price", "context_length": 8192,
             "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "vendor/paid", "name": "Paid", "pricing": {"prompt": "0.000001", "completion": "0.000002"}},
        ]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            rows = AIProviderClient().list_model_catalog({"provider":"openrouter"}, "router-secret")
        by_id = {item["id"]: item for item in rows}
        self.assertTrue(by_id["vendor/free-model:free"]["free_variant"])
        self.assertEqual(by_id["vendor/free-model:free"]["pricing_status"], "free-variant")
        self.assertEqual(by_id["vendor/zero-price"]["pricing_status"], "zero-priced-may-require-credits")
        self.assertEqual(by_id["vendor/paid"]["pricing_status"], "paid")

    def test_gemini_image_generation_uses_documented_interactions_api_and_extracts_image(self):
        import base64
        png_bytes = b"gemini-image-bytes"
        payload = json.dumps({"output_image": {"mime_type": "image/png", "data": base64.b64encode(png_bytes).decode()}}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().generate_image(
                {"provider":"gemini", "model":"gemini-3.1-flash-image"}, "gemini-secret",
                "A forest-green abstract wallpaper", model="gemini-3.1-flash-image", size="1536x1024", quality="high"
            )
        self.assertEqual(result, (png_bytes, "image/png", "png"))
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://generativelanguage.googleapis.com/v1beta/interactions")
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-secret")
        body = json.loads(request.data.decode())
        self.assertEqual(body["model"], "gemini-3.1-flash-image")
        self.assertEqual(body["input"], "A forest-green abstract wallpaper")
        self.assertEqual(body["response_format"]["type"], "image")
        self.assertEqual(body["response_format"]["aspect_ratio"], "3:2")
        self.assertEqual(body["response_format"]["image_size"], "2K")

    def test_gemini_image_generation_reports_when_response_has_no_image_part(self):
        payload = json.dumps({"status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": "No image was produced."}]}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            with self.assertRaisesRegex(ProviderError, "no image data"):
                AIProviderClient().generate_image(
                    {"provider":"gemini", "model":"gemini-3.1-flash-image"}, "gemini-secret",
                    "A forest-green abstract wallpaper", model="gemini-3.1-flash-image"
                )

    def test_image_generation_rejects_unsupported_provider(self):
        with self.assertRaisesRegex(ProviderError, "OpenAI"):
            AIProviderClient().generate_image({"provider":"groq", "model":"llama"}, "key", "test")

    def test_normalizes_default_endpoints(self):
        openai = normalize_settings({"provider": "openai-compatible", "model": "gpt-test"})
        ollama = normalize_settings({"provider": "ollama", "model": "qwen2.5:7b"})
        anthropic = normalize_settings({"provider": "anthropic", "model": "claude-model"})
        gemini = normalize_settings({"provider": "gemini", "model": "gemini-model"})
        self.assertEqual(openai["base_url"], "https://api.openai.com/v1")
        self.assertEqual(ollama["base_url"], "http://127.0.0.1:11434")
        self.assertEqual(anthropic["base_url"], "https://api.anthropic.com/v1")
        self.assertEqual(gemini["base_url"], "https://generativelanguage.googleapis.com/v1beta")

    def test_vendor_presets_include_nvidia_groq_kimi_and_major_compatible_hosts(self):
        expected = {
            "openai": "https://api.openai.com/v1",
            "nvidia": "https://integrate.api.nvidia.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "deepseek": "https://api.deepseek.com",
            "kimi": "https://api.moonshot.ai/v1",
            "together": "https://api.together.ai/v1",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "cerebras": "https://api.cerebras.ai/v1",
            "mistral": "https://api.mistral.ai/v1",
            "sambanova": "https://api.sambanova.ai/v1",
            "xai": "https://api.x.ai/v1",
            "perplexity": "https://api.perplexity.ai",
            "deepinfra": "https://api.deepinfra.com/v1/openai",
            "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "huggingface": "https://router.huggingface.co/v1",
            "novita": "https://api.novita.ai/openai/v1",
            "cohere": "https://api.cohere.com/compatibility/v1",
            "freellm": "http://127.0.0.1:31415/v1",
        }
        for provider, endpoint in expected.items():
            with self.subTest(provider=provider):
                self.assertEqual(DEFAULT_ENDPOINTS[provider], endpoint)
                config = normalize_settings({"provider": provider, "model": "vendor-model"})
                self.assertEqual(config["base_url"], endpoint)

    def test_local_openai_compatible_servers_can_be_keyless(self):
        for provider in ("lmstudio", "vllm", "localai", "llamacpp"):
            with self.subTest(provider=provider):
                settings = normalize_settings({"provider": provider, "key_id": "must-be-cleared"})
                self.assertIsNone(settings["key_id"])

    def test_rejects_unknown_provider_id(self):
        with self.assertRaisesRegex(ValueError, "supported provider preset"):
            normalize_settings({"provider": "made-up-provider", "model": "x"})

    def test_groq_uses_openai_compatible_model_listing(self):
        payload = json.dumps({"data": [{"id": "llama-test"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = AIProviderClient().list_models({"provider": "groq"}, "groq-secret")
        self.assertEqual(models, ["llama-test"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/models")
        self.assertEqual(request.get_header("Authorization"), "Bearer groq-secret")

    def test_kimi_streams_through_openai_compatible_adapter(self):
        lines = [b'data: {"choices":[{"delta":{"content":"Kimi response"}}]}\n', b'data: [DONE]\n']
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider": "kimi", "model": "kimi-model"}, "kimi-secret",
                [{"role": "user", "content": "Hello"}],
            ))
        self.assertEqual(chunks, ["Kimi response"])
        self.assertEqual(open_url.call_args.args[0].full_url, "https://api.moonshot.ai/v1/chat/completions")

    def test_ollama_settings_do_not_retain_an_api_key_reference(self):
        settings = normalize_settings({
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen:7b",
            "key_id": "cloud-key-id",
        })
        self.assertIsNone(settings["key_id"])

    def test_rejects_unsafe_or_invalid_base_urls(self):
        with self.assertRaises(ValueError):
            normalize_settings({"provider": "openai-compatible", "base_url": "file:///etc/passwd", "model": "x"})
        with self.assertRaises(ValueError):
            normalize_settings({"provider": "openai-compatible", "base_url": "https://user:pass@example.com/v1", "model": "x"})

    def test_lists_openai_compatible_models(self):
        payload = json.dumps({"data": [{"id": "model-a"}, {"id": "model-b"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = AIProviderClient().list_models({"provider": "openai-compatible", "base_url": "https://example.test/v1"}, "secret-token")
        self.assertEqual(models, ["model-a", "model-b"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")

    def test_lists_ollama_models(self):
        payload = json.dumps({"models": [{"name": "qwen:7b"}, {"name": "llama:8b"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            models = AIProviderClient().list_models({"provider": "ollama", "base_url": "http://127.0.0.1:11434"}, None)
        self.assertEqual(models, ["llama:8b", "qwen:7b"])

    def test_streams_openai_sse_content_only(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":" there"}}]}\n\n',
            b'data: [DONE]\n\n',
        ]
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider": "openai-compatible", "base_url": "https://example.test/v1", "model": "model-a"},
                "secret-token",
                [{"role": "user", "content": "Say hi"}],
            ))
        self.assertEqual(chunks, ["Hello", " there"])
        request = open_url.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/chat/completions"))
        self.assertNotIn("secret-token", request.data.decode())

    def test_streams_ollama_ndjson_content(self):
        lines = [
            b'{"message":{"content":"Local"},"done":false}\n',
            b'{"message":{"content":" model"},"done":true}\n',
        ]
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider": "ollama", "base_url": "http://127.0.0.1:11434", "model": "qwen:7b"},
                None,
                [{"role": "user", "content": "Say hi"}],
            ))
        self.assertEqual(chunks, ["Local", " model"])
        self.assertTrue(open_url.call_args.args[0].full_url.endswith("/api/chat"))

    def test_provider_errors_do_not_include_credentials(self):
        from urllib.error import HTTPError
        error = HTTPError("https://example.test", 401, "Unauthorized", {}, io.BytesIO(b"secret-token leaked"))
        with patch("app.ai_provider.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                AIProviderClient().list_models({"provider": "openai-compatible", "base_url": "https://example.test/v1"}, "secret-token")
        self.assertNotIn("secret-token", str(caught.exception))
        self.assertNotIn("leaked", str(caught.exception))



    def test_401_error_explains_provider_key_and_endpoint_checks(self):
        from urllib.error import HTTPError
        error = HTTPError("https://example.test/v1/models", 401, "Unauthorized", {}, io.BytesIO(b'{"error":"bad token"}'))
        with patch("app.ai_provider.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                AIProviderClient().list_models({"provider":"groq","base_url":"https://api.groq.com/openai/v1"}, "bad-key")
        message = str(caught.exception).lower()
        self.assertIn("401", message)
        self.assertIn("provider-specific", message)
        self.assertNotIn("bad-key", message)

    def test_http_400_includes_provider_detail_but_redacts_google_api_keys(self):
        from urllib.error import HTTPError
        body = json.dumps({"error": {"message": "Unknown field response_format; key=AIzaSyBcdefghijklmnopqrstuvwxyz123456"}}).encode()
        error = HTTPError("https://example.test", 400, "Bad Request", {}, io.BytesIO(body))
        with patch("app.ai_provider.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                AIProviderClient().probe_model({"provider": "gemini", "model": "test"}, "secret")
        self.assertIn("Unknown field response_format", str(caught.exception))
        self.assertIn("[redacted API key]", str(caught.exception))
        self.assertNotIn("AIzaSyBcdefghijklmnopqrstuvwxyz123456", str(caught.exception))

    def test_openai_compatible_tool_calls_execute_and_continue_to_final_answer(self):
        first = {"choices":[{"message":{"role":"assistant","content":None,"tool_calls":[{"id":"call-1","type":"function","function":{"name":"browser_open","arguments":"{\"url\":\"https://example.com\"}"}}]},"finish_reason":"tool_calls"}]}
        second = {"choices":[{"message":{"role":"assistant","content":"I opened the page."},"finish_reason":"stop"}]}
        responses = [FakeResponse(json.dumps(first).encode()), FakeResponse(json.dumps(second).encode())]
        seen = []
        def handler(name, args):
            seen.append((name,args))
            return {"ok": True, "title": "Example"}
        with patch("app.ai_provider.urlopen", side_effect=responses):
            answer, calls = AIProviderClient().complete_with_tools(
                {"provider":"groq","base_url":"https://api.groq.com/openai/v1","model":"llama-test"},
                "secret", [{"role":"user","content":"Open example.com"}],
                [{"type":"function","function":{"name":"browser_open","description":"Open a page","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}}], handler)
        self.assertEqual(answer, "I opened the page.")
        self.assertEqual(seen[0][0], "browser_open")
        self.assertEqual(len(calls), 1)


    def test_anthropic_native_tool_calls_execute_and_continue(self):
        first = {"content":[{"type":"tool_use","id":"tool-1","name":"browser_open","input":{"url":"https://example.com"}}]}
        second = {"content":[{"type":"text","text":"Claude opened the website."}]}
        responses = [FakeResponse(json.dumps(first).encode()), FakeResponse(json.dumps(second).encode())]
        with patch("app.ai_provider.urlopen", side_effect=responses) as open_url:
            answer, activity = AIProviderClient().complete_with_tools(
                {"provider":"anthropic","model":"claude-test"}, "anthropic-secret",
                [{"role":"user","content":"Open example.com"}],
                [{"type":"function","function":{"name":"browser_open","description":"open","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}}],
                lambda name,args:{"ok":True,"summary":"Opened Example"})
        self.assertEqual(answer, "Claude opened the website.")
        self.assertEqual(activity[0]["tool"], "browser_open")
        request = open_url.call_args_list[0].args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "anthropic-secret")

    def test_gemini_native_function_calls_execute_and_continue(self):
        first = {"candidates":[{"content":{"role":"model","parts":[{"functionCall":{"name":"browser_read_page","args":{}}}]}}]}
        second = {"candidates":[{"content":{"role":"model","parts":[{"text":"Gemini inspected the page."}]}}]}
        responses = [FakeResponse(json.dumps(first).encode()), FakeResponse(json.dumps(second).encode())]
        with patch("app.ai_provider.urlopen", side_effect=responses) as open_url:
            answer, activity = AIProviderClient().complete_with_tools(
                {"provider":"gemini","model":"gemini-fast"}, "gemini-secret",
                [{"role":"user","content":"Read my browser page"}],
                [{"type":"function","function":{"name":"browser_read_page","description":"read","parameters":{"type":"object","properties":{}}}}],
                lambda name,args:{"ok":True,"summary":"Read page"})
        self.assertEqual(answer, "Gemini inspected the page.")
        self.assertEqual(activity[0]["tool"], "browser_read_page")
        request = open_url.call_args_list[0].args[0]
        self.assertIn("/models/gemini-fast:generateContent", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-secret")

    def test_streams_anthropic_message_events(self):
        lines = [
            b'event: content_block_delta\n',
            b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}\n\n',
            b'data: {"type":"message_stop"}\n\n',
        ]
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider":"anthropic","base_url":"https://api.anthropic.com/v1","model":"claude-test"},
                "anthropic-secret", [{"role":"user","content":"Say hi"}],
            ))
        self.assertEqual(chunks, ["Hello"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "anthropic-secret")
        self.assertTrue(request.full_url.endswith("/messages"))

    def test_lists_gemini_models(self):
        payload = json.dumps({"models":[{"name":"models/gemini-fast","supportedGenerationMethods":["generateContent"]},{"name":"models/embed","supportedGenerationMethods":["embedContent"]}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = AIProviderClient().list_models({"provider":"gemini","base_url":"https://generativelanguage.googleapis.com/v1beta"}, "gemini-secret")
        self.assertEqual(models, ["gemini-fast"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-goog-api-key"), "gemini-secret")

    def test_streams_gemini_sse_text(self):
        lines = [b'data: {"candidates":[{"content":{"parts":[{"text":"Gemini says hi"}]}}]}\n\n']
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider":"gemini","base_url":"https://generativelanguage.googleapis.com/v1beta","model":"gemini-fast"},
                "gemini-secret", [{"role":"user","content":"Say hi"}],
            ))
        self.assertEqual(chunks, ["Gemini says hi"])
        self.assertIn(":streamGenerateContent?", open_url.call_args.args[0].full_url)
    def test_openai_compatible_model_listing_follows_all_cursor_pages(self):
        page_one = json.dumps({"data": [{"id": "model-a"}], "has_more": True}).encode()
        page_two = json.dumps({"data": [{"id": "model-b"}], "has_more": False}).encode()
        with patch("app.ai_provider.urlopen", side_effect=[FakeResponse(page_one), FakeResponse(page_two)]) as open_url:
            models = AIProviderClient().list_models({"provider": "openai", "base_url": "https://example.test/v1"}, "secret-token")
        self.assertEqual(models, ["model-a", "model-b"])
        self.assertIn("after=model-a", open_url.call_args_list[1].args[0].full_url)

    def test_openai_compatible_model_listing_follows_explicit_next_cursor_without_has_more(self):
        page_one = json.dumps({"data": [{"id": "model-a"}], "next_cursor": "cursor-b"}).encode()
        page_two = json.dumps({"data": [{"id": "model-b"}]}).encode()
        with patch("app.ai_provider.urlopen", side_effect=[FakeResponse(page_one), FakeResponse(page_two)]) as open_url:
            models = AIProviderClient().list_models({"provider": "openai", "base_url": "https://example.test/v1"}, "secret-token")
        self.assertEqual(models, ["model-a", "model-b"])
        self.assertIn("after=cursor-b", open_url.call_args_list[1].args[0].full_url)

    def test_custom_gateway_supports_x_api_key_auth_mode(self):
        payload = json.dumps({"data": [{"id": "gateway-model"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            models = AIProviderClient().list_models({
                "provider": "freellm", "base_url": "http://127.0.0.1:31415/v1", "auth_mode": "x-api-key"
            }, "gateway-secret")
        self.assertEqual(models, ["gateway-model"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "gateway-secret")
        self.assertIsNone(request.get_header("Authorization"))

    def test_custom_gateway_can_disable_auth_header(self):
        payload = json.dumps({"data": [{"id": "public-model"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            AIProviderClient().list_models({
                "provider": "freellm", "base_url": "http://127.0.0.1:31415/v1", "auth_mode": "none"
            }, "ignored-secret")
        request = open_url.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertIsNone(request.get_header("X-api-key"))

    def test_openai_compatible_stream_uses_configured_api_key_header(self):
        lines = [b'data: {"choices":[{"delta":{"content":"ok"}}]}\n', b'data: [DONE]\n']
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(b"", lines=lines)) as open_url:
            chunks = list(AIProviderClient().stream_chat(
                {"provider": "freellm", "base_url": "http://127.0.0.1:31415/v1", "model": "m", "auth_mode": "api-key"},
                "gateway-secret", [{"role": "user", "content": "hello"}],
            ))
        self.assertEqual(chunks, ["ok"])
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Api-key"), "gateway-secret")
        self.assertIsNone(request.get_header("Authorization"))

    def test_model_catalog_supports_gateway_models_array_shape(self):
        payload = json.dumps({"models": [{"name": "model-z"}, {"name": "model-a"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            models = AIProviderClient().list_models({"provider": "freellm", "base_url": "http://127.0.0.1:31415/v1"}, "gateway-key")
        self.assertEqual(models, ["model-a", "model-z"])

    def test_anthropic_model_catalog_follows_after_id_pagination(self):
        page_one = json.dumps({"data": [{"id": "claude-a"}], "has_more": True, "last_id": "claude-a"}).encode()
        page_two = json.dumps({"data": [{"id": "claude-b"}], "has_more": False}).encode()
        with patch("app.ai_provider.urlopen", side_effect=[FakeResponse(page_one), FakeResponse(page_two)]) as open_url:
            models = AIProviderClient().list_models({"provider": "anthropic"}, "anthropic-secret")
        self.assertEqual(models, ["claude-a", "claude-b"])
        self.assertIn("after_id=claude-a", open_url.call_args_list[1].args[0].full_url)

    def test_gemini_model_catalog_follows_page_tokens(self):
        page_one = json.dumps({
            "models": [{"name": "models/gemini-a", "supportedGenerationMethods": ["generateContent"]}],
            "nextPageToken": "next-token",
        }).encode()
        page_two = json.dumps({
            "models": [{"name": "models/gemini-b", "supportedGenerationMethods": ["generateContent"]}],
        }).encode()
        with patch("app.ai_provider.urlopen", side_effect=[FakeResponse(page_one), FakeResponse(page_two)]) as open_url:
            models = AIProviderClient().list_models({"provider": "gemini"}, "gemini-secret")
        self.assertEqual(models, ["gemini-a", "gemini-b"])
        self.assertIn("pageToken=next-token", open_url.call_args_list[1].args[0].full_url)

    def test_rejects_unknown_gateway_auth_mode(self):
        with self.assertRaisesRegex(ValueError, "Choose Bearer"):
            normalize_settings({"provider": "freellm", "auth_mode": "basic"})


    def test_rejects_remote_cleartext_provider_endpoints(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            normalize_settings({"provider": "openai-compatible", "base_url": "http://api.example.com/v1", "model": "x"})

    def test_allows_loopback_http_for_local_gateways(self):
        config = normalize_settings({"provider": "freellm", "base_url": "http://127.0.0.1:31415/v1", "model": "x"})
        self.assertEqual(config["base_url"], "http://127.0.0.1:31415/v1")

    def test_catalog_marks_non_openrouter_models_as_unverified(self):
        payload = json.dumps({"data": [{"id": "gemini-4-argon"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            rows = AIProviderClient().list_model_catalog({"provider": "openai"}, "key")
        self.assertEqual(rows[0]["eligibility_status"], "unverified")
        self.assertIn("not verified", rows[0]["eligibility_label"].lower())

    def test_probe_model_sends_minimal_openai_compatible_request(self):
        payload = json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().probe_model({"provider": "openai", "model": "gpt-test"}, "secret")
        request = open_url.call_args.args[0]
        body = json.loads(request.data.decode())
        self.assertTrue(result["ok"])
        self.assertEqual(body["max_tokens"], 1)
        self.assertFalse(body["stream"])
        self.assertEqual(body["model"], "gpt-test")
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")

    def test_probe_model_uses_gemini_native_generate_content_endpoint(self):
        payload = json.dumps({"candidates": [{"content": {"parts": [{"text": "O"}]}}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            AIProviderClient().probe_model({"provider": "gemini", "model": "gemini-4-argon"}, "gemini-secret")
        request = open_url.call_args.args[0]
        body = json.loads(request.data.decode())
        self.assertTrue(request.full_url.endswith("/models/gemini-4-argon:generateContent"))
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 1)

    def test_http_403_explains_model_tier_access(self):
        from urllib.error import HTTPError
        error = HTTPError("https://example.test", 403, "Forbidden", {}, io.BytesIO(b'{"error":{"message":"model not enabled for this account"}}'))
        with patch("app.ai_provider.urlopen", side_effect=error):
            with self.assertRaises(ProviderError) as caught:
                AIProviderClient().probe_model({"provider": "openai", "model": "premium-model"}, "secret")
        self.assertIn("does not have access", str(caught.exception).lower())

    def test_probe_model_rejects_empty_choices_without_error_field(self):
        payload = json.dumps({"choices": []}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            with self.assertRaisesRegex(ProviderError, "valid generation response"):
                AIProviderClient().probe_model({"provider": "openai", "model": "gpt-test"}, "secret")

    def test_probe_model_requires_a_key_for_cloud_provider(self):
        with self.assertRaisesRegex(ProviderError, "API key"):
            AIProviderClient().probe_model({"provider": "gemini", "model": "gemini-test"}, None)

    def test_probe_model_rejects_unsafe_model_ids(self):
        for model in ("", "model\nX-Injected", "../secret", "model?key=secret"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                AIProviderClient().probe_model({"provider": "openai", "model": model}, "secret")

    def test_http_402_and_429_have_specific_guidance(self):
        from urllib.error import HTTPError
        for status, expected in ((402, "billing"), (429, "quota")):
            with self.subTest(status=status):
                error = HTTPError("https://example.test", status, "Provider error", {}, io.BytesIO(b"{}"))
                with patch("app.ai_provider.urlopen", side_effect=error):
                    with self.assertRaises(ProviderError) as caught:
                        AIProviderClient().probe_model({"provider": "openai", "model": "m"}, "secret")
                self.assertIn(expected, str(caught.exception).lower())


if __name__ == "__main__":
    unittest.main()


class ModelTierAndProtocolProbeTests(unittest.TestCase):
    def test_gemini_4_argon_catalog_identifies_paid_api_tier_requirement(self):
        payload = json.dumps({"models": [{"name": "models/gemini-4-argon", "supportedGenerationMethods": ["generateContent"]}]}).encode()
        # Gemini's model discovery uses the native models envelope.
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)):
            rows = AIProviderClient().list_model_catalog({"provider": "gemini"}, "key")
        row = next(item for item in rows if item["id"] == "gemini-4-argon")
        self.assertEqual(row["pricing_status"], "paid")
        self.assertIn("paid gemini api tier", row["pricing_label"].lower())
        self.assertEqual(row["eligibility_status"], "paid-tier-required")
        self.assertIn("Test access", row["eligibility_label"])

    def test_anthropic_model_probe_uses_messages_api_and_native_key_header(self):
        payload = json.dumps({"content": [{"type": "text", "text": "OK"}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().probe_model({"provider": "anthropic", "model": "claude-test"}, "anthropic-secret")
        request = open_url.call_args.args[0]
        body = json.loads(request.data.decode())
        self.assertTrue(result["ok"])
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("X-api-key"), "anthropic-secret")
        self.assertEqual(body["model"], "claude-test")

    def test_ollama_model_probe_uses_local_chat_api_without_api_key(self):
        payload = json.dumps({"message": {"role": "assistant", "content": "OK"}, "done": True}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().probe_model({"provider": "ollama", "model": "qwen-test"}, None)
        request = open_url.call_args.args[0]
        body = json.loads(request.data.decode())
        self.assertTrue(result["ok"])
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(body["model"], "qwen-test")

class OpenAIProbeCompatibilityRegressionTests(unittest.TestCase):
    def test_probe_retries_with_max_completion_tokens_when_max_tokens_is_unsupported(self):
        from urllib.error import HTTPError
        unsupported = HTTPError(
            "https://api.openai.com/v1/chat/completions", 400, "Bad Request", {},
            io.BytesIO(b'{"error":{"code":"unsupported_parameter","message":"Unsupported parameter: max_tokens. Use max_completion_tokens instead."}}'),
        )
        success = FakeResponse(json.dumps({"choices":[{"message":{"content":"O"}}]}).encode())
        with patch("app.ai_provider.urlopen", side_effect=[unsupported, success]) as open_url:
            result = AIProviderClient().probe_model({"provider":"openai", "model":"gpt-new-reasoning"}, "secret")
        self.assertTrue(result["ok"])
        self.assertEqual(open_url.call_count, 2)
        first = json.loads(open_url.call_args_list[0].args[0].data.decode())
        second = json.loads(open_url.call_args_list[1].args[0].data.decode())
        self.assertEqual(first.get("max_tokens"), 1)
        self.assertNotIn("max_tokens", second)
        self.assertEqual(second.get("max_completion_tokens"), 1)

    def test_probe_does_not_retry_non_parameter_model_access_errors(self):
        from urllib.error import HTTPError
        denied = HTTPError(
            "https://api.openai.com/v1/chat/completions", 403, "Forbidden", {},
            io.BytesIO(b'{"error":{"code":"model_not_allowed","message":"Model not enabled for this account"}}'),
        )
        with patch("app.ai_provider.urlopen", side_effect=denied) as open_url:
            with self.assertRaises(ProviderError):
                AIProviderClient().probe_model({"provider":"openai", "model":"premium-model"}, "secret")
        self.assertEqual(open_url.call_count, 1)

class KeylessCompatibleProbeRegressionTests(unittest.TestCase):
    def test_probe_allows_keyless_openai_compatible_gateway_when_auth_is_none(self):
        payload = json.dumps({"choices":[{"message":{"content":"O"}}]}).encode()
        with patch("app.ai_provider.urlopen", return_value=FakeResponse(payload)) as open_url:
            result = AIProviderClient().probe_model(
                {"provider":"openai-compatible", "base_url":"https://gateway.example.test/v1",
                 "auth_mode":"none", "model":"local-chat-model"}, None
            )
        self.assertTrue(result["ok"])
        request = open_url.call_args.args[0]
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(request.full_url, "https://gateway.example.test/v1/chat/completions")
