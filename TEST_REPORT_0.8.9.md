# Spaceline 0.8.9 — Free Image Provider Release Report

Release build: 2026-11-11

## Scope

This incremental 0.8.9 build adds AI Horde as an optional free, image-only community image provider. Existing direct OpenAI, Gemini, and Eden AI connections remain separate and unchanged. No Sand AI or MAGI integration was added.

## Verification results

- Full Python suite: **314 passed, 68 subtests passed**.
- AI Horde-focused suite: **11 passed**.
- Frontend JavaScript syntax: `node --check static/app.js` — passed.
- Python bytecode compilation: `python -m compileall -q app` — passed.
- Backend import / provider initialization — passed.
- Anonymous image-model discovery route — passed with mocked provider responses.
- Anonymous image-generation route — passed with mocked image bytes.
- Asynchronous submission, status polling and result retrieval — passed with mocked API responses.
- Provider selection isolation and image-only restrictions — covered by tests.
- Anonymous key handling, registered-key handling, model discovery and official endpoint allowlist — covered by tests.
- Result download validation (HTTPS, DNS/private-network checks, redirect blocking, MIME and size validation) — covered by tests.

## AI Horde setup

1. Launch Spaceline and open **Customize → Providers & Keys → Add connection**.
2. Choose **AI Horde (Free Community Images)**.
3. Leave the optional key list empty to use anonymous access, or add a free registered AI Horde key from https://aihorde.net/register.
4. Save the connection and open **Image Studio**.
5. Select the AI Horde connection, refresh the model list, choose an online worker model and generate.

AI Horde uses volunteer GPU workers. Anonymous access uses its published public key `0000000000` and has the lowest queue priority. A registered free account can get better priority through kudos. Model availability and wait time vary with online workers and current queue load.

## Integration behavior and security

- Default API endpoint: `https://aihorde.net/api`.
- Model discovery: `GET /v2/status/models`.
- Generation: `POST /v2/generate/async`; polling: `GET /v2/generate/check/{id}`; results: `GET /v2/generate/status/{id}`.
- AI Horde is image-only and is not selectable as the chat provider.
- No saved key is required for anonymous access. A selected registered key remains optional.
- AI Horde connections are restricted to official HTTPS hosts to prevent sending keys to arbitrary endpoints.
- Downloaded images are fetched only from public HTTPS endpoints, with DNS/private-address validation, redirects disabled, MIME checks and a 20 MB bound.
- Spaceline does not automatically switch providers/models or resubmit a generation after an uncertain timeout.
- The build adds no new Python dependencies and does not bundle third-party model weights.

## Live-service limitation

Automated tests use mocked HTTP responses. No real image generation was run against the user's account in this environment. AI Horde is a volunteer-powered community service, so the actual model list, queue duration and completion depend on live workers. Anonymous requests have the lowest priority and may be restricted during high load.

## Existing paid-provider clarification

Google's current Gemini API pricing lists `gemini-3.1-flash-image` as unavailable on the Free Tier. Eden AI requests also require available account credits/billing. AI Horde provides the free option in this build, but it is not a universal free API key for all proprietary models.

## 2026-11-12 audit/hotfix verification

- Root-cause review of the reported `Local workspace is not authorized` image-generation failure: this message is produced by Spaceline's local-session guard before any provider API call. The image endpoint correctly requires `X-Spaceline-Token`; the frontend now detects this exact stale-session response instead of treating it as a provider failure.
- Stale server-session recovery: Spaceline saves the in-progress image prompt/settings locally, refreshes the page to obtain the current server token, restores the image-generation state, and does **not** automatically resubmit the generation request. This preserves the one-request-per-user-action rule and does not weaken the local API authorization.
- Full Python suite after hotfix: **316 passed, 68 subtests passed**.
- Frontend JavaScript syntax after hotfix: `node --check static/app.js` — passed.
- Python bytecode compilation after hotfix: `python -m compileall -q app` — passed.
- Security scan found no obvious hard-coded provider secrets in application source; regex matches were limited to intentional secret-pattern test fixtures.
- Real external image generation could not be verified from this isolated execution environment because outbound provider access was unavailable. Existing provider tests therefore remain mocked for live-service calls.
