from __future__ import annotations

import base64
import json
import re
import ipaddress
import socket
import time
from typing import Any, Iterable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

# Named provider presets. Most hosted providers expose OpenAI Chat Completions;
# Anthropic, Gemini, and Ollama keep their native wire protocols.
DEFAULT_ENDPOINTS = {
    "openai-compatible": "https://api.openai.com/v1",  # Legacy generic/FreeLLM profile id.
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
    "ollama": "http://127.0.0.1:11434",
    "lmstudio": "http://127.0.0.1:1234/v1",
    "vllm": "http://127.0.0.1:8000/v1",
    "localai": "http://127.0.0.1:8080/v1",
    "llamacpp": "http://127.0.0.1:8080/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    # Eden AI V3 exposes OpenAI-compatible chat and dedicated image endpoints.
    "edenai": "https://api.edenai.run/v3",
    # AI Horde is a volunteer-compute image generation service.
    "aihorde": "https://aihorde.net/api",
}

PROVIDER_PROTOCOLS = {
    "ollama": "ollama",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "aihorde": "aihorde",
}

KEY_OPTIONAL_PROVIDERS = {"ollama", "lmstudio", "vllm", "localai", "llamacpp", "aihorde"}

PROVIDER_LABELS = {
    "openai-compatible": "Custom OpenAI-compatible / FreeLLM",
    "openai": "OpenAI",
    "nvidia": "NVIDIA NIM",
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "deepseek": "DeepSeek",
    "kimi": "Kimi (Moonshot AI)",
    "together": "Together AI",
    "fireworks": "Fireworks AI",
    "cerebras": "Cerebras",
    "mistral": "Mistral AI",
    "sambanova": "SambaNova",
    "xai": "xAI (Grok)",
    "perplexity": "Perplexity",
    "deepinfra": "DeepInfra",
    "qwen": "Qwen / Alibaba DashScope",
    "huggingface": "Hugging Face Inference",
    "novita": "Novita AI",
    "cohere": "Cohere",
    "freellm": "FreeLLM API (local gateway)",
    "ollama": "Ollama (local)",
    "lmstudio": "LM Studio (local)",
    "vllm": "vLLM (local)",
    "localai": "LocalAI (local)",
    "llamacpp": "llama.cpp server (local)",
    "anthropic": "Anthropic Claude",
    "gemini": "Google Gemini",
    "edenai": "Eden AI",
    "aihorde": "AI Horde (Free Community Images)",
}


def provider_protocol(provider: str) -> str:
    return PROVIDER_PROTOCOLS.get(provider, "openai-compatible")


def provider_requires_key(provider: str) -> bool:
    return provider not in KEY_OPTIONAL_PROVIDERS


PROVIDER_CATALOG = [
    {"id": provider_id, "label": label, "default_base_url": DEFAULT_ENDPOINTS[provider_id],
     "protocol": provider_protocol(provider_id),
     "key_required": provider_id not in KEY_OPTIONAL_PROVIDERS,
     "category": ("local" if provider_id in {"ollama", "lmstudio", "vllm", "localai", "llamacpp", "freellm"}
                  else "custom" if provider_id == "openai-compatible" else "cloud")}
    for provider_id, label in PROVIDER_LABELS.items()
]



class ProviderError(RuntimeError):
    """Safe-to-display provider failure; never includes request headers or secrets."""

    def __init__(self, message: str, status_code: int | None = None, retry_hint: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        # Internal compatibility hint. Never includes the provider response body.
        self.retry_hint = retry_hint


def normalize_settings(values: dict[str, Any]) -> dict[str, Any]:
    provider = str(values.get("provider") or "openai-compatible").strip().lower()
    if provider not in DEFAULT_ENDPOINTS:
        raise ValueError("Choose a supported provider preset or use Custom OpenAI-compatible.")
    base_url = str(values.get("base_url") or DEFAULT_ENDPOINTS[provider]).strip().rstrip("/")
    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Endpoint must be a valid HTTP or HTTPS URL.")
    hostname = parts.hostname.rstrip(".").lower()
    if provider == "aihorde":
        # The AI Horde provider sends a service API key, even in registered mode.
        # Pin requests to the official HTTPS API hosts to prevent credential exfiltration.
        official_hosts = {"aihorde.net", "stablehorde.net"}
        if (parts.scheme != "https" or hostname not in official_hosts
                or parts.path.rstrip("/") not in {"", "/api"}
                or parts.port not in {None, 443}):
            raise ValueError("AI Horde connections must use the official AI Horde HTTPS API endpoint (https://aihorde.net/api).")
        base_url = f"https://{hostname}/api"
        parts = urlsplit(base_url)
    is_loopback = hostname == "localhost" or hostname.endswith(".localhost")
    try:
        is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        pass
    if parts.scheme == "http" and not is_loopback:
        raise ValueError("Use HTTPS for remote provider endpoints. Plain HTTP is only allowed for localhost/loopback services such as Ollama or a local gateway.")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Endpoint cannot contain credentials, query parameters or fragments.")
    try:
        _ = parts.port
    except ValueError:
        raise ValueError("Endpoint contains an invalid port number.") from None
    if len(base_url) > 500:
        raise ValueError("Endpoint URL is too long.")
    name = str(values.get("name") or "Provider").strip()
    if not name or len(name) > 80:
        raise ValueError("Give this provider connection a name (maximum 80 characters).")
    model = str(values.get("model") or "").strip()
    if len(model) > 200:
        raise ValueError("Model name must be 200 characters or fewer.")
    key_id = values.get("key_id") or None
    if key_id is not None:
        key_id = str(key_id).strip()
        if not key_id or len(key_id) > 64:
            raise ValueError("Choose a valid saved API key.")
    if not provider_requires_key(provider):
        key_id = None
    auth_mode = str(values.get("auth_mode") or "bearer").strip().lower()
    if auth_mode not in {"bearer", "x-api-key", "api-key", "none"}:
        raise ValueError("Choose Bearer, X-API-Key, API-Key, or No authentication.")
    # Native provider protocols own their authentication headers.
    if provider_protocol(provider) != "openai-compatible":
        auth_mode = "bearer"
    return {"name": name, "provider": provider, "base_url": base_url, "model": model,
            "key_id": key_id, "auth_mode": auth_mode}


def _safe_http_error(exc: HTTPError) -> ProviderError:
    # Inspect only broad error categories. Never echo upstream bodies, request IDs,
    # headers or provider messages because some gateways include sensitive data.
    try:
        raw = exc.read(12_000)
        payload = json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
    except Exception:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if isinstance(error, dict):
        signals = " ".join(str(error.get(key, "")) for key in ("code", "type", "status", "message")).lower()
    else:
        signals = str(error).lower()
    if exc.code == 401:
        message = ("Authentication failed (HTTP 401). The provider did not accept this key. Check that it is a provider-specific active key, "
                   "that the endpoint belongs to the same provider, and that the key has no extra spaces. For local gateways, use the gateway's own key. "
                   "Spaceline can retry other saved keys in this provider's key pool.")
    elif exc.code == 402:
        message = "Payment or billing is required for this request (HTTP 402). Check the provider's API billing, credits and plan."
    elif exc.code == 403:
        if any(word in signals for word in ("model", "tier", "entitlement", "permission", "not enabled", "access")):
            message = "This key/account does not have access to this model (HTTP 403). It may require a paid API tier, model approval, a different project/region, or an account setting. A consumer-app subscription does not automatically grant API access."
        else:
            message = "The provider denied this request (HTTP 403). Check API permissions, project/organization, model access and billing status."
    elif exc.code == 404:
        message = "The endpoint or model was not found (HTTP 404). The model may be unavailable to this API, retired, or the base URL may be incorrect. Do not add /chat/completions to the base URL."
    elif exc.code == 408:
        message = "Provider timed out (HTTP 408). Try again or choose another model/provider."
    elif exc.code == 503:
        message = "The provider is temporarily unavailable (HTTP 503). This is not proof that your key or model is invalid; retry later or use another provider."
    elif exc.code == 429:
        message = "Provider rate, quota or credit limit reached (HTTP 429). Check your usage limits and billing, wait for reset, or switch account/provider."
    elif exc.code == 400 and "max_tokens" in signals and any(
            word in signals for word in ("unsupported", "unrecognized", "unknown parameter", "not supported")):
        message = "This model endpoint does not accept the legacy token-limit field; Spaceline will retry with the compatible token-limit field."
        return ProviderError(message, exc.code, retry_hint="max_completion_tokens")
    elif exc.code == 400:
        raw_message = error.get("message", "") if isinstance(error, dict) else ""
        detail = " ".join(str(raw_message).split())[:360]
        detail = re.sub(r"\bAIza[0-9A-Za-z_-]{20,}\b", "[redacted API key]", detail)
        detail = re.sub(
            r"(?i)(authorization|x-goog-api-key|api[_ -]?key)(\s*[:=]\s*)[^\s,;]+",
            r"\1\2[redacted]", detail,
        )
        message = (
            f"Provider rejected the image/request payload (HTTP 400): {detail}"
            if detail else
            "Provider rejected the image/request payload (HTTP 400). Check the model ID and request parameters."
        )
    else:
        message = f"Provider returned HTTP {exc.code}. Check the endpoint, model, account access and API key."
    return ProviderError(message, exc.code)


def _safe_network_error(exc: Exception) -> ProviderError:
    if isinstance(exc, TimeoutError):
        return ProviderError("Provider request timed out. Check that the endpoint is reachable.")
    return ProviderError("Could not reach the AI provider. Check the endpoint and your network connection.")


class AIProviderClient:
    """Streaming adapters for OpenAI-compatible gateways, Ollama, Anthropic and Gemini."""

    def __init__(self, timeout: int = 90):
        self.timeout = timeout

    @staticmethod
    def _headers(api_key: str | None, accept: str = "application/json", auth_mode: str = "bearer") -> dict[str, str]:
        headers = {"Accept": accept, "Content-Type": "application/json", "User-Agent": "Spaceline/0.9.6"}
        if api_key and auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif api_key and auth_mode == "x-api-key":
            headers["X-API-Key"] = api_key
        elif api_key and auth_mode == "api-key":
            headers["api-key"] = api_key
        return headers

    @staticmethod
    def _with_query(url: str, **params: str | int | None) -> str:
        query = {key: value for key, value in params.items() if value is not None and value != ""}
        return f"{url}?{urlencode(query)}" if query else url

    def _request_json_any(self, request: Request, timeout: int | None = None) -> Any:
        try:
            with urlopen(request, timeout=timeout or self.timeout) as response:
                payload = response.read()
            return json.loads(payload.decode("utf-8"))
        except HTTPError as exc:
            raise _safe_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise _safe_network_error(exc) from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderError("Provider returned an invalid JSON response.") from None

    def _request_json(self, request: Request, timeout: int | None = None) -> dict[str, Any]:
        data = self._request_json_any(request, timeout=timeout)
        if not isinstance(data, dict):
            raise ProviderError("Provider returned an unexpected response format.")
        return data

    def list_models(self, settings: dict[str, Any], api_key: str | None = None) -> list[str]:
        """Fetch the complete model catalogue exposed by the selected provider/gateway.

        Model APIs differ: OpenAI-compatible and Anthropic APIs use cursor pagination,
        Gemini uses pageToken, and Ollama returns its local installed model list.
        Pagination is bounded to avoid a misbehaving gateway causing an infinite loop.
        """
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        provider = config["provider"]
        base = config["base_url"]
        protocol = provider_protocol(provider)
        names: list[str] = []
        seen_cursors: set[str] = set()
        if provider == "aihorde":
            return [item["id"] for item in self.list_image_models(config, api_key)]
        if protocol == "ollama":
            request = Request(f"{base}/api/tags", headers=self._headers(None), method="GET")
            payload = self._request_json(request)
            items = payload.get("models", [])
            if isinstance(items, list):
                names.extend(item.get("name") for item in items if isinstance(item, dict))
        elif protocol == "anthropic":
            headers = self._headers(None)
            headers.update({"x-api-key": api_key or "", "anthropic-version": "2023-06-01"})
            cursor = None
            for _ in range(50):
                request = Request(self._with_query(f"{base}/models", limit=100, after_id=cursor), headers=headers, method="GET")
                payload = self._request_json(request)
                items = payload.get("data", [])
                if isinstance(items, list):
                    names.extend(item.get("id") for item in items if isinstance(item, dict))
                next_cursor = payload.get("last_id") or (items[-1].get("id") if isinstance(items, list) and items and payload.get("has_more") else None)
                if not payload.get("has_more") or not next_cursor or str(next_cursor) in seen_cursors:
                    break
                cursor = str(next_cursor)
                seen_cursors.add(cursor)
        elif protocol == "gemini":
            headers = self._headers(None)
            headers["x-goog-api-key"] = api_key or ""
            page_token = None
            for _ in range(50):
                request = Request(self._with_query(f"{base}/models", pageSize=1000, pageToken=page_token), headers=headers, method="GET")
                payload = self._request_json(request)
                items = payload.get("models", [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            supported = item.get("supportedGenerationMethods", [])
                            name = item.get("name")
                            if isinstance(name, str) and (not supported or "generateContent" in supported):
                                names.append(name.removeprefix("models/"))
                next_token = payload.get("nextPageToken")
                if not next_token or str(next_token) in seen_cursors:
                    break
                page_token = str(next_token)
                seen_cursors.add(page_token)
        else:
            cursor = None
            headers = self._headers(api_key, auth_mode=config.get("auth_mode", "bearer"))
            for _ in range(50):
                request = Request(self._with_query(f"{base}/models", after=cursor), headers=headers, method="GET")
                payload = self._request_json(request)
                items = payload.get("data")
                if not isinstance(items, list) or not items:
                    alternate_items = payload.get("models", [])
                    if isinstance(alternate_items, list) and alternate_items:
                        items = alternate_items
                if isinstance(items, list):
                    names.extend((item.get("id") or item.get("name") or item.get("model"))
                                 if isinstance(item, dict) else item for item in items)
                # OpenAI-compatible model lists are usually unpaginated. Only
                # continue when the server explicitly signals another page; using
                # the last model ID unconditionally would issue bogus cursor
                # requests to providers such as Groq that return a plain data list.
                has_more_flag = payload.get("has_more", payload.get("hasMore"))
                next_cursor = (payload.get("next_cursor") or payload.get("next_page_token")
                               or payload.get("nextPageToken") or payload.get("last_id"))
                # A provider may return an explicit next cursor without a separate
                # has_more flag. Honor that, but an explicit false flag wins.
                has_more = (bool(next_cursor) if has_more_flag is None else bool(has_more_flag))
                if has_more and not next_cursor and isinstance(items, list) and items:
                    last_item = items[-1]
                    next_cursor = (last_item.get("id") or last_item.get("name")) if isinstance(last_item, dict) else None
                if not has_more or not next_cursor or str(next_cursor) in seen_cursors:
                    break
                cursor = str(next_cursor)
                seen_cursors.add(cursor)
        return sorted({str(name) for name in names if isinstance(name, str) and name.strip()}, key=str.casefold)

    def list_image_models(self, settings: dict[str, Any], api_key: str | None = None) -> list[dict[str, str]]:
        """List image models available from Eden AI or currently active on AI Horde."""
        config = normalize_settings({**settings, "name": settings.get("name", "Image Models")})
        if config["provider"] == "aihorde":
            request = Request(
                f"{config['base_url']}/v2/status/models",
                headers={"Accept": "application/json", "apikey": api_key or "0000000000",
                         "Client-Agent": "Spaceline:0.9.6:personal-client"},
                method="GET",
            )
            payload = self._request_json_any(request)
            if isinstance(payload, dict):
                items = payload.get("models") or payload.get("data") or []
            else:
                items = payload
            rows: dict[str, dict[str, str]] = {}
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict):
                    continue
                model_id = str(item.get("name") or item.get("id") or "").strip()
                if not model_id or len(model_id) > 160 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._()+:/-]{0,159}", model_id):
                    continue
                try:
                    workers = int(item.get("count", item.get("workers", 1)) or 0)
                except (TypeError, ValueError):
                    workers = 0
                # Only list models currently advertised as active by the Horde.
                if workers <= 0:
                    continue
                rows[model_id] = {"id": model_id, "name": f"{model_id} · {workers} worker(s)"}
            if not rows:
                raise ProviderError("AI Horde is reachable, but no image models currently report online workers. Refresh later or check the Horde status page.")
            return sorted(rows.values(), key=lambda row: row["id"].casefold())

        host = (urlsplit(config["base_url"]).hostname or "").lower()
        if config["provider"] != "edenai" and host != "api.edenai.run":
            raise ValueError("Image model discovery is only available for Eden AI or AI Horde connections.")
        if not api_key:
            raise ProviderError("Eden AI image model discovery needs a saved API key.")
        request = Request(
            f"{config['base_url']}/images/models",
            headers=self._headers(api_key), method="GET",
        )
        payload = self._request_json(request)
        if isinstance(payload, list):
            items = payload
        else:
            items = payload.get("data")
            if not isinstance(items, list):
                items = payload.get("models")
            if not isinstance(items, list):
                items = payload.get("items", [])
        rows: dict[str, dict[str, str]] = {}
        for item in items if isinstance(items, list) else []:
            if isinstance(item, str):
                model_id, label = item.strip(), item.strip()
            elif isinstance(item, dict):
                model_id = str(item.get("id") or item.get("model") or item.get("name") or "").strip()
                label = str(item.get("name") or item.get("label") or model_id).strip()
            else:
                continue
            # Eden model identifiers are explicit provider/model pairs. Do not
            # invent a provider or silently rewrite IDs returned by the catalog.
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.:/+-]+", model_id):
                continue
            rows[model_id] = {"id": model_id, "name": label[:160] or model_id}
        return sorted(rows.values(), key=lambda row: row["id"].casefold())

    def list_model_catalog(self, settings: dict[str, Any], api_key: str | None = None) -> list[dict[str, Any]]:
        """Return models visible through this connection, with pricing only when the provider reports it."""
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        if config["provider"] != "openrouter":
            catalog = []
            for model in self.list_models(config, api_key):
                row = {"id": model, "name": model, "context_length": None, "pricing_status": "unknown",
                       "pricing_label": "Pricing not exposed by provider", "free_variant": False,
                       "eligibility_status": "unverified",
                       "eligibility_label": "Listed by provider · access not verified until tested"}
                # Google documents Gemini 4 Argon as unavailable on the free Gemini API tier.
                # This is a plan-level warning, not a successful account-access check.
                if config["provider"] == "gemini" and model.lower().startswith("gemini-4-argon"):
                    row.update({
                        "pricing_status": "paid",
                        "pricing_label": "Paid Gemini API tier only · API billing required; confirm current rates in Google AI Studio",
                        "eligibility_status": "paid-tier-required",
                        "eligibility_label": "Not available on the free Gemini API tier. Enable API billing, then run Test access for this key/project.",
                    })
                catalog.append(row)
            return catalog

        catalog_scope = "provider-catalog"
        if api_key:
            # OpenRouter's account-preference catalogue is more specific than the
            # public catalogue, but its documentation requires a management key.
            # Ordinary inference keys commonly receive 403, so fall back without
            # pretending that a public model listing proves account access/quota.
            user_request = Request(f"{config['base_url']}/models/user", headers=self._headers(api_key), method="GET")
            try:
                payload = self._request_json(user_request)
                catalog_scope = "user-filtered"
            except ProviderError as exc:
                if exc.status_code not in {403, 404}:
                    raise
                request = Request(f"{config['base_url']}/models", headers=self._headers(api_key), method="GET")
                payload = self._request_json(request)
        else:
            request = Request(f"{config['base_url']}/models", headers=self._headers(None), method="GET")
            payload = self._request_json(request)
        items = payload.get("data", [])
        catalog: list[dict[str, Any]] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
            try:
                prompt_price = float(pricing.get("prompt")) if pricing.get("prompt") is not None else None
                completion_price = float(pricing.get("completion")) if pricing.get("completion") is not None else None
            except (TypeError, ValueError):
                prompt_price, completion_price = None, None
            free_variant = item["id"].lower().endswith(":free")
            zero_priced = prompt_price == 0 and completion_price == 0
            if free_variant:
                pricing_status = "free-variant"
                pricing_label = "Free variant · usage limited"
            elif zero_priced:
                pricing_status = "zero-priced-may-require-credits"
                pricing_label = "$0 model price · account credits may still be required"
            elif prompt_price is not None and completion_price is not None:
                pricing_status = "paid"
                pricing_label = f"${prompt_price * 1_000_000:g}/M input · ${completion_price * 1_000_000:g}/M output"
            else:
                pricing_status = "unknown"
                pricing_label = "Pricing not reported"
            catalog.append({
                "id": item["id"], "name": str(item.get("name") or item["id"]),
                "context_length": item.get("context_length") if isinstance(item.get("context_length"), int) else None,
                "pricing_status": pricing_status, "pricing_label": pricing_label,
                "free_variant": free_variant,
                "eligibility_status": "unverified",
                "eligibility_label": "Catalog listing is not proof of account access; run Test access",
                "catalog_scope": catalog_scope,
            })
        return catalog

    def probe_model(self, settings: dict[str, Any], api_key: str | None = None) -> dict[str, Any]:
        """Send one tiny, non-streaming generation request to verify actual model access.

        This can incur a minimal provider charge. It is deliberately opt-in in the UI.
        A successful HTTP response confirms this key/endpoint can invoke the model now;
        it does not promise future quota, latency or account availability.
        """
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        model = config["model"].strip()
        # Provider model IDs may contain namespaces (vendor/model) and route
        # suffixes (:free), but never whitespace, URL query data or path traversal.
        if (not model or len(model) > 200
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,199}", model)
                or ".." in model.split("/")):
            raise ValueError("Enter a valid provider model ID (letters, numbers, . _ : / @ + - only).")
        protocol = provider_protocol(config["provider"])
        if protocol == "aihorde":
            raise ProviderError("AI Horde is an image-only provider and cannot be tested as a chat model. Use Image Studio's model discovery instead.")
        keyless_compatible = protocol == "openai-compatible" and config.get("auth_mode") == "none"
        if provider_requires_key(config["provider"]) and not api_key and not keyless_compatible:
            raise ProviderError("Add a valid API key before testing this model.")
        if protocol == "ollama":
            payload = {"model": model, "messages": [{"role": "user", "content": "Reply with OK."}],
                       "stream": False, "options": {"num_predict": 1}}
            request = Request(f"{config['base_url']}/api/chat", data=json.dumps(payload).encode("utf-8"),
                              headers=self._headers(None), method="POST")
            response = self._request_json(request, timeout=30)
            valid = isinstance(response.get("message"), dict) and bool(response.get("message"))
        elif protocol == "anthropic":
            payload = {"model": model, "max_tokens": 1,
                       "messages": [{"role": "user", "content": "Reply with OK."}]}
            headers = self._headers(None)
            headers.update({"x-api-key": api_key or "", "anthropic-version": "2023-06-01"})
            request = Request(f"{config['base_url']}/messages", data=json.dumps(payload).encode("utf-8"),
                              headers=headers, method="POST")
            response = self._request_json(request, timeout=30)
            valid = isinstance(response.get("content"), list) and bool(response.get("content"))
        elif protocol == "gemini":
            model_path = model.removeprefix("models/")
            payload = {"contents": [{"role": "user", "parts": [{"text": "Reply with OK."}]}],
                       "generationConfig": {"maxOutputTokens": 1}}
            headers = self._headers(None)
            headers["x-goog-api-key"] = api_key or ""
            request = Request(f"{config['base_url']}/models/{model_path}:generateContent",
                              data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            response = self._request_json(request, timeout=30)
            valid = isinstance(response.get("candidates"), list) and bool(response.get("candidates"))
        else:
            payload = {"model": model, "messages": [{"role": "user", "content": "Reply with OK."}],
                       "max_tokens": 1, "stream": False}
            headers = self._headers(api_key, auth_mode=config.get("auth_mode", "bearer"))
            request = Request(f"{config['base_url']}/chat/completions", data=json.dumps(payload).encode("utf-8"),
                              headers=headers, method="POST")
            try:
                response = self._request_json(request, timeout=30)
            except ProviderError as exc:
                # Newer reasoning/chat models on several OpenAI-compatible APIs
                # have replaced max_tokens with max_completion_tokens. Retry only
                # when the provider explicitly identifies that parameter as the
                # problem; do not retry access, billing, quota or model-not-found errors.
                if exc.retry_hint != "max_completion_tokens":
                    raise
                compatible_payload = {key: value for key, value in payload.items() if key != "max_tokens"}
                compatible_payload["max_completion_tokens"] = 1
                compatible_request = Request(
                    f"{config['base_url']}/chat/completions",
                    data=json.dumps(compatible_payload).encode("utf-8"), headers=headers, method="POST"
                )
                response = self._request_json(compatible_request, timeout=30)
            valid = isinstance(response.get("choices"), list) and bool(response.get("choices"))
        if not isinstance(response, dict) or not valid:
            raise ProviderError("The provider responded, but did not return a valid generation response. Check the provider protocol and model ID.")
        return {"ok": True, "status": "verified", "model": model,
                "message": "Access verified: this key and endpoint accepted a minimal generation request. Usage may be billed."}

    def complete_with_tools(
        self,
        settings: dict[str, Any],
        api_key: str | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_handler,
        max_tool_rounds: int = 5,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Run bounded native function-tool rounds on the exact selected model."""
        if not isinstance(max_tool_rounds, int) or not 1 <= max_tool_rounds <= 16:
            raise ValueError("Tool-round budget must be between 1 and 16.")
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        if not config["model"]:
            raise ProviderError("Choose a model before starting a tool-assisted task.")
        protocol = provider_protocol(config["provider"])
        if protocol == "anthropic":
            return self._complete_anthropic_tools(config, api_key, messages, tools, tool_handler, max_tool_rounds)
        if protocol == "gemini":
            return self._complete_gemini_tools(config, api_key, messages, tools, tool_handler, max_tool_rounds)
        if protocol == "ollama":
            return self._complete_ollama_tools(config, messages, tools, tool_handler, max_tool_rounds)
        return self._complete_openai_tools(config, api_key, messages, tools, tool_handler, max_tool_rounds)

    def _execute_tool_calls(self, calls: list[dict[str, Any]], tool_handler) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        results, activity = [], []
        for call in calls:
            function = call.get("function", {})
            name = function.get("name") if isinstance(function, dict) else None
            raw_args = function.get("arguments", "{}") if isinstance(function, dict) else "{}"
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be an object.")
                result = tool_handler(str(name), arguments)
                summary = str(result.get("summary", "Tool completed")) if isinstance(result, dict) else "Tool completed"
                activity.append({"tool": str(name), "ok": True, "summary": summary[:240]})
            except Exception as exc:
                result = {"ok": False, "error": str(exc)[:500]}
                activity.append({"tool": str(name), "ok": False, "summary": str(exc)[:240]})
            results.append({"id": call.get("id", ""), "name": str(name), "result": result})
        return results, activity

    def _complete_openai_tools(self, config, api_key, messages, tools, tool_handler, max_tool_rounds):
        transcript = [dict(message) for message in messages]
        activity: list[dict[str, Any]] = []
        for _ in range(max_tool_rounds + 1):
            payload = {"model": config["model"], "messages": transcript, "stream": False,
                       "tools": tools, "tool_choice": "auto"}
            request = Request(f"{config['base_url']}/chat/completions",
                              data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              headers=self._headers(api_key, auth_mode=config.get("auth_mode", "bearer")), method="POST")
            response = self._request_json(request)
            choices = response.get("choices", [])
            if not choices or not isinstance(choices[0], dict):
                raise ProviderError("Provider returned no assistant choice while using tools.")
            message = choices[0].get("message", {})
            if not isinstance(message, dict):
                raise ProviderError("Provider returned an invalid tool response.")
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                content = message.get("content") or ""
                if isinstance(content, list):
                    content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
                return (content if isinstance(content, str) else str(content)), activity
            transcript.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls})
            results, round_activity = self._execute_tool_calls(tool_calls, tool_handler)
            activity.extend(round_activity)
            for item in results:
                transcript.append({"role": "tool", "tool_call_id": item["id"],
                                   "content": json.dumps(item["result"], ensure_ascii=False)[:12000]})
        raise ProviderError("The assistant reached the tool-call limit. Ask it to continue from the completed actions.")

    def _complete_anthropic_tools(self, config, api_key, messages, tools, tool_handler, max_tool_rounds):
        system_text = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
        transcript = [{"role": m["role"], "content": m["content"]}
                      for m in messages if m.get("role") in {"user", "assistant"}]
        native_tools = [{"name": item["function"]["name"], "description": item["function"].get("description", ""),
                         "input_schema": item["function"].get("parameters", {"type": "object", "properties": {}})}
                        for item in tools]
        activity = []
        for _ in range(max_tool_rounds + 1):
            payload = {"model": config["model"], "max_tokens": 4096, "messages": transcript,
                       "tools": native_tools, "tool_choice": {"type": "auto"}}
            if system_text:
                payload["system"] = system_text
            headers = self._headers(None)
            headers.update({"x-api-key": api_key or "", "anthropic-version": "2023-06-01"})
            request = Request(f"{config['base_url']}/messages", data=json.dumps(payload).encode("utf-8"),
                              headers=headers, method="POST")
            response = self._request_json(request)
            blocks = response.get("content", [])
            if not isinstance(blocks, list):
                raise ProviderError("Anthropic returned an invalid message while using tools.")
            tool_uses = [block for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use"]
            if not tool_uses:
                text = "".join(block.get("text", "") for block in blocks if isinstance(block, dict) and block.get("type") == "text")
                return text, activity
            transcript.append({"role": "assistant", "content": blocks})
            tool_results = []
            for item in tool_uses:
                call = {"id": item.get("id", ""), "function": {"name": item.get("name", ""), "arguments": item.get("input", {})}}
                result, round_activity = self._execute_tool_calls([call], tool_handler)
                activity.extend(round_activity)
                tool_results.append({"type": "tool_result", "tool_use_id": item.get("id", ""),
                                     "content": json.dumps(result[0]["result"], ensure_ascii=False)[:12000]})
            transcript.append({"role": "user", "content": tool_results})
        raise ProviderError("Claude reached the tool-call limit. Ask it to continue from the completed actions.")

    def _complete_gemini_tools(self, config, api_key, messages, tools, tool_handler, max_tool_rounds):
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents = []
        for message in messages:
            role = message.get("role")
            if role in {"user", "assistant"}:
                contents.append({"role": "model" if role == "assistant" else "user", "parts": [{"text": message["content"]}]})
        declarations = [{"name": item["function"]["name"], "description": item["function"].get("description", ""),
                         "parameters": item["function"].get("parameters", {"type": "OBJECT", "properties": {}})} for item in tools]
        payload: dict[str, Any] = {"contents": contents, "tools": [{"functionDeclarations": declarations}]}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        headers = self._headers(None)
        headers["x-goog-api-key"] = api_key or ""
        model = config["model"].removeprefix("models/")
        request_url = f"{config['base_url']}/models/{model}:generateContent"
        activity = []
        for _ in range(max_tool_rounds + 1):
            request = Request(request_url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              headers=headers, method="POST")
            response = self._request_json(request)
            candidates = response.get("candidates", [])
            parts = candidates[0].get("content", {}).get("parts", []) if candidates and isinstance(candidates[0], dict) else []
            calls = [part["functionCall"] for part in parts if isinstance(part, dict) and isinstance(part.get("functionCall"), dict)]
            if not calls:
                return "".join(part.get("text", "") for part in parts if isinstance(part, dict)), activity
            # Retain the model function-call part exactly as returned by Gemini.
            contents.append({"role": "model", "parts": parts})
            result_parts = []
            for call in calls:
                tool_call = {"id": "", "function": {"name": call.get("name", ""), "arguments": call.get("args", {})}}
                result, round_activity = self._execute_tool_calls([tool_call], tool_handler)
                activity.extend(round_activity)
                result_parts.append({"functionResponse": {"name": call.get("name", ""), "response": result[0]["result"]}})
            contents.append({"role": "user", "parts": result_parts})
        raise ProviderError("Gemini reached the tool-call limit. Ask it to continue from the completed actions.")

    def _complete_ollama_tools(self, config, messages, tools, tool_handler, max_tool_rounds):
        transcript = [dict(message) for message in messages if message.get("role") != "system"]
        system = [m.get("content", "") for m in messages if m.get("role") == "system"]
        if system:
            transcript.insert(0, {"role": "system", "content": "\n\n".join(system)})
        activity = []
        for _ in range(max_tool_rounds + 1):
            payload = {"model": config["model"], "messages": transcript, "tools": tools, "stream": False}
            request = Request(f"{config['base_url']}/api/chat", data=json.dumps(payload).encode("utf-8"),
                              headers=self._headers(None), method="POST")
            response = self._request_json(request)
            message = response.get("message", {})
            calls = message.get("tool_calls", []) if isinstance(message, dict) else []
            if not calls:
                return str(message.get("content", "") if isinstance(message, dict) else ""), activity
            transcript.append({"role": "assistant", "content": message.get("content"), "tool_calls": calls})
            results, round_activity = self._execute_tool_calls(calls, tool_handler)
            activity.extend(round_activity)
            for item in results:
                transcript.append({"role": "tool", "tool_name": item["name"],
                                   "content": json.dumps(item["result"], ensure_ascii=False)[:12000]})
        raise ProviderError("Ollama reached the tool-call limit. Ask it to continue from the completed actions.")

    def generate_image(
        self,
        settings: dict[str, Any],
        api_key: str | None,
        prompt: str,
        *,
        model: str = "gpt-image-2.5-flare",
        size: str = "1024x1024",
        quality: str = "medium",
        aspect_ratio: str | None = None,
    ) -> tuple[bytes, str, str]:
        """Generate an image through OpenAI Images API or Gemini Interactions API.

        ``size`` remains accepted for older callers. New callers should provide
        ``aspect_ratio`` so provider-specific dimensions are selected here.
        """
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        clean_prompt = (prompt or "").strip()
        if not clean_prompt or len(clean_prompt) > 4000:
            raise ValueError("Enter an image prompt between 1 and 4,000 characters.")
        if not api_key and config["provider"] != "aihorde":
            raise ProviderError("Image generation needs a saved provider API key.")

        legacy_size_ratios = {
            "1024x1024": "1:1", "1536x1024": "3:2", "1024x1536": "2:3",
        }
        ratio_to_openai_size = {
            "1:1": "1024x1024",
            "3:2": "1536x1024",
            "2:3": "1024x1536",
            "16:9": "1536x864",
            "9:16": "864x1536",
            "4:3": "1360x1024",
            "3:4": "1024x1360",
            "4:5": "1024x1280",
            "5:4": "1280x1024",
            "21:9": "1792x768",
        }
        allowed_ratios = set(ratio_to_openai_size) | {"1:4", "4:1", "1:8", "8:1"}
        ratio = aspect_ratio or legacy_size_ratios.get(size)
        if ratio not in allowed_ratios:
            raise ValueError("Choose a supported image aspect ratio.")
        if quality not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Choose a supported image quality.")

        if config["provider"] == "aihorde":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._()+:/-]{0,159}", model or ""):
                raise ValueError("Choose an exact active AI Horde image model from the model list.")
            dimensions = {
                "1:1": (512, 512), "3:2": (768, 512), "2:3": (512, 768),
                "16:9": (896, 512), "9:16": (512, 896), "4:3": (704, 512),
                "3:4": (512, 704), "4:5": (512, 640), "5:4": (640, 512),
                "21:9": (896, 384),
            }
            if ratio not in dimensions:
                raise ValueError("AI Horde supports the standard aspect ratios shown in Image Studio.")
            width, height = dimensions[ratio]
            horde_key = api_key or "0000000000"  # Public anonymous key; registered keys get better queue priority.
            headers = {
                "Accept": "application/json", "Content-Type": "application/json",
                "apikey": horde_key, "Client-Agent": "Spaceline:0.9.6:personal-client",
            }
            payload = {
                "prompt": clean_prompt,
                "params": {"n": 1, "width": width, "height": height, "steps": 25,
                           "cfg_scale": 7.0},
                "nsfw": False, "censor_nsfw": True, "models": [model], "r2": True,
            }
            submit = Request(
                f"{config['base_url']}/v2/generate/async",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers, method="POST",
            )
            accepted = self._request_json(submit, timeout=30)
            request_id = str(accepted.get("id") or "").strip()
            if not request_id:
                reason = str(accepted.get("message") or "The Horde did not return a generation ID.")[:240]
                raise ProviderError(f"AI Horde could not queue this image: {reason}")
            if accepted.get("is_possible") is False:
                reason = str(accepted.get("message") or "No active worker can fulfil this exact model/settings request.")[:240]
                raise ProviderError(f"AI Horde cannot fulfil this request: {reason}")

            completed = False
            last_check: dict[str, Any] = {}
            # Horde is volunteer-powered and can queue slowly. Poll its cached
            # status endpoint at 5s intervals; never resubmit the paid/free job.
            for attempt in range(120):  # bounded at ten minutes
                check_request = Request(
                    f"{config['base_url']}/v2/generate/check/{request_id}",
                    headers={"Accept": "application/json", "apikey": horde_key,
                             "Client-Agent": "Spaceline:0.9.6:personal-client"},
                    method="GET",
                )
                last_check = self._request_json(check_request, timeout=30)
                if last_check.get("faulted"):
                    raise ProviderError(f"AI Horde generation failed on its worker. Request ID: {request_id}. Try another active model.")
                if last_check.get("done"):
                    completed = True
                    break
                if last_check.get("is_possible") is False:
                    raise ProviderError(f"AI Horde cannot fulfil this request with the selected model. Request ID: {request_id}.")
                if attempt < 119:
                    time.sleep(5)
            if not completed:
                queue_position = last_check.get("queue_position")
                position_text = f" Queue position: {queue_position}." if queue_position is not None else ""
                raise ProviderError(
                    f"AI Horde is still processing this request after ten minutes.{position_text} Request ID: {request_id}. "
                    "Do not submit it again immediately; check the Horde queue before retrying."
                )
            result_request = Request(
                f"{config['base_url']}/v2/generate/status/{request_id}",
                headers={"Accept": "application/json", "apikey": horde_key,
                         "Client-Agent": "Spaceline:0.9.6:personal-client"},
                method="GET",
            )
            result_data = self._request_json(result_request, timeout=30)
            generations = result_data.get("generations")
            if not isinstance(generations, list) or not generations or not isinstance(generations[0], dict):
                raise ProviderError(f"AI Horde completed the request but returned no image. Request ID: {request_id}.")
            image_url = generations[0].get("img") or generations[0].get("url")
            if not isinstance(image_url, str) or not image_url:
                raise ProviderError(f"AI Horde returned an unsupported image result. Request ID: {request_id}.")
            image_bytes, mime_type = self._download_provider_image(image_url, provider_name="AI Horde")
            extension = "jpeg" if mime_type in {"image/jpeg", "image/jpg"} else "webp" if mime_type == "image/webp" else "png"
            return image_bytes, mime_type, extension

        edenai_host = (urlsplit(config["base_url"]).hostname or "").lower() == "api.edenai.run"
        if config["provider"] == "edenai" or (config["provider"] == "openai-compatible" and edenai_host):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.:/+-]+", model or ""):
                raise ValueError("Eden AI image models must use the exact provider/model identifier returned by its image catalog.")
            ratio_to_eden_size = {
                "1:1": "1024x1024", "3:2": "1536x1024", "2:3": "1024x1536",
                "16:9": "1536x864", "9:16": "864x1536", "4:3": "1360x1024",
                "3:4": "1024x1360", "4:5": "1024x1280", "5:4": "1280x1024",
                "21:9": "1792x768",
            }
            if ratio not in ratio_to_eden_size:
                raise ValueError("Eden AI image generation supports common aspect ratios from the image studio.")
            # Eden V3 supports `quality` only for models whose own provider
            # accepts it. The catalog does not expose a reliable per-model
            # quality capability, so omit it rather than sending a potentially
            # unsupported field and turning a valid generation into HTTP 400.
            payload = {
                "model": model,
                "prompt": clean_prompt,
                "n": 1,
                "size": ratio_to_eden_size[ratio],
                "response_format": "b64_json",
            }
            request = Request(
                f"{config['base_url']}/images/generations",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=self._headers(api_key), method="POST",
            )
            data = self._request_json(request)
            rows = data.get("data")
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                raise ProviderError("Eden AI returned no generated image. Check its image model, account credits and response details.")
            encoded = rows[0].get("b64_json")
            mime_type = str(rows[0].get("mime_type") or rows[0].get("mimeType") or "image/png")
            if not encoded:
                image_url = rows[0].get("url")
                if isinstance(image_url, str) and image_url:
                    image_bytes, mime_type = self._download_eden_image(image_url)
                    extension = "jpeg" if mime_type in {"image/jpeg", "image/jpg"} else "webp" if mime_type == "image/webp" else "png"
                    return image_bytes, mime_type, extension
                raise ProviderError("Eden AI completed the request but returned neither b64_json nor a downloadable image URL.")
        elif config["provider"] == "openai":
            model_ids = {
                "gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
                "gpt-image-2.6-flare", "gpt-image-2.6-sunburst",
            }
            if model not in model_ids:
                raise ValueError("Choose a supported GPT Image model.")
            if ratio not in ratio_to_openai_size:
                raise ValueError("OpenAI GPT Image supports aspect ratios between 1:3 and 3:1.")
            payload = {
                "model": model, "prompt": clean_prompt,
                "size": ratio_to_openai_size[ratio], "quality": quality,
                "n": 1, "output_format": "png",
            }
            request = Request(
                f"{config['base_url']}/images/generations",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=self._headers(api_key), method="POST",
            )
            data = self._request_json(request)
            rows = data.get("data")
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                raise ProviderError("The image provider returned no generated image.")
            encoded = rows[0].get("b64_json")
            mime_type = "image/png"
        elif config["provider"] == "gemini":
            gemini_models = {
                "gemini-3.1-flash-image", "gemini-3.1-flash-lite-image", "gemini-3-pro-image",
            }
            if model not in gemini_models:
                raise ValueError("Choose a supported Gemini image model.")
            if model == "gemini-3.1-flash-lite-image":
                if quality not in {"low", "medium"}:
                    raise ValueError("Gemini 3.1 Flash Lite Image supports 1K output only. Choose Low or Medium quality.")
                image_size = "1K"
            elif model == "gemini-3.1-flash-image" and quality == "low":
                image_size = "512"
            else:
                image_size = {"low": "1K", "medium": "1K", "high": "2K", "xhigh": "4K", "max": "4K"}[quality]
            if ratio not in allowed_ratios:
                raise ValueError("Choose a supported Gemini image aspect ratio.")
            payload = {
                "model": model,
                "input": clean_prompt,
                "response_format": {
                    "type": "image", "mime_type": "image/png",
                    "aspect_ratio": ratio, "image_size": image_size,
                },
            }
            headers = self._headers(None)
            headers["x-goog-api-key"] = api_key
            request = Request(
                f"{config['base_url']}/interactions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers, method="POST",
            )
            data = self._request_json(request)
            output_image = data.get("output_image") if isinstance(data.get("output_image"), dict) else None
            if output_image is None:
                for step in data.get("steps", []) if isinstance(data.get("steps"), list) else []:
                    if not isinstance(step, dict) or step.get("type") not in {None, "model_output"}:
                        continue
                    for block in step.get("content", []) if isinstance(step.get("content"), list) else []:
                        if isinstance(block, dict) and block.get("type") == "image":
                            output_image = block
                            break
                    if output_image:
                        break
            encoded = output_image.get("data") if isinstance(output_image, dict) else None
            mime_type = str((output_image or {}).get("mime_type") or (output_image or {}).get("mimeType") or "image/png")
            if not encoded:
                status = str(data.get("status") or "").lower()
                if status and status not in {"completed", "succeeded"}:
                    raise ProviderError(f"Gemini image job did not complete (status: {status[:40]}).")
                raise ProviderError("Gemini returned no image data. Check the model response and image-generation access.")
        else:
            raise ProviderError("Image generation is supported through OpenAI, Google Gemini, Eden AI and AI Horde image connections.")

        if not isinstance(encoded, str) or not encoded:
            raise ProviderError("The image provider returned an unsupported image response format.")
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise ProviderError("The image provider returned invalid image data.") from None
        if not image_bytes or len(image_bytes) > 20 * 1024 * 1024:
            raise ProviderError("The generated image is empty or exceeds the 20 MB safety limit.")
        extension = "jpeg" if mime_type in {"image/jpeg", "image/jpg"} else "webp" if mime_type == "image/webp" else "png"
        return image_bytes, mime_type, extension

    def _download_eden_image(self, image_url: str) -> tuple[bytes, str]:
        """Backward-compatible Eden image download wrapper."""
        return self._download_provider_image(image_url, provider_name="Eden AI")

    def _download_provider_image(self, image_url: str, *, provider_name: str = "Image provider") -> tuple[bytes, str]:
        """Download a provider-hosted image without allowing HTTP, redirects or private-network SSRF."""
        from urllib.error import HTTPError
        from urllib.request import HTTPRedirectHandler, build_opener

        parts = urlsplit(image_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ProviderError(f"{provider_name} returned an unsafe image URL. Expected a direct HTTPS image URL.")
        if parts.port not in (None, 443):
            raise ProviderError(f"{provider_name} returned an image URL on an unsupported port.")
        # Do not let a provider-returned URL turn the local Spaceline backend into
        # an SSRF proxy. Refuse loopback, private, link-local, multicast and
        # other non-public DNS answers before opening the URL.
        try:
            resolved = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
            addresses = {ipaddress.ip_address(row[4][0]) for row in resolved}
        except (OSError, ValueError):
            raise ProviderError(f"{provider_name} returned an image host that could not be safely resolved.") from None
        if not addresses or any(not address.is_global for address in addresses):
            raise ProviderError(f"{provider_name} returned an image URL that resolves to a non-public network address.")

        class _BlockRedirects(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        request = Request(image_url, headers={"Accept": "image/*"}, method="GET")
        opener = build_opener(_BlockRedirects())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                mime_type = str(response.headers.get_content_type() or "")
                if not mime_type.startswith("image/"):
                    raise ProviderError(f"{provider_name}'s image URL did not return an image content type.")
                image_bytes = response.read(20 * 1024 * 1024 + 1)
        except ProviderError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError):
            raise ProviderError(f"Could not safely download the generated image from {provider_name}. Try generating again.") from None
        if not image_bytes or len(image_bytes) > 20 * 1024 * 1024:
            raise ProviderError(f"{provider_name}'s generated image is empty or exceeds the 20 MB safety limit.")
        return image_bytes, mime_type

    def get_context_window(self, settings: dict[str, Any]) -> tuple[int | None, str | None]:
        """Discover context size only where the provider exposes it; never guess cloud model limits."""
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        if config["provider"] != "ollama" or not config["model"]:
            return None, None
        request = Request(
            f"{config['base_url']}/api/show",
            data=json.dumps({"model": config["model"]}).encode("utf-8"),
            headers=self._headers(None), method="POST",
        )
        try:
            data = self._request_json(request)
        except ProviderError:
            return None, None
        model_info = data.get("model_info") if isinstance(data.get("model_info"), dict) else {}
        for key, value in model_info.items():
            if str(key).endswith(".context_length"):
                try:
                    length = int(value)
                    if 1024 <= length <= 10_000_000:
                        return length, "provider"
                except (TypeError, ValueError):
                    pass
        parameters = data.get("parameters", "")
        match = re.search(r"(?im)^\s*num_ctx\s+(\d+)\s*$", str(parameters))
        if match:
            length = int(match.group(1))
            if 1024 <= length <= 10_000_000:
                return length, "provider"
        return None, None

    def stream_chat(
        self,
        settings: dict[str, Any],
        api_key: str | None,
        messages: list[dict[str, str]],
    ) -> Iterator[str]:
        config = normalize_settings({**settings, "name": settings.get("name", "Connection")})
        if not config["model"]:
            raise ProviderError("Choose a model before starting a chat.")
        if not messages:
            raise ProviderError("Enter a message to start the conversation.")
        protocol = provider_protocol(config["provider"])
        if protocol == "ollama":
            yield from self._stream_ollama(config, messages)
        elif protocol == "anthropic":
            yield from self._stream_anthropic(config, api_key, messages)
        elif protocol == "gemini":
            yield from self._stream_gemini(config, api_key, messages)
        else:
            yield from self._stream_openai_compatible(config, api_key, messages)

    def _stream_openai_compatible(self, config: dict[str, Any], api_key: str | None,
                                  messages: list[dict[str, str]]) -> Iterator[str]:
        payload = {"model": config["model"], "messages": messages, "stream": True}
        request = Request(f"{config['base_url']}/chat/completions",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers=self._headers(api_key, "text/event-stream", auth_mode=config.get("auth_mode", "bearer")), method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                yield from self._openai_chunks(response)
        except HTTPError as exc:
            raise _safe_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise _safe_network_error(exc) from None

    def _stream_ollama(self, config: dict[str, Any], messages: list[dict[str, str]]) -> Iterator[str]:
        payload = {"model": config["model"], "messages": messages, "stream": True}
        request = Request(f"{config['base_url']}/api/chat",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers=self._headers(None, "application/x-ndjson"), method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                yield from self._ollama_chunks(response)
        except HTTPError as exc:
            raise _safe_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise _safe_network_error(exc) from None

    def _stream_anthropic(self, config: dict[str, Any], api_key: str | None,
                          messages: list[dict[str, str]]) -> Iterator[str]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        chat_messages = [{"role": m["role"], "content": m["content"]}
                         for m in messages if m.get("role") in {"user", "assistant"}]
        payload: dict[str, Any] = {"model": config["model"], "max_tokens": 4096,
                                   "messages": chat_messages, "stream": True}
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = self._headers(None, "text/event-stream")
        headers.update({"x-api-key": api_key or "", "anthropic-version": "2023-06-01"})
        request = Request(f"{config['base_url']}/messages",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                yield from self._anthropic_chunks(response)
        except HTTPError as exc:
            raise _safe_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise _safe_network_error(exc) from None

    def _stream_gemini(self, config: dict[str, Any], api_key: str | None,
                       messages: list[dict[str, str]]) -> Iterator[str]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents = []
        for message in messages:
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue
            contents.append({"role": "model" if role == "assistant" else "user",
                             "parts": [{"text": message["content"]}]})
        payload: dict[str, Any] = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        model = config["model"].removeprefix("models/")
        query = urlencode({"alt": "sse"})
        headers = self._headers(None, "text/event-stream")
        headers["x-goog-api-key"] = api_key or ""
        request = Request(f"{config['base_url']}/models/{model}:streamGenerateContent?{query}",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                yield from self._gemini_chunks(response)
        except HTTPError as exc:
            raise _safe_http_error(exc) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise _safe_network_error(exc) from None

    @staticmethod
    def _openai_chunks(response: Iterable[bytes]) -> Iterator[str]:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                packet = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = packet.get("choices", []) if isinstance(packet, dict) else []
            if not choices or not isinstance(choices[0], dict):
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content") if isinstance(delta, dict) else None
            if isinstance(content, str) and content:
                yield content
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        yield part["text"]

    @staticmethod
    def _ollama_chunks(response: Iterable[bytes]) -> Iterator[str]:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                packet = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(packet, dict):
                continue
            message = packet.get("message", {})
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str) and content:
                yield content
            if packet.get("error"):
                raise ProviderError("Ollama reported an error. Check the selected model and local Ollama service.")
            if packet.get("done") is True:
                break

    @staticmethod
    def _anthropic_chunks(response: Iterable[bytes]) -> Iterator[str]:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                packet = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if not isinstance(packet, dict):
                continue
            if packet.get("type") == "content_block_delta":
                delta = packet.get("delta", {})
                if isinstance(delta, dict) and delta.get("type") == "text_delta" and isinstance(delta.get("text"), str):
                    yield delta["text"]
            elif packet.get("type") == "error":
                raise ProviderError("Anthropic returned an error. Check the selected model, key and account access.")

    @staticmethod
    def _gemini_chunks(response: Iterable[bytes]) -> Iterator[str]:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                packet = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if not isinstance(packet, dict):
                continue
            candidates = packet.get("candidates", [])
            if candidates and isinstance(candidates[0], dict):
                content = candidates[0].get("content", {})
                parts = content.get("parts", []) if isinstance(content, dict) else []
                for part in parts:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        yield part["text"]
            if packet.get("error"):
                raise ProviderError("Gemini returned an error. Check the selected model, key and account access.")
