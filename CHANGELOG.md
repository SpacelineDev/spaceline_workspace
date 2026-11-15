## 0.9.6 — Login, landing page, Firebase and account isolation (2026-11-13)

- Added a responsive first-open landing experience introducing Spaceline and showing Google, GitHub and email/password sign-in alongside the existing workspace after authentication.
- Fixed Firebase frontend initialization by defining the web config object before checking it or calling `initializeApp`.
- Added GitHub Firebase Authentication with popup-to-redirect fallback and the `read:user` / `user:email` scopes; GitHub still requires valid OAuth credentials configured in Firebase Console.
- Preserved Google popup-to-redirect fallback, email/password account creation and sign-in, password reset, password visibility and remember-me persistence.
- Added per-verified-Firebase-UID workspace roots for SQLite state, project files, API-key metadata, generated images, skills and embedded Chromium profiles. The first authenticated account claims and migrates legacy installation-wide data using a pending/claimed ownership marker; interrupted migration fails closed; a cross-process filesystem lock serializes competing first-account claims. Later accounts get separate empty workspaces. The UID is hashed for folder names and the ownership marker.
- Added regression tests proving the workspace API does not expose one Firebase UID's project to another UID.
- Expanded test fixtures to exercise the production Firebase-token middleware using a synthetic test verifier; production behavior still requires real Firebase Admin verification.
- Release package and environment template remain secret-free. The actual Firebase Web API key/app ID and Admin Application Default Credentials must be configured locally; genuine Google/GitHub sign-in and Windows runtime/Chromium startup still require manual verification.

## 0.9.5 — 2026-11-12

- Replaced Chromium-based Web Search / Deep Research retrieval with direct HTTP search and source reading. Research now stays in the conversation/Activity workflow and does not start or inspect embedded Chromium as a side effect.
- Added three-way concurrent initial search fan-out for Deep Research and two-way fan-out for Web Search, followed by selected-model tool rounds for targeted searches and source reads. Search/source content is bounded, treated as untrusted data, and source URLs are checked and followed through safe redirects.
- Preserved the embedded Playwright Chromium workbench for explicit interactive browser requests. Added negative-intent handling so “do not open the browser” stays in research mode.
- Fixed the post-response browser snapshot path that caused Chromium to start after research completed.
- Kept one icon-only note-copy button below every assistant response; browser-level regression confirms all legacy copy buttons are removed, and the full Markdown response is copied exactly.
- Added port collision handling and cache-busted assets so the newly launched version cannot silently appear to be an older process using port 8765.
- Compared the workflow with the current public Codex release stream (Codex CLI 0.167.2, Nov 11; Codex app 26.1007, Oct 8), focusing on task threads, review, worktrees, agent progress, and distinct browser/research workflows. See `CODEX_WORKFLOW_REVIEW_2026-11-12.md` for the feature comparison and limitations.
- Verification: 377 tests and 68 subtests pass; Chromium DOM regression confirms one icon-only note action and exact clipboard payload. Live internet search could not be verified from the build environment because outbound DNS resolution is restricted.

## 0.9.4 — 2026-11-12

- Fixed a real MutationObserver loop in message-copy cleanup: browser-normalized SVG markup is now checked structurally instead of compared as serialized `innerHTML`.
- Kept one icon-only note-copy action below each completed assistant response; legacy Copy / Copy markdown / Copy all / Copy code controls are removed even when inserted after render.
- Added a browser regression proving observer cleanup settles, exactly one icon remains below the response, and the copied content is the complete original Markdown (including prompts and code).
- Revalidated research routing: Web Search / Deep Research use private headless Chromium for source retrieval, show progress in Activity, and leave the Browser workbench available without opening it automatically.
- Explicit “open/show/use the browser” requests now take precedence over research-mode hiding; ordinary Web Search / Deep Research still leave Chromium in the background.
- The Review workbench tab is now preserved across reloads. No provider/model switching was introduced; the model selected in the composer remains the model that performs reasoning and synthesis.

## 0.9.3 — 2026-11-12

- Hardened assistant reply copy controls: each completed assistant reply has exactly one icon-only note button beneath the full Markdown response; stale/legacy copy buttons are removed and a DOM observer guards dynamically inserted message markup. Code blocks no longer have independent copy actions. Terminal output copying remains separate.
- Improved Web Search and Deep Research: Web Search now seeds two distinct searches; Deep Research seeds three distinct search angles before the selected model starts its follow-up tool loop. Evidence is bounded, marked as untrusted page content, and initial search failures are disclosed. Tool-round budgets are 8 for Web Search and 14 for Deep Research.
- Kept the embedded Playwright Chromium session headless and private during research. Search progress remains in Activity; Browser is shown only when the user explicitly opens it.
- Added local Git worktree support in Review: create a separate task branch/folder from committed HEAD, list isolated workspaces, and open a worktree as a selectable Spaceline project. The base checkout is left untouched; uncommitted changes are not copied.
- Versioned static assets as 0.9.3 and disabled caching for both the application HTML and static JS/CSS so older copy controls cannot persist from a cached bundle. Updated the launcher-ready marker and provider user-agent.
- Added regression tests for multi-angle research seeding, isolated worktree creation/listing and error handling, stale message-copy control cleanup, private research UI routing, and release asset versioning.

## 0.9.2 — 2026-11-12

- Made the assistant response action icon-only: one note symbol below each completed assistant reply copies the complete original Markdown content (including prompts and code). Removed duplicate copy actions from message toolbars and code blocks. The live response shows its note action only after completion; terminal output remains a separate control.
- Made Web Search and Deep Research start with a real live search through the app-managed headless Chromium session. The result is passed into the currently selected model's context before it generates an answer. Web Search receives up to 6 model tool rounds; Deep Research receives up to 10. Search failures are explicitly disclosed instead of being presented as completed research.
- Kept research inside the chat workflow: browser tool activity updates the Activity panel and refreshes private browser state without automatically switching to the visible Browser tab. The Browser tab remains available for explicit manual browsing.
- Added a read-only Git Review workbench tab with tracked working-tree status and redacted unstaged diff for the selected project. It does not stage, commit, reset or modify files; staged changes and untracked files are not included yet.
- Changed the launcher to scan loopback ports 8765–8799 and open the exact URL for the newly started process. This prevents an old server already using 8765 from making a fresh install appear unchanged. Versioned static assets as 0.9.2 and disabled caching for the main HTML response.
- Added regression tests for initial research evidence, search-failure disclosure, no-search chat behavior, launcher port selection, and Git Review authorization/read-only routing.
- Verification: `python -m pytest -q` — 347 passed, 68 subtests passed (final result is recorded in `TEST_REPORT_0.9.2.md`).

## 0.9.1 — 2026-11-12

- Reworked Web Search and Deep Research so research runs privately through the retained embedded Chromium engine while progress stays in the chat Activity panel. The Browser workbench is opened only when explicitly requested.
- Improved search/research instructions for date checks, source quality, independent cross-checks, inline citations and structured reports. Deep Research now receives a larger bounded tool-call budget.
- Replaced visible message copy labels with one icon-only note-copy action below every assistant response, including replies containing code or prompts. Added cleanup for legacy duplicate message copy controls.
- Added release-versioned static asset URLs and no-store home-page headers to prevent stale front-end bundles and session pages.

## 0.9.0 — 2026-11-12
- Added local workspace personalization: user context, response tone/detail/format, problem-solving style, behavior toggles and additional instructions.
- Applied personalization to the system context of the exact selected model. Preferences do not fine-tune providers or override security, system, developer or task constraints.
- Refined Deep Think into structured problem-solving; web browsing is no longer forced unless the task needs current external evidence. Web Search and Deep Research keep their browser-backed research path.
- Added a source + live HTML preview split, delayed auto-save, explicit save state, preview refresh, top-bar preview access and Ctrl+S in the project editors.
- Moved the interface to black/white/neutral-gray styling and retained accessible focus/reduced-motion treatments.
- Added tests for personalization persistence and prompt application, fixed provider/model preservation, Deep Think routing and preview/personalization UI contracts.
- Updated the local version and Windows dependency-ready marker to 0.9.0.
- Simplified chat reply actions to one **▤ Copy note** button below each assistant reply. It copies the complete reply as Markdown (including code); removed the separate Copy, Copy raw code, Copy full markdown and code-block Copy code controls. Terminal output copying remains available.

## 0.8.9 — 2026-11-11

- Added AI Horde as an optional image-only free community provider: anonymous access, active model discovery, queued async generation, and optional registered free keys for better queue priority. AI Horde requests are pinned to official HTTPS hosts and use bounded safe downloads.
- Added Eden AI as a first-class provider preset for Image Studio, using the official V3 OpenAI-compatible image endpoints (`/v3/images/models` and `/v3/images/generations`).
- Eden AI image models are discovered live from the saved account key and region; Spaceline uses the exact `provider/model` ID returned by Eden AI instead of assuming every account has the same catalog.
- Added Eden AI request/response handling for `b64_json` and HTTPS image URLs, provider-aware image dimension mapping and conservative parameter handling, and bounded image download handling.
- Added Eden AI key authentication testing against its image-model catalog, plus an image-model discovery endpoint protected by the local Spaceline session token.
- Kept direct OpenAI and Gemini integrations independent. No Sand AI/MAGI integration or automatic provider switching was added.
- Added regression tests for Eden AI endpoint routing, Bearer authentication, live model catalog parsing, key checks, profile access control, and frontend model selection.
- Gemini Image Studio 400-diagnostic hotfix: confirmed the existing `/v1beta/interactions` route and `response_format` schema against Google's current image-generation docs; preserved that supported route, now surfaces the provider's safe 400 error detail with API-key redaction, and handles the documented `output_image` and `steps[].content[]` response shapes more explicitly.
- Added a dedicated Image Studio destination in the sidebar and a persistent top-bar Image Studio launch button; image generation is now reachable independently of chat and the workbench tab.
- Introduced a standalone premium Image Studio page with a focused creation hero, provider readiness, saved-creation count, responsive prompt controls and a dedicated local gallery.
- Preserved prompt, provider, model, aspect-ratio and quality selections across image-generation refreshes.
- Added a sequential **Test all saved keys** action in the API key vault. It checks every stored credential against its provider model-list endpoint, records per-key results, shows progress, and never returns or displays credential values. This is an authentication/catalog check, not a guarantee that every model is entitled or that generation billing/quota is available.
- Sanitized the user-facing key-test error categories so provider error details cannot accidentally display credential material.
- Added UI contract tests for Image Studio routing, image form/gallery wiring and sequential saved-key testing.
- Expanded Image Studio with persistent local image history, prompt/model metadata, gallery refresh, download and delete actions.
- Added provider-aware aspect-ratio controls, including widescreen and vertical formats, with OpenAI dimensions mapped to supported custom sizes.
- Added Gemini 3.1 Flash Lite Image and Gemini 3 Pro Image alongside Gemini 3.1 Flash Image; enforced Flash Lite's 1K-only output limit.
- Added OpenAI GPT Image 2.5/2.6 Flare and Sunburst options with aspect ratio and quality settings.
- Kept legacy 0.8.x image `size` requests compatible while the updated UI sends explicit aspect ratios.
- Merged the FastAPI lifespan shutdown hotfix and versioned the Windows dependency-ready marker to 0.8.9.
- Added regression coverage for image model/resolution routing, persistent image history, local-session authorization, and image deletion.

## 0.8.8 — 2026-11-08

- Refined the visual language into a classic premium green-charcoal workspace: calmer graphite-green surfaces, restrained brass accents, sharper type hierarchy, more legible chat typography, balanced card depth and floating controls without excessive glow.
- Added a searchable command palette with **Ctrl+K**, 15 workspace actions, keyboard arrow navigation, Enter to run and Escape to dismiss; exposed it from the top bar as well.
- Added per-chat/per-profile local draft restoration, capped to 16 recent drafts and 12,000 characters each. Draft persistence is best-effort and remains local to the browser profile.
- Persisted sidebar collapse and workbench panel/tab preferences across app restarts.
- Corrected stale quick-start and README language that still described cross-provider round-robin/failover; chat requests remain pinned to the user's explicitly selected provider and model.
- Added regression coverage for command palette keyboard navigation, workspace preferences and draft persistence. Updated release metadata and Windows dependency marker to 0.8.8.

## 0.8.7 — 2026-11-08

- Completed a 30-role specialist audit of the 0.8.6 source and fixed additional issues found.
- Explicit connection key pools now remain scoped to the key IDs assigned to that connection; unselected provider keys are not discovered as implicit backups.
- Wired the UI's context-window setting into chat requests and model-aware conversation-history compaction. The budget remains a conservative character estimate, not an exact tokenizer.
- Capped the combined activated-skill prompt context at 12,000 characters, with truncation disclosure, preventing multiple large skill packs from overwhelming the prompt.
- Added regression coverage for direct browser risky-link guards, side-effect-aware retry protection, browser shutdown, full connection-consent fingerprinting, old-chat model changes, selected-key scoping, context limits, and skill prompt budgets.
- Updated the app version, API user agent, Windows setup marker, README and quick start to 0.8.7.
- Replaced an outdated test expectation that allowed automatic discovery of unselected backup credentials with the stricter selected-key-only contract.

# Changelog
- Added AI Horde as an optional, image-only free community provider. It supports anonymous `0000000000` access, active model discovery, queued generation/polling, bounded safe image downloads, and optional registered free keys for better queue priority.

## 0.8.6 — 2026-11-08
- Removed implicit active-model recovery: Spaceline no longer selects the first enabled provider when the saved active selection is missing or disabled.
- Added explicit permission prompts for connection/model switches, model-ID updates, and opening a conversation tied to a different model.
- Pinned chat requests to the approved active connection and exact configured model ID; the backend rejects mismatches before persisting or sending the prompt.
- Clarified that key-pool credential retries are scoped to the same provider/model and do not switch model routes.
- Added deep green-charcoal workspace styling, Space Grotesk/Inter and Geist Mono font stacks, translucent borders, premium floating controls, and a subtle accessible cursor halo.
- Aligned app version, user-agent, setup marker, README and tests.

## 0.8.4 — 2026-11-08
- Replaced the previous forest-filled buttons with a near-black glass visual system and elevated floating pill/circle action controls.
- Added layered depth/shadows, warm brass micro-accents, subtle hover lift and pressed states across primary/secondary actions, icon controls, composer actions, browser shortcuts, model checks and chat deletion.
- Refined the base canvas/sidebar/topbar, modal, composer, form fields, provider cards, suggestion surfaces and browser command panel to match the premium black direction.
- Preserved visible keyboard focus and reduced-motion behaviour.
- Updated app version, provider user-agent, Windows environment marker and release documentation.

## 0.8.3 — 2026-11-08
- Fixed model-picker selection so a model that failed the latest full access check cannot remain silently selected; when models passed, the picker defaults to a confirmed working choice.
- Added a manual model-ID test path even after a bulk scan or when no bulk scan has been run. Unlisted IDs must pass a generation probe before Spaceline lets the user select them; successful manual probes persist with the account fingerprint.
- Bulk model verification now reports safe failure categories (missing/invalid key, billing, model/account access, missing model, quota, provider outage, timeout and connection errors) without exposing raw provider diagnostics. Quota, billing and outages are explicitly described as inconclusive rather than proof that a model is unsupported.
- Persisted failure categories with verified model results so the diagnosis remains visible after a refresh; model verification remains scoped to the provider, endpoint, auth mode and saved key pool and expires after 24 hours.
- Fixed active-provider recovery when the previously selected connection has been disabled; Spaceline now selects and persists the next enabled connection instead of leaving the composer pointed at a disabled profile.
- Corrected the premium modal theme to target the actual `.modal` element, completed the green-charcoal/brass surface treatment across project editor, terminal, browser, workbench and artifact views, refined system font fallback/typography and improved collapsed-sidebar branding.
- Added regression tests for model failure categories, missing-key classification, manual model verification/persistence, disabled active provider recovery and actual modal styling. Updated the Windows setup marker and application version for a clean 0.8.3 upgrade.

## 0.8.2 — 2026-11-08
- Fixed the embedded-browser startup gap: `start.bat` now checks for the actual Playwright-managed Chromium executable and automatically installs it when missing, including when upgrading an existing `.venv`.
- If Chromium download is blocked by the network, the launcher gives the exact recovery command but continues starting the rest of Spaceline; the Browser panel reports the remaining limitation clearly.
- Kept the right-side Browser command bar accessible from the chat toolbar. It controls the separate Spaceline Chromium profile, not the user's everyday Chrome session/cookies.
- Added a release-contract regression test for the Windows Chromium check/install path.

## 0.8.1 — 2026-11-08
- Added a compact animated **Thinking** label with a subtle shimmer; reduced-motion preferences are respected.
- Added provider-level **Test all models** with streamed per-model progress and a final working-only list. Each listed model gets a minimal generation probe; unavailable model IDs are hidden from the usable-model set and summarized as a count. Multi-key profiles may try alternate keys after authorization/permission denials. Provider quota or charges may apply.
- Ensured the bulk-test endpoint continues after unexpected SDK/transport exceptions, hides raw exception diagnostics, and completes the stream with a reliable summary. Fixed the test placement so pytest actually collects the bulk-verification regression tests.
- Added a right-side Browser command bar beside chat and expanded safe element actions: click links/buttons/tabs/menu items, fill non-sensitive text fields, select ordinary dropdown options, check/uncheck checkboxes, hover, scroll, read and navigate history.
- Exposed the same browser controls to tool-capable research/thinking models, with safety blocks for credentials, payment fields, form submission, purchases, messaging and destructive/account actions.
- Added a browser-command busy state, corrected the Customize browser capability copy, and added a regression check against literal empty button templates.
- Updated README and Windows quick-start instructions. Versioned the setup marker so an existing 0.8.0 environment refreshes dependencies on first launch of 0.8.1.

## 0.8.0 — 2026-11-08
- Added local text extraction for PDF, DOCX, XLSX, PPTX, CSV/TSV and common text/source files, with bounded sizes, warnings for scanned/image-only content, and no macro/script execution.
- Added document upload, project document preview, Ask AI about this file, and project-wide phrase search; read-only project tools are available in Cowork/research modes while writes and command execution remain Code-mode only.
- Expanded built-in skills to 28 domains, including planning, math tutoring, interview coaching, test engineering, backend architecture, DevOps, visualization, technical writing, cloud learning and accessibility review.
- Masked common secret assignments and recognizable API/token patterns in file context before provider sharing; filtered sensitive paths from agent file listings and blocked binary files from raw text readers.
- Updated PyInstaller bundling for built-in skills and the document extraction/browser dependencies.
- Separated provider model discovery from live model access; added an opt-in, one-token generation probe for OpenAI-compatible, Anthropic, Gemini and Ollama APIs, with clearer access/billing/quota/key/model failure states.
- Added explicit Gemini 4 Argon paid-tier metadata based on Google's current Gemini API pricing documentation; free-tier users are warned before they try it.
- Enforced HTTPS for remote provider endpoints while preserving HTTP for local loopback services; added endpoint transport indicators.
- Added confirmed Delete chat actions in the sidebar, chat search and active conversation toolbar; deleting a chat cascades to its messages.
- Hardened AI project-file tools against common credential/private-key paths; blocked browser requests to non-public destinations and disabled shell interpretation for the project terminal allowlist.
- Stopped automatic key/provider failover after a successful project write or any verification-command execution to avoid repeating side effects.
- Updated the test suite for model probes, access error classification, endpoint transport, chat deletion, protected project paths and no-replay behavior.

## 0.7.3 — 2026-11-08
- Added OpenAI GPT Image and Gemini 3.1 Flash Image generation through saved provider connections; generated assets are stored locally in `Generated Images`.
- Added per-key API connection testing against the provider model endpoint. Tests report authentication/model-list results without exposing credential values.
- Enabled simultaneous provider connections with round-robin selection across new chat turns, per-connection saved-key rotation, and sequential failover on retryable provider errors before content is emitted. Requests are not duplicated across all providers.
- Added richer model catalogue metadata and OpenRouter's account-preference filtered catalogue attempt, with fallback to the general catalogue for keys that are not authorized for the management-only endpoint.
- Added OpenRouter paid/free pricing labels and a true `:free` variant filter; $0-listed routes are not advertised as guaranteed account-accessible.
- Restricted Gemini image generation to the currently documented `gemini-3.1-flash-image` model.

## 0.7.2 — 2026-11-07
- Added direct Chat, Web Search, Deep Think and Deep Research buttons in the composer, synchronized with the ＋ tools menu and task-mode routing.
- Added a 36px canvas-based cyan/amber thinking HUD below the Spaceline assistant label while requests are active, with tool status text and clean teardown on success/failure.
- Respects `prefers-reduced-motion`; animation is local and does not add external assets or network requests.


## 0.7.1 — 2026-11-07

- Added a ChatGPT-style plus menu beside the composer for modes, browser/research, UI and motion references, code/preview/files, skills, plugins, connectors and providers.
- Added bounded text/code attachments with explicit provider-sharing notice.
- Kept image generation disabled until a working image provider integration exists.


## 0.7.0 — 2026-11-07
- Added Chat, Web Search, Deep Think and Deep Research task modes with automatic browser-tool routing for research modes.
- Added a Manus-inspired left navigation / centre conversation / right live-workbench layout.
- Added Browser, Preview, Code, Files and Activity workbench tabs, plus design-system, motion, template and prompt-reference shortcuts.
- Added browser search, page-link extraction and a protected browser screenshot endpoint.
- Integrated project HTML preview and code editing into the chat workbench.
- Deferred image generation to a later release to prioritize core agent workspace reliability.

## 0.6.1
- Fixed unpaginated OpenAI-compatible provider model listing (including Groq) so the client no longer guesses a next cursor when the server did not signal another page.
- Follow explicit next-cursor metadata when present without `has_more`; an explicit `has_more: false` stops pagination.
- Expanded regression coverage for model catalog pagination and no-pagination provider responses.

## 0.6.0
- Added a searchable model picker opened by the **Models** button in chat. The picker fetches the provider's live catalogue, supports a separate **Refresh models** action, and accepts manual model IDs for gateways without model discovery.
- Added bounded cursor/page-token model pagination for OpenAI-compatible endpoints, Anthropic and Gemini, with parsing for common `data` and `models` response shapes.
- Added per-connection authentication modes for OpenAI-compatible providers and gateways: Bearer, `X-API-Key`, `api-key`, or no authentication. Native provider authentication remains unchanged.
- Fixed FreeLLM key alias grouping for labels including `FreeLLM`, `FreeLLM API`, and `FreeLLM API (local gateway)`.
- Added actionable FreeLLM 401 diagnostics that name the endpoint host, auth mode and number of attempted keys without revealing secrets.
- Added a backward-compatible SQLite migration for connection authentication mode and tests for migration, key matching, auth headers, pagination and picker controls.


## 0.5.0
- Added a compact provider + model switcher directly above the chat composer, plus one-click model discovery/refresh and saved model selection.
- Added ordered multi-key pools per provider connection. Spaceline retries another saved key after 401/403 and promotes the first key that succeeds.
- Improved authentication errors with practical 401/403/404/429 guidance while keeping upstream response bodies and API secrets out of the UI.
- Added a persistent, isolated Chrome session with page inspection and safe link-following tools; browser-intent chat requests can call it automatically.
- Added native function/tool-call loops for OpenAI-compatible APIs, Anthropic Claude, Gemini and Ollama. Code mode can inspect/read/write within the selected project and run an allowlist of test/build checks.
- Added built-in skill packs and Claude-compatible `SKILL.md` import. Matching skills are automatically attached to relevant requests.
- Fixed the missing browser module and profile key-pool persistence APIs from the previous source bundle.
- Added Playwright to the setup requirements and expanded the test suite.

## 0.4.1
- Added a named provider preset catalog for OpenAI, NVIDIA NIM, Groq, OpenRouter, DeepSeek, Kimi / Moonshot, Together AI, Fireworks, Cerebras, Mistral, SambaNova, xAI, Perplexity, DeepInfra, Qwen, Hugging Face, Novita, Cohere, Anthropic, Gemini, FreeLLM and local OpenAI-compatible servers.
- Added automatic provider base URL selection, editable endpoint overrides, and provider dropdowns for API-key labeling.
- Added keyless local profiles for LM Studio, vLLM, LocalAI and llama.cpp.
- Kept provider requests on native Anthropic/Gemini/Ollama adapters or the OpenAI-compatible streaming adapter as appropriate.


## 0.4.0 — 2026-11-06
- Rebuilt the local UI around a Claude-inspired charcoal workspace shell with Cowork / Code modes.
- Added persistent conversation history and search in SQLite.
- Added multiple named provider profiles, multiple independently saved API keys, and active-model selection.
- Added streaming adapters for Anthropic Messages, Google Gemini, OpenAI-compatible gateways (including FreeLLM-style endpoints), and Ollama.
- Added source-aware project context with limited file excerpts, dependency filtering, and common credential-pattern redaction.
- Added File Explorer and VS Code project launch actions; excluded common dependency/build folders from the file tree.
- Preserved project folders, code editor, HTML preview, terminal, artifact vault, and Windows Credential Manager key storage.
- Fixed streaming error display and connection-draft handling; added provider, chat, source context, key vault, and workspace tests (43 passing).

## 0.3.0
- Added OpenAI-compatible and Ollama provider adapters, connection tests, model discovery, and streamed chat.
- Added persistent provider settings and API key references.
- Updated workspace interface theme.

## 0.2.1
- Added Windows executable launcher and PyInstaller build recipe.

## 0.2.0
- Added API key vault and local AI Studio foundation.


