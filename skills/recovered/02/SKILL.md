---
name: API Integration
description: Design and debug API integrations with clear endpoint contracts, auth, pagination, retries, rate limits, streaming, timeout and safe secret handling.
triggers: api integration, rest api, endpoint, webhook, openapi, authentication error, http error, rate limit, provider connection
---

# API integration

1. Confirm the provider's current API documentation, exact base URL, endpoint, method, auth scheme and required headers.
2. Keep secrets in a vault or environment reference; never echo keys in logs, errors, activity or generated code.
3. Validate request and response shapes, status codes, timeouts, pagination and streaming behavior.
4. Retry only transient/idempotent failures. Do not replay a request after a successful side effect or partial stream.
5. Distinguish authentication, permission, billing, quota, model-not-found, validation and provider-outage errors.
6. Test with mocked transport for deterministic cases and an opt-in minimal live probe for real entitlement.
