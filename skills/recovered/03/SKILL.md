---
name: api-testing
description: Test HTTP APIs and debug provider authentication and endpoint issues.
triggers: api, endpoint, postman, request, rest, bearer token, api key, provider, model endpoint
---
Check the exact base URL, route, HTTP method, authentication scheme and provider-specific key. Do not append duplicate route suffixes. Distinguish 401 authentication failures, 403 permission failures, 404 endpoint/model failures and 429 rate limits. Never print secrets. Test a small harmless request before interpreting provider availability.
