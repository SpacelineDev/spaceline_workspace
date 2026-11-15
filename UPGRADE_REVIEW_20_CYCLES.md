# Spaceline 0.8.0 — 20-cycle review and hardening record

**Review target:** uploaded Spaceline 0.7.3 source bundle  
**Result:** source upgraded to 0.8.0  
**Method:** twenty sequential specialist review/fix/retest passes. These are twenty focused review cycles performed in sequence by this assistant, not twenty separately spawned autonomous agents. Each pass examined the latest working tree and carried its corrections forward.

## Cycle log

| Cycle | Specialist lens | Finding / decision | Change made or verified |
|---:|---|---|---|
| 1 | Architecture and migration | Preserve existing local data; do not replace the app with a mock or fresh scaffold. | Kept the FastAPI/SQLite architecture and added only backward-compatible migrations for existing provider profile settings. Version advanced to 0.8.0. |
| 2 | Conversation lifecycle | Delete existed at the data/API layer but was not available consistently in the UI. | Added confirmed Delete chat actions to recent chats, search results and the active conversation toolbar; active-view state is cleared after deletion. Database foreign-key cascade removes its messages. |
| 3 | Local API boundary | Mutating and sensitive local API operations must require the Spaceline local-session token. | Reviewed and retained session-token checks; regression tests cover protected reads, mutations and chat deletion. |
| 4 | API-key vault and secret handling | Key values must never be returned by settings, connection tests or chat model UI. | Kept key metadata separate from secret values; tests verify API-key tests do not return keys. Windows Credential Manager itself cannot be runtime-verified in this Linux build environment. |
| 5 | Provider model catalogue | A provider `/models` response is only a catalogue listing, not proof of account access. | Model entries now say unverified until an actual model request succeeds. Pricing/tier hints are separate from entitlement state. |
| 6 | Model access and entitlement diagnosis | Users need to distinguish bad keys, billing, quota, missing models and provider outages. | Added a small per-model **Test access** request using each provider's native generation protocol; error messages distinguish 401, 402, 403, 404, 429 and 503. The probe may incur a small provider charge. |
| 7 | Google model/tier review | Gemini 4 Argon is not accessible through the free Gemini API tier; a consumer Gemini subscription is not the same as API billing. | Added accurate paid-API-tier metadata and an explicit note/link in the model picker. The user's own project/key still needs to be tested after API billing/access is configured. |
| 8 | Transport security | Sending cloud API keys over remote plain HTTP exposes credentials in transit. | Remote provider endpoints now require HTTPS. HTTP is accepted only for local loopback services such as Ollama and the user's local FreeLLM-style gateway. UI distinguishes these states. |
| 9 | Retry and side-effect safety | Retrying a task after a successful write or executed check can duplicate side effects. | Automatic provider/key failover is stopped once a project mutation or verification command has executed, including a failed check. |
| 10 | Browser and SSRF review | Browser access to loopback, local, private, link-local, reserved and non-public DNS targets is unsafe. | Added URL validation and request guards, including redirects/subresources and DNS resolution checks. Browser is explicitly described as a separate headless Chromium profile, not the user's everyday Chrome session. DNS rebinding cannot be eliminated completely by a browser-level preflight guard; this is not an OS/network sandbox. |
| 11 | Terminal and command execution | Shell interpretation and command chaining were too powerful for an agent-facing project runner. | Removed `shell=True`; command parsing rejects shell operators/expansion and uses `shell=False` plus an executable allowlist. Clearly warns that manually run developer-terminal commands execute with the user's Windows permissions and are not OS-sandboxed. |
| 12 | Workspace path and credential access | Common credential paths, private keys and hidden dependency directories must not be available to AI tools. | Added protected-path filtering for common secret/config locations and private-key names; kept reads/searches in read-only modes and writes/checks restricted to Code mode. |
| 13 | File/document extraction | Treating binary files as UTF-8 text corrupts reads and gives the model meaningless context. | Added bounded extraction for selectable PDF text, DOCX, XLSX, PPTX, CSV/TSV and common text/source files, with size, part, page, row and output limits. No macros or embedded code are executed. |
| 14 | Spreadsheet/presentation accuracy | Excel formulas are not recalculated and image-only/scanned content is not text-extractable. | Previews disclose that cached spreadsheet values are not recalculated. Scanned PDFs and image-only slides report the need for OCR/vision rather than pretending their contents were read. |
| 15 | Secret redaction and search | Redacting direct reads is insufficient if search results still expose secret values. | Redaction now occurs before search matching and before excerpts are returned; duplicate matches are bounded per file. Added regression tests for API-key/token leakage. |
| 16 | Project file search and editor | Extensionless project files such as Dockerfile and Makefile are important source/config files; binary files do not belong in the text editor. | Added common extensionless text names and selected safe dotfiles; binary documents route to extraction/preview instead of raw text decoding. Search has an explicit no-match state. |
| 17 | Filesystem adversarial review | A symlink with a harmless filename could alias a protected file inside the project and bypass path-name checks. | Added a red-first regression test; path resolution now rejects symlink components and the file tree omits symlinked files as well as symlinked directories. This closes the tested alias path. |
| 18 | Skills and specialist coverage | The initial skill set was too narrow for document, data, test, security, UX and learning tasks. | Expanded to 28 built-in `SKILL.md` packs covering backend, APIs, coding, review, debugging, security, tests, DevOps, Python learning, data/spreadsheets, documents, presentations, visualization, browser/web research, accessibility, UX, planning, math, interviews and writing. Existing Claude-compatible skill import remains. |
| 19 | Frontend and capability-claim review | Some labels suggested universal Chrome, OAuth connectors, plugins or a scheduler that the runtime does not provide. | Reworded the browser and Integration Status pages; documented the absence of generic OAuth connector runtime/plugin marketplace and scheduler. Clarified HTTP 503 (provider unavailable) is different from remote `http://` transport being blocked. |
| 20 | Release, regression and packaging review | Release must be reproducible and the review must disclose what could not be verified. | Updated README/changelog/spec, corrected the attachment-menu limits, added `requirements-dev.txt`, versioned the launcher dependency marker for upgrades, updated the Windows EXE builder to run pytest, and ran the full suite plus Python compilation, JavaScript syntax check and capability assertions. Final suite: **207 passed, 50 subtests passed**. |

## Delivered capabilities

- Provider profiles and key pools with per-key connection checks and per-model access probes.
- Clear distinction between model IDs listed by a provider and models actually verified for a selected key/account.
- Remote HTTPS enforcement; loopback HTTP retained for local gateways.
- Chat deletion in the sidebar, search results and open conversation.
- Read-only project file list/read/search/document-analysis tools in Cowork, Deep Think and Code when a project is selected; project writes and allowlisted checks remain Code-mode capabilities.
- PDF, DOCX, XLSX, PPTX, CSV/TSV and text/source extraction; uploaded documents can be attached to chat for analysis.
- Twenty-eight built-in skills plus import of additional `SKILL.md` packs.
- Secret redaction before AI context and search excerpts; protected paths and symlink paths blocked from agent access.
- Embedded browser research using a separate headless Chromium profile.

## Important limits — not hidden

1. **Real account entitlement cannot be proven here.** No user API keys were provided to this build session. A listed model remains unverified until you run **Test access** with your saved key. The probe can be billable.
2. **Gemini 4 Argon requires a paid Gemini API tier.** Consumer Gemini subscriptions do not substitute for API billing. Check current provider pricing/availability before spending.
3. **HTTP 503 is not a transport-security warning.** It means the provider is temporarily unavailable; it does not by itself prove the key or model is invalid. Remote `http://` endpoints, by contrast, are blocked because they are unencrypted.
4. **Document extraction is not OCR.** Image-only/scanned PDFs and image-only slides need OCR/vision. Spreadsheet formulas are not recalculated; cached values, if present, are only displayed as stored.
5. **Browser protections are not network isolation.** Public DNS prechecks block common private-network SSRF paths, but a browser-level guard is not a substitute for an OS/network sandbox and cannot fully eliminate DNS rebinding races.
6. **The developer terminal is not sandboxed.** It runs with the current Windows user's permissions. Do not run untrusted scripts or commands. AI-run checks have a narrower fixed command list.
7. **No universal integration marketplace or scheduler is claimed.** GitHub, Drive, Slack and similar OAuth integrations need dedicated implementations; recurring background jobs are not included.
8. **Windows-only release checks remain.** This review environment is Linux. Windows Credential Manager and the packaged Windows executable must be validated on Windows; PyInstaller packaging was updated, but a Windows `.exe` was not built or certified here.

## Verification run

- `python -m pytest -q` — **207 passed, 50 subtests passed**.
- `python -m compileall -q app tests` — passed.
- `node --check static/app.js` — passed in the available Node runtime.
- Capability assertions — 28 skill files found; extensionless text names and supported document types recognized.
