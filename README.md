# Spaceline 0.9.6

## Download, installation, and Windows security

**Windows download:** get the current installer from the [Spaceline GitHub Releases page](https://github.com/srijanmuddam16-hub/spaceline_workspace/releases). The current published release is **v0.9.6** and includes `Spaceline-Setup-0.9.6.exe`. Follow [Windows installation](INSTALL_WINDOWS.md) for setup details.

**Important security notice:** the currently published EXE installer is not code-signed. Windows Smart App Control may block an unsigned installer when its reputation service cannot verify it. GitHub hosting does not remove that warning, and Windows does not provide a per-app Smart App Control exception. Do not disable Windows security or install a certificate from an untrusted source to work around this. We are evaluating trusted, no-cost distribution/signing routes; until one is approved and implemented, users whose Windows device blocks the installer should not attempt to bypass the protection.

**Code signing policy:** Spaceline's current v0.9.6 Windows installer is unsigned. No third-party signing provider has been approved or used for this release. Any future signed release will identify the signing provider and provide signature-verification instructions here and on its release page.

**Project integrity:** download releases only from the repository linked above. Review the source and release notes before installing. Never share your Firebase service-account credentials, OAuth client secrets, API keys, or local `.env` file in an issue, public commit, or release.


## Login and Firebase repair

- Added the supplied Spaceline SVG mark to the sign-in and workspace branding.
- Rebuilt the login route with a stationary glass card, keyboard-accessible email/password fields, account creation, password reset, password visibility controls, and a remember-me choice backed by Firebase persistence.
- Google and GitHub sign-in use Firebase popup authentication and fall back to the Firebase redirect flow when the browser blocks a popup. Email/password supports account creation, sign-in, and password reset. It remains independent of the embedded Chromium profile.
- The login background uses a low-motion field of programming fragments. It respects `prefers-reduced-motion`; the card itself has no position or entrance animation.
- Missing Firebase web settings now identify the required `.env` variables without exposing configuration values. Enable **Google**, **GitHub**, and **Email/Password** in Firebase Authentication. Configure a GitHub OAuth App with Firebase’s `__/auth/handler` callback before using GitHub sign-in.

## First-open landing page and sign-in

The first screen is a responsive Spaceline introduction with Google, GitHub and email/password sign-in. It is shown to signed-out users; after Firebase restores or completes authentication, the existing workspace loads. GitHub requires a Firebase GitHub provider configured with the GitHub OAuth app callback.

## 0.9.5 workflow update

- Web Search and Deep Research now use direct HTTP search and page reading, not embedded Chromium. Initial search angles run concurrently and the selected model continues with follow-up source inspection and queries. Research progress remains in chat Activity.
- The embedded Playwright Chromium workbench is preserved for explicit interactive-browser requests. It does not auto-open when a user asks for research, and “do not open the browser” is treated as a negative instruction.
- Assistant replies have exactly one icon-only note-copy button below the full response. Legacy Copy / Copy markdown / Copy all / Copy code buttons are removed, including stale controls inserted after initial render. The button copies the original complete Markdown.
- Review can create a separate Git worktree branch/folder for an isolated task, list existing Spaceline worktrees, and switch the active project context to one. Create from committed HEAD; uncommitted changes are not copied.
- Startup scans ports 8765–8799 and opens the actual port for the new process; assets are versioned 0.9.6 and the home page is not cached.


A local-first AI and coding workspace for Windows. Spaceline combines a ChatGPT-style conversation flow, explicit provider flexibility and a Codex-style local code workspace. It runs from VS Code or `start.bat`; the launcher selects the first available loopback port in `8765–8799` and prints the exact local URL.

## Firebase sign-in and setup

See [FIREBASE_SETUP.md](FIREBASE_SETUP.md) for detailed provider setup. Copy `.env.example` to `.env` in the project root, then fill the Firebase Web API key, App ID and sender ID from Firebase Console → Project settings → General → Your apps. The supplied template already includes the project ID (`spaceline-87f04`) and auth domain (`spaceline-87f04.firebaseapp.com`); verify those match your Firebase project.

Enable **Google**, **GitHub**, and **Email/Password** in Firebase Authentication. GitHub sign-in also needs a GitHub OAuth App whose authorization callback is `https://spaceline-87f04.firebaseapp.com/__/auth/handler`, with its Client ID and Client Secret entered in Firebase's GitHub provider settings. Never put the GitHub Client Secret in `.env`, frontend code or a ZIP.

Configure Firebase Admin Application Default Credentials for the same project in PowerShell with `gcloud auth application-default login`. The account must have permission to verify Firebase ID tokens. Do not put a service-account private key in the project or its release ZIP. Spaceline fails closed when Firebase Admin verification is unavailable.

Each verified Firebase UID receives its own local workspace directory under `.spaceline-users`; this includes project files, SQLite state, API-key metadata, generated images, imported skills and the embedded browser profile. The first account to sign in after upgrading claims the legacy installation-wide workspace. Back up the existing `Documents\Spaceline` folder before the first sign-in after upgrading, and use the same Firebase account that owns the old workspace. Later accounts receive separate workspaces. This is local filesystem isolation, not cloud synchronization or protection from other Windows users who can read the same Windows profile.

The first-open landing screen is displayed while signed out. After Firebase restores or completes authentication, the existing Spaceline workspace is loaded. The embedded Chromium browser remains separately signed in and does not inherit your Google or GitHub login.

## Windows installation

1. Extract the complete ZIP into a writable permanent folder (for example, `%LOCALAPPDATA%\Spaceline`).
2. Install Python 3.10 or newer and ensure `python` or the Windows `py` launcher is available.
3. Copy `.env.example` to `.env` and fill the Firebase Web values described above.
4. In PowerShell, run `gcloud auth application-default login` for the Firebase project. Install the Google Cloud CLI first if it is not already installed.
5. Run `start.bat`. It creates `.venv`, installs `requirements.txt`, downloads the Playwright Chromium engine if needed and starts the local server. Keep its window open.

## What changed in 0.9.0

- Added saved **Personalization** controls for response tone, detail, formatting, problem-solving style, user context, and bounded custom instructions. Preferences are stored in the local workspace and injected into chat instructions without modifying provider/model routing.
- Added a more structured **Deep Think** workflow for decomposing problems, identifying assumptions, comparing trade-offs and verifying conclusions; it no longer forces web browsing for questions that do not need current sources. Web Search and Deep Research use the direct HTTP research flow introduced in 0.9.5.
- Added a Codex-style split editor with a live HTML preview beside the source, delayed auto-save, explicit Save, preview refresh, unsaved status and Ctrl+S support. Edits are saved through the existing protected project API before the preview refreshes.
- Added a top-bar Preview shortcut and cache-busted preview refreshes.
- Changed the interface to a black, white and neutral-gray monochrome theme while preserving natural colors inside user-generated preview and image content.
- Replaced all message/code copy toolbars with one icon-only note action beneath each completed assistant reply. It copies the original full Markdown response, including code blocks and prompts; terminal output copying remains separate.
- Web Search and Deep Research used a first live search through Spaceline’s private headless Chromium session in the 0.9.0 release; 0.9.5 replaces this transport with direct HTTP retrieval to avoid starting Chromium for research. The model can continue with targeted searches and page reads (8 tool rounds for Web Search; 14 for Deep Research); activity stays in the chat Activity panel unless the user explicitly opens Browser.
- Added a read-only Git Review workbench tab showing redacted tracked-file status and unstaged diff for the selected project. It does not stage, commit, reset or modify the repository.
- Changed the Windows launcher to scan ports 8765–8799 and open the exact URL for the new process, preventing an older Spaceline instance on 8765 from appearing to be the new release. Versioned JS/CSS assets as 0.9.2 and disabled caching for the main HTML response.
- Preserved existing provider selection consent, exact model routing, Windows Credential Manager key storage, image generation, local workspace tools and Smart App Control compatibility.

## What changed in 0.8.9

- Added a dedicated Image Studio destination in the sidebar and persistent top-bar launch button, opening a premium standalone image-creation workspace independent of chat.
- Added sequential **Test all saved keys** in the API key vault; each saved key is checked against its provider model-list endpoint without revealing credentials. This verifies authentication/catalog access only.
- Expanded Image Studio with persistent local image history, prompt/model metadata, gallery refresh, download and delete actions.
- Added provider-aware aspect-ratio controls, including widescreen and vertical formats, with OpenAI dimensions mapped to supported custom sizes.
- Added verified Gemini image model choices: Gemini 3.1 Flash Image, Gemini 3.1 Flash Lite Image (1K output only), and Gemini 3 Pro Image. Added OpenAI GPT Image 2.5/2.6 Flare and Sunburst options.
- Added Eden AI as an optional Image Studio provider. Spaceline retrieves the available image-model catalog from the user's Eden AI account and uses its exact `provider/model` identifier with the V3 image-generation endpoint.
- Added AI Horde as a free, image-only community provider. It supports anonymous access with the published `0000000000` key (no saved key required), active-worker model discovery, asynchronous queue polling, HTTPS result downloads, and optional registered free keys for better queue priority.
- Kept legacy 0.8.x `size` requests compatible while the updated UI uses explicit aspect ratios.
- Merged the FastAPI lifespan shutdown hotfix and versioned the Windows dependency-ready marker to 0.8.9.
- Added regression coverage for image model/resolution routing, persistent image history, local-session authorization, and image deletion.


## What changed in 0.8.8

- Added the searchable command palette (`Ctrl+K`) for navigation, new chats/projects/artifacts, browser workbench, provider settings, skills and workspace view controls.
- Added bounded local draft restoration per chat and selected provider connection; drafts are stored in this browser profile only.
- Saved sidebar collapse and right-workbench layout preferences between app restarts.
- Refined the classic premium green-charcoal visual design with restrained brass details, clearer typography, calmer shadows, keyboard focus and reduced-motion support.
- Corrected quick-start and historical summary language that could suggest automatic cross-provider routing; explicit provider/model selection remains authoritative.
- Fixed active model selection so Spaceline never silently picks the first enabled connection when no explicit selection exists. The server reports `explicit_selection_only`; the composer requires a real selected connection before sending.
- Added a clear model-switch permission dialog for connection changes, model-ID changes, and opening an older conversation that used a different model. Declining preserves the current selection.
- The chat request sends the exact selected profile ID and model ID; the backend validates both before writing the user message or contacting a provider. A mismatch is rejected rather than rerouted.
- Kept provider/key-pool rotation scoped to credentials for the same selected profile; it cannot choose a different provider or model.
- Refined the theme into a deep green-charcoal glass system (`#121614`, `#181C1A`) with translucent borders, Space Grotesk/Inter and Geist Mono font stacks, raised floating controls, and a subtle interactive cursor halo that respects reduced-motion settings.
- Updated setup/version markers and release metadata to 0.8.8.
- Restricted each connection to the exact saved API-key IDs assigned to it. Spaceline no longer pulls unselected provider keys into a hidden fallback pool; only explicitly attached keys can rotate after an authentication failure.
- Connected the Model & context setting to the actual chat payload. When a context window is known or manually configured, older conversation history is compacted to a conservative context-derived budget; this is a character/token estimate, not an exact tokenizer.
- Capped all automatically activated skill instructions together at 12,000 characters and disclose when skill content is truncated, preventing multiple large imported skills from flooding a prompt.
- Hardened direct browser link clicks against destructive/account labels, marked browser state-changing actions as side effects so failed agent tasks are not replayed after a successful action, and close the persistent browser during FastAPI shutdown.
- Added regression coverage for the 30-role audit findings and replaced an obsolete test that expected Spaceline to automatically use an API key not assigned to the selected connection.

- Refined the interface with a deep green-charcoal glass palette, warm brass accents, elevated pill/circle controls, consistent panel surfaces, Space Grotesk/Inter and Geist Mono font stacks, and a subtle interactive cursor halo. Keyboard focus and reduced-motion preferences are respected.

## What changed in 0.8.3

- Fixed first-run browser setup: `start.bat` checks whether the Playwright Chromium binary is present and automatically runs `python -m playwright install chromium` when it is missing. This also repairs existing virtual environments. If the download fails, Spaceline still starts and the launcher prints a manual recovery command.
- Fixed model selection state: verified models persist for 24 hours against a provider/endpoint/auth/key-pool fingerprint; changing provider clears the old model ID; a disabled active connection is replaced by an enabled one.
- Added provider failure categories to full model scans (missing/invalid key, billing, permission, model not found, quota, timeout and provider outage) so a temporary provider problem is not misreported as an unsupported model.
- Added a manual **Test ID** path before or after a bulk scan. An unlisted model is added to the usable list only after its own generation probe succeeds, and successful manual checks persist across restarts; failed models remain unselectable.
- Added a narrow OpenAI-compatible compatibility retry for endpoints that explicitly reject `max_tokens` and require `max_completion_tokens`; access, quota and billing errors are never retried using that fallback.
- Refined the visual system with Windows-native variable-font typography, clearer heading hierarchy, calmer forest-graphite surfaces, improved modal/forms, provider cards, code/workbench surfaces, focus states and reduced-motion support.

## What changed in 0.8.1

- Added a small shimmer to the inline **Thinking** word while the assistant is processing; reduced-motion preferences are respected.
- Added **Test all models** below each provider connection in Customize. It runs a minimal generation probe against every model ID exposed by that connection, streams progress, and shows only IDs that passed for the saved key pool at test time. Unavailable IDs are counted but their individual errors are hidden. This may use provider quota or incur charges; a connection with multiple saved keys may try another key after an authorization/permission denial.
- Updated the model chooser after a complete bulk test so only passing models are available to select; the catalogue is not treated as an entitlement check until then.
- Added a right-side Browser command bar next to chat. It can navigate/search, click ordinary links/buttons/tabs/menu items, fill non-sensitive text fields, select dropdown options, check/uncheck ordinary checkboxes, hover, scroll, read, and move backward/forward.
- Added matching browser control tools for tool-capable Deep Think/Deep Research/Web Search models. The browser remains a separate Spaceline Chromium profile, not the user’s existing Chrome window/session.
- Added busy-state protection for browser commands and expanded regression checks for command safety, hidden failed models, and empty button markup.
- Corrected the browser capability description in Customize and the setup guide.

## What changed in 0.8.0

- Added project and upload document reading for PDF, DOCX, XLSX, PPTX, CSV/TSV and common source/text formats. Project search can find matching passages; a selected document can be sent to chat for analysis.
- Read-only project file tools now work in Cowork and research modes when a project is selected; file-writing and command-running tools remain restricted to Code mode.
- Added 10 more skill packs (28 built-in skills total) across planning, math, interviews, testing, backend architecture, DevOps, visualization, technical writing, cloud and accessibility. Imported `SKILL.md` packs remain supported.
- Common credential assignments and recognizable provider tokens are masked from uploaded/project-file content before it is sent to an AI provider. Protected credential/key paths are excluded from file listings and agent access.
- Added safe, styled document previews and project-wide file search; binary documents no longer pass through the raw text editor.
- Updated the Windows PyInstaller spec to bundle the built-in skills directory and document/parser/browser modules.
- Added regression tests for read-only routing, document parsing and safety, secret masking, protected file paths, skills selection and frontend wiring.


- Separated **model discovery** from **model access**. Provider `/models` endpoints only prove that a model ID was listed; each model now has an opt-in **Test access** request using the provider's real generation protocol (OpenAI-compatible, Anthropic, Gemini or Ollama). The one-token probe can incur a small charge and only verifies the selected key/account at test time.
- Added paid-tier metadata for Gemini 4 Argon. Google's current Gemini API pricing page explicitly marks `gemini-4-argon` unavailable on the Free tier. Enable API billing for the Google AI Studio project before testing; a Gemini consumer-app subscription is not API billing.
- Remote provider endpoints must use HTTPS. Plain HTTP is accepted only for localhost/loopback services such as Ollama and local gateways; provider cards show the transport state.
- Added permanent **Delete chat** actions in the recent-chat sidebar, chat search results and current conversation toolbar. Confirmation is required and deleted messages are cascaded by the database.
- Hardened AI project tools against reading/writing credential paths and private-key files; tightened browser request guards against local/private-network destinations; project terminal commands use an executable allowlist with `shell=False`.
- Prevented automatic provider/key failover from replaying a task after a project file write or a verification command has executed. A failed check still counts as an executed side effect.

## What changed in 0.7.3

- Added a model image-generation adapter for OpenAI GPT Image and Google's Gemini 3.1 Flash Image. Generated files are saved locally under `Generated Images`; cloud image requests are billed or quota-limited by the selected provider.
- Added a per-key **Test connection** action in the API key vault. It validates each saved key against that provider's authenticated model-list endpoint without returning the secret to the UI.
- Kept multiple provider connections available for explicit selection. A chat is sent only to the active connection and exact model selected by the user. Provider/model failures stop with a visible error; Spaceline never automatically rotates to a different connection or model. Credential retry is limited to keys explicitly assigned to that same connection and does not change the provider/model route.
- Improved provider model discovery. Each connection is queried with its saved API key; OpenRouter first attempts its account-preference/guardrail-filtered model endpoint and falls back to the general catalogue when the management-key-only endpoint is unavailable.
- Added provider pricing labels for OpenRouter, including a filter for `:free` variants. Models listed by a provider are not a guarantee of account entitlement, remaining quota, or billing eligibility; the provider still checks access when a request is made.
- Restricted Gemini image generation to the documented `gemini-3.1-flash-image` model rather than advertising unverified legacy image model IDs.

## What changed in 0.7.2

- Added four always-visible task-mode shortcuts inside the composer: Chat, Web Search, Deep Think and Deep Research. They share the same mode state and backend routing as the ＋ menu.
- Added a compact 36-pixel cyan/amber Spaceline HUD indicator beneath the assistant label while a model request is running. Its status changes as browser/tool work proceeds and while the model streams a reply; it is removed on completion or error.
- The HUD uses a small canvas rather than a full-screen animation and respects the operating system's reduced-motion preference.

## What changed in 0.7.1

- Added one ChatGPT-style **＋ Tools** menu beside the composer, with mode switching, browser, template/motion references, project code/preview/files, skills, plugins, connectors and provider management.
- Added message attachments for PDF, DOCX, XLSX, PPTX, CSV/TSV and text/code files. Up to 3 files (20 MB per uploaded file); extracted content is capped at 15,000 combined characters per message and is sent to the selected provider. Do not attach secrets.
- Kept image generation visible as unavailable until an image provider is actually integrated.

## What changed in 0.7.0

- Added four task modes above chat: **Chat**, **Web Search**, **Deep Think**, and **Deep Research**. Deep Think automatically activates the structured research workflow and browser tools; it does not silently change your selected provider or model.
- Added a Manus-inspired three-part workspace: navigation/projects on the left, conversation and task controls in the centre, and a right-side live workbench.
- The workbench includes **Browser**, **Preview**, **Code**, **Files**, and **Activity** tabs. It can be collapsed, resized responsively through the layout, and opened automatically by research modes.
- Added a browser address bar and quick links for shadcn/ui, Motion, React Bits, Aceternity UI, Magic UI, Vercel templates, Tailwind, Awwwards, and prompt-writing references.
- Added a live browser screenshot and readable-page panel using the existing persistent Playwright-controlled Chromium profile. Browser snapshots now include visible HTTP/HTTPS links so the model can inspect sources.
- Added a browser search tool and automatic browser-tool routing for Web Search, Deep Think, and Deep Research. Research prompts instruct the model to compare sources and cite the URLs it actually opened.
- Added a protected local screenshot endpoint and right-panel HTML preview / editable project code integration. Existing project file, chat, provider, key-vault, and SQLite data formats are retained.
- Image generation is intentionally not wired in this release; browser research, code editing, and live preview are the priority foundation.

## What changed in 0.6.1

- Fixed OpenAI-compatible model discovery so an ordinary unpaginated `data` response (including Groq) does not trigger a bogus second-page request based on the last model ID.
- Followed explicit `next_cursor` responses even when a gateway omits `has_more`, while respecting an explicit `has_more: false`. Added regression coverage for both cursor styles and unpaginated responses.
- The chat **Models ↻** action opens a searchable live catalogue; **Refresh models** fetches it again. The list includes every model ID returned by that endpoint across supported cursor/page-token pages (bounded to 50 pages), not a global directory of every model sold by a provider. Manual IDs remain available when discovery is disabled.
- Re-ran provider key fallback, FreeLLM auth-mode, API-key pool and app migration coverage after the pagination fix.

## What changed in 0.6.0

- Replaced the tiny inline model dropdown with a clear **Models** button in the chat composer. Clicking it fetches the selected provider's live model catalogue and opens a searchable list; the dialog also has its own **Refresh models** button and a manual model-ID fallback.
- Model discovery now follows cursor/page-token pagination for OpenAI-compatible model endpoints, Anthropic, and Gemini (bounded to 50 pages), so providers that paginate do not silently show only the first page. Gemini, Anthropic, Ollama, and common OpenAI-compatible `data`/`models` response shapes are parsed separately.
- Added per-connection gateway authentication modes: `Authorization: Bearer`, `X-API-Key`, `api-key`, or no auth. Anthropic, Gemini, and Ollama keep their native authentication.
- Fixed FreeLLM key-label matching. Keys saved under `FreeLLM`, `FreeLLM API`, or `FreeLLM API (local gateway)` can be associated with a `freellm` connection and are eligible for the configured primary/backup key pool.
- Expanded safe 401 diagnostics for FreeLLM to show the endpoint host, auth mode and number of attempted saved keys, without exposing credential values or upstream response bodies.
- Added a SQLite migration for `provider_profiles.auth_mode`; existing 0.4.x/0.5.x data and chats are retained and old profiles default to Bearer authentication.

## What changed in 0.5.0

- Simple provider and model selectors directly in the chat composer. Switch a saved connection, refresh its model list with ↻, and select the model without reopening settings.
- Multiple API keys can be attached to one connection as an ordered primary/backup pool. On 401/403 before any response text is received, Spaceline tries the next saved key and promotes the key that works.
- Clearer HTTP 400/401/403/404/429 troubleshooting while keeping upstream error bodies and credentials out of the UI.
- A separate, persistent headless Chromium browser controlled by Playwright; it does not use your everyday Chrome profile or signed-in browser session.
- Six built-in skills plus import of one or more Claude-compatible `SKILL.md` files; relevant skills are selected automatically.
- Code-mode agent tools can inspect and edit files in the selected project and run an allowlist of verification commands.

## Provider catalog (0.4.1)

- Expanded the provider selector with named presets for OpenAI, NVIDIA NIM, Groq, OpenRouter, DeepSeek, Kimi / Moonshot, Together AI, Fireworks, Cerebras, Mistral, SambaNova, xAI / Grok, Perplexity, DeepInfra, Qwen / DashScope, Hugging Face, Novita, Cohere, Anthropic, Gemini, FreeLLM, Ollama, LM Studio, vLLM, LocalAI and llama.cpp.
- Presets automatically fill the provider's common API base URL. The URL remains editable for regional endpoints, proxies, private gateways, Azure deployments, and future providers.
- Native API transports remain used for Anthropic, Gemini and Ollama. Other cloud presets use the OpenAI Chat Completions-compatible streaming adapter; provider-specific features and model availability can differ.
- API key entry now uses a provider selector with a custom label option. Multiple keys can be stored for each service.

## What changed in 0.4.0

- Claude screenshot-inspired charcoal interface, with Cowork / Code modes and sidebar navigation for New, Search, Projects, Artifacts, Scheduled, and Customize.
- Persistent conversations in local SQLite. Chats remain available after closing and reopening the app.
- Multiple saved provider connections. Each connection can have its own name, provider, model, endpoint, and key reference.
- Multiple API keys per provider/account. Add separate primary, backup, gateway, or personal keys and choose which key a connection uses.
- Streaming adapters for OpenAI-compatible APIs (including FreeLLM-style gateways), Anthropic Claude Messages API, Google Gemini API, and local Ollama.
- Model discovery where the provider exposes a models endpoint; a model ID can also be entered manually for gateways that do not list models.
- Existing local project folders, file editor, HTML preview, command runner, notes/artifacts, and API key vault are retained.

## Start from VS Code (recommended)

1. Extract the `Spaceline` folder somewhere permanent, such as `Desktop\Spaceline`.
2. Open that folder in VS Code (`File → Open Folder`).
3. Make sure Python 3.10+ is installed and available in PowerShell as `python`.
4. Open the VS Code terminal and run:

   ```powershell
   .\start.bat
   ```

5. The first run creates `.venv`, installs Python dependencies, checks for the Playwright-managed Chromium engine, and downloads Chromium if it is missing. The launcher prints the exact URL after selecting an available port in the `8765–8799` range.
6. Keep the terminal running while you use Spaceline. Press `Ctrl+C` in that terminal to stop it.

You can also double-click `start.bat` from File Explorer. `run.py` is the server entry point if you prefer to run it directly after installing `requirements.txt`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

## Add your API keys and providers

1. Open **Customize → Providers & keys**.
2. Choose **Add API key**. Give the key a provider label (for example `FreeLLM`), a key name, and paste the secret.
3. Save the key. The secret value is stored in Windows Credential Manager; the browser only receives the key's label and ID.
4. Choose **Add connection**. Select the provider protocol, name the connection, choose the saved key, and enter a model ID.
5. Save the connection. In chat, choose it in the provider selector and click **Models ↻**. The live catalogue opens with search and a second **Refresh models** button.
6. Pick a model and choose **Use selected model**. You can also enter a model ID manually if the provider does not expose a catalogue.

### FreeLLM / custom gateway example

Choose `OpenAI-compatible / FreeLLM / Gateway`, use a connection name such as `FreeLLM – Qwen`, select the API key you saved with the `FreeLLM` label, and enter the base URL documented by your FreeLLM setup. For the local gateway URL previously used in your setup, the base URL is:

```text
http://127.0.0.1:31415/v1
```

Do not append `/chat/completions`; Spaceline adds that route itself. Enter the exact model ID your gateway exposes. You can add multiple FreeLLM keys and create separate profiles for different models or accounts.

For the local FreeLLM gateway, set **API authentication** to match its configuration: Bearer is the normal OpenAI-compatible default; choose `X-API-Key` or `API-Key` only if your gateway expects that header, or `No authentication` only when the gateway has auth disabled. Use the gateway's own access key if it protects the local endpoint; an upstream NVIDIA/Groq/Gemini key is not automatically the same credential.

### Provider selector presets

| Provider | Default API base URL |
|---|---|
| OpenAI | `https://api.openai.com/v1` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |
| DeepSeek | `https://api.deepseek.com` |
| Kimi / Moonshot AI | `https://api.moonshot.ai/v1` |
| Together AI | `https://api.together.ai/v1` |
| Fireworks AI | `https://api.fireworks.ai/inference/v1` |
| Cerebras | `https://api.cerebras.ai/v1` |
| Mistral AI | `https://api.mistral.ai/v1` |
| SambaNova | `https://api.sambanova.ai/v1` |
| xAI / Grok | `https://api.x.ai/v1` |
| Perplexity | `https://api.perplexity.ai` |
| DeepInfra | `https://api.deepinfra.com/v1/openai` |
| Qwen / DashScope (international) | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| Hugging Face Inference | `https://router.huggingface.co/v1` |
| Novita AI | `https://api.novita.ai/openai/v1` |
| Cohere compatibility API | `https://api.cohere.com/compatibility/v1` |
| Anthropic Claude (native) | `https://api.anthropic.com/v1` |
| Google Gemini (native) | `https://generativelanguage.googleapis.com/v1beta` |
| FreeLLM local gateway | `http://127.0.0.1:31415/v1` |
| Ollama (native) | `http://127.0.0.1:11434` |
| LM Studio | `http://127.0.0.1:1234/v1` |
| vLLM | `http://127.0.0.1:8000/v1` |
| LocalAI / llama.cpp | `http://127.0.0.1:8080/v1` |
| Custom OpenAI-compatible | Enter your own base URL |

The named cloud presets (apart from Anthropic and Gemini) use an OpenAI Chat Completions-compatible request path. This standardizes basic text streaming and model discovery, but does not promise that every vendor supports every tool, parameter, image input, reasoning option, or model. Anthropic and Gemini use their native HTTP protocols; Ollama uses its native local API. Model access, prices, rate limits and feature compatibility are controlled by each service. See vendor docs: [Groq OpenAI compatibility](https://console.groq.com/docs/openai), [OpenRouter API](https://openrouter.ai/developers), [Moonshot / Kimi configuration](https://moonshotai.github.io/kimi-code/en/configuration/providers.html), and [provider endpoint examples](https://docs.inference.net/integrations/overview).

A provider's model availability, usage limits, pricing, and supported request features are determined by that provider and your account. Spaceline does not make paid APIs free and cannot guarantee response speed beyond using a direct local-to-provider streaming connection.

## Code workspace

Select **Code** in the top-left mode switch or open **Projects**. Create a project, select a file to edit it, save changes, and preview HTML files. Open the actual project directory in File Explorer or VS Code with the toolbar actions. The bottom terminal runs commands from the selected project's root. In Cowork chat, choose a project in the composer to attach up to eight small source files (40,000 characters total) to the provider request. The app excludes common dependency/build folders, `.env` and common credential files, and redacts several common hard-coded API-token patterns. This is a convenience filter, not a guarantee that arbitrary project content contains no secrets; review projects before sharing them with a cloud provider.

The command runner executes using your normal Windows account. It is not a sandbox. Spaceline asks for confirmation before executing a command, but you should still run only commands you understand and trust.

## Image Studio

Open **＋ → Generate an image** or choose the **Images** tab in the right workbench. Select an enabled OpenAI, Gemini, Eden AI, or AI Horde connection, then choose the image model, aspect ratio, and quality/resolution. Available models are based on the provider's documented image API model IDs:

- OpenAI: `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst`, `gpt-image-2.6-flare`, and `gpt-image-2.6-sunburst` through the Images API. OpenAI supports square, landscape, portrait, widescreen, vertical, classic, social, and ultrawide presets.
- Gemini: `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image`, and `gemini-3-pro-image` through the Gemini Interactions API (`/v1beta/interactions`) using `model`, `input` and `response_format`. Flash Lite is restricted to 1K output; higher resolution choices are hidden when that model is selected. Aspect-ratio options are provider-specific.
- Eden AI: choose **Eden AI** when adding a provider connection and save your Eden API key in Windows Credential Manager. Image Studio loads the account/region-specific image catalog from `GET https://api.edenai.run/v3/images/models`, then generates using `POST https://api.edenai.run/v3/images/generations`. Model IDs must remain exactly as returned (for example, `google/gemini-2.5-flash-image`); available models and supported sizes depend on the Eden AI account and underlying provider. Spaceline leaves quality at the provider/model default because not every Eden model accepts a quality parameter. Eden AI's V3 endpoint returns OpenAI-compatible `data[].b64_json` or hosted `data[].url` results and may include provider and cost metadata. Spaceline does not automatically switch models or providers.

Image requests use the selected profile's saved key where required and are sent only to that provider. AI Horde uses its public anonymous key when no registered key is selected. Image API usage is separate from chat; OpenAI, Gemini and Eden AI can consume paid credits or quota, while AI Horde is free community compute. Generated files are saved locally in `Documents\Spaceline\Generated Images`; a sidecar JSON file stores the prompt and non-secret generation metadata. The gallery reloads the latest 100 images after app restart and supports refresh, save, and delete. Older images without sidecar metadata still appear in the gallery, but their original prompts cannot be recovered.

AI Horde (free): Add **AI Horde (Free Community Images)** under Customize → Providers & keys, leave the optional key selection empty for anonymous access, then open Image Studio and refresh the model list. Anonymous requests use the public `0000000000` key and have the lowest priority; register at https://aihorde.net/register for a free key and better queue priority. Model availability and wait time depend on online volunteer workers.

Official model references: [AI Horde integration API](https://aihorde.net/api/) · [AI Horde free image-generation guide](https://horde.stablehorde.net/docs/image/) · [OpenAI image generation](https://developers.openai.com/api/docs/guides/image-generation) · [Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation) · [Eden AI V3 image generation](https://www.edenai.co/docs/v3/llms/image-generation).

## Where your data lives

By default, projects and the SQLite workspace database live here:

```text
%USERPROFILE%\Documents\Spaceline
```

- Project files are ordinary folders inside the workspace.
- Chat history, provider profile metadata, notes, and key labels are in `.spaceline-data.sqlite3`.
- API key secret values are in the current Windows account's **Credential Manager**, not in SQLite or frontend code.
- Copying the workspace directory backs up project files and chat history, but not the secrets; add the keys again on another Windows account or PC.

Set `SPACELINE_WORKSPACE_DIR` before launching to choose a different data directory.

## Security notes

- The app binds to `127.0.0.1` only. Do not expose port `8765` to your LAN or the public internet.
- Provider requests are sent from the local Python backend. API secrets are never returned to browser JavaScript or included in chat history.
- Provider errors are deliberately sanitized so upstream response bodies cannot echo credentials into the UI. HTTP 401 errors now explain common key/provider/endpoint mismatches, and Spaceline can retry saved backup keys.
- Spaceline uses its own persistent Playwright-managed Chromium profile under the workspace directory. It runs headlessly and renders page screenshots plus readable text in the right-hand Browser panel; it does not open your everyday browser or share its cookies. The right-side Browser command bar and tool-capable models can also interact with ordinary visible links, buttons, tabs/menu items, text inputs, select menus and checkboxes, plus hover and scroll. Passwords, API tokens, payment fields, form submission, purchases, message sending and destructive/account actions remain blocked.
- The local command runner is not an OS sandbox. Treat commands as if you typed them in your own PowerShell session.
- This is a personal local workspace, not a multi-user hosted service. Do not add public authentication or bind to `0.0.0.0` without designing a proper security boundary first.

## Troubleshooting

- **Python not found:** install Python 3.10+ and reopen PowerShell/VS Code.
- **Port 8765 is already in use:** stop the other Spaceline instance or change the port in `run.py`.
- **API key vault reports it needs Windows:** the secret store uses native Windows Credential Manager.
- **FreeLLM connection fails:** confirm the gateway is running on `127.0.0.1:31415`, the base URL includes `/v1`, and the model ID matches the gateway's provider list.
- **Model discovery returns no models:** click **Refresh models** once to retry, then enter the provider's exact model ID manually if its gateway restricts or omits `/models`. A model catalogue can only show IDs exposed by that endpoint and key; it is not a global list of every vendor model.
- **HTTP 401:** verify the key belongs to the selected provider, contains no extra spaces, and matches the base URL. A FreeLLM local gateway may expect its own gateway token rather than the upstream provider key. Add another key to the same connection only if you explicitly want same-provider credential retry for the same model. Spaceline never falls back to another connection or model. It cannot make an invalid or revoked provider key valid.
- **Spaceline browser not available:** start Spaceline with `start.bat`; it checks for the Playwright Chromium engine and installs it when missing. If the download was blocked, run `.venv\Scripts\python.exe -m playwright install chromium` in the Spaceline folder, then restart. Spaceline uses its own Chromium engine, not the Chrome app already installed on Windows.
- **HTTP 404:** check the base URL and model ID. Do not include `/chat/completions` in the base URL.
- **Ollama not reachable:** start Ollama and run `ollama list` to confirm that a model is installed.

## Run the tests

Install the development test dependency once, then run the complete suite:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The suite covers storage/migrations, key handling, provider protocols and model access probes, transport security, browser destination guards, chat deletion, document extraction, secret redaction, filesystem path safety, skill selection and frontend contracts.

## Project structure

- `app/main.py` — FastAPI routes and local session protection.
- `app/ai_provider.py` — provider catalog, model discovery, streaming adapters, and tool-call loops.
- `app/browser.py` — persistent Embedded Chromium automation through Playwright.
- `app/skills.py` and `skills/` — built-in and imported Claude-compatible skill packs.
- `app/key_vault.py` — Windows Credential Manager integration.
- `app/workspace.py` — project/file operations and SQLite persistence.
- `static/` — Claude-inspired workspace interface.
- `tests/` — automated tests.
- `start.bat` — Windows setup and launcher.
- `run.py` — local server entry point.

## Reading and analyzing files

Spaceline can extract selectable text from project files or message attachments in PDF, DOCX, XLSX, PPTX, CSV/TSV and common source/text formats. Choose a project file in the Files panel to preview it, then use **Ask AI about this file**; or attach a document with the composer **＋** menu. Uploaded documents are limited to 20 MB each, up to 3 attachments, with 15,000 combined extracted characters sent per message. Scanned PDFs and image-only slides need OCR/vision, which is not built into this extractor. Spreadsheet formulas are shown with cached values if present; Spaceline does not recalculate formulas.

## Skills, browser, and workspace agent tools

- The 28 built-in skills cover coding, code review, backend architecture, API integration/testing, security, debugging, DevOps, browser/web research, document and presentation analysis, data/spreadsheet analysis, visualization, accessibility, UX, project planning, prompt engineering, technical writing, Python learning, math and interview coaching. Matching skills are loaded into the model prompt automatically.
- Import one or more Claude-compatible `SKILL.md` files from **Customize → Skills**. Imported skills are stored in `Documents\Spaceline\skills` and auto-activate when their names/descriptions/triggers match a message. Imported skill text is treated as instructions subordinate to the app's safety boundaries.
- **Browser workbench / Customize → Connectors** uses a private persistent Playwright Chromium profile. It stays inside Spaceline as a captured page preview plus readable text and does not launch another browser window or reuse normal Chrome cookies. Browser-capable models can navigate, inspect visible text, click ordinary links/buttons/tabs/menu items, fill non-sensitive text inputs, choose dropdown values, check/uncheck ordinary checkboxes, hover and scroll. Passwords, API tokens, payment fields, form submissions, purchases, message sending and destructive/account actions remain blocked.
- With a project selected, tool-capable models can list, search and read eligible source files in Cowork, Deep Think and Code, and analyze PDF/DOCX/XLSX/PPTX/CSV/TSV documents. Code mode additionally allows project-scoped writes and a fixed allowlist of verification commands. Common secret paths and symlinks are blocked; the normal developer terminal remains available with explicit confirmation and is not sandboxed.
- Browser and coding tool calls use non-streaming function-call rounds; ordinary text chat still streams. Tool use depends on the selected provider/model supporting function calling. Not every provider exposes identical features.

## Current scope boundaries

Spaceline 0.9.6 is a local-first AI workspace with **15 selectable operational modes**, persistent chats, provider profiles, verified-model access checks, 28 built-in skills plus imported `SKILL.md` packs with a combined prompt budget, document extraction, an embedded Playwright Chromium browser, protected project tools, and a right-side workbench. **Only the connection/model you explicitly select is used for chat.** A change to the active connection, provider, endpoint or model ID requires approval. The backend checks that every chat request matches the approved active profile and exact configured model ID; if it does not, the request is rejected before the prompt is sent or saved. A connection may retry credentials from its own explicitly assigned saved key pool, but those credentials are used for the same provider and model—it is not cross-provider/model routing. A provider may still apply its own aliasing or routing rules after it receives the requested model ID; Spaceline cannot control provider-side behaviour.

Architect and Review/Audit are read-only tool modes. Build, Debug/Self-Fix and Autonomous use bounded project tools according to their mode permissions. File-analysis and data-analysis modes expose read-only file/document workflows. Long chats use automatic context compaction while preserving recent turns. Spaceline creates a checkpoint before project file writes. Message copy controls include plain text, raw code and full Markdown, with terminal-output copying. Deep Research and browser actions depend on the selected model supporting function calling; providers do not all expose identical capabilities. The embedded Chromium browser uses a separate persistent Spaceline profile, not the user's already-open everyday Chrome profile or its cookies. Scanned PDFs and image-only slides still need OCR/vision, which is not built into the document extractor.

Spaceline is not a universal OAuth connector hub: services such as GitHub, Drive or Slack still need dedicated integrations. There is no general background scheduler in this build. The developer terminal is not an OS sandbox and runs with the current Windows user's permissions; AI-issued project checks use a narrower allowlist. Spaceline does not submit purchases, payments, messages or other sensitive web actions.
