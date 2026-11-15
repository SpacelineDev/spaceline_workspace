# Spaceline 0.8.7 — 30-role iterative review

**Review target:** the 0.8.6 source package.
**Release candidate:** 0.8.7.
**Method:** 30 sequential specialist review lenses. Each lens inspected a distinct area, recorded a finding or validation result, and passed that state to the next lens. These are 30 role-based passes performed by one assistant, not 30 independently spawned agents.

## Review ledger

| # | Specialist role | Review focus | Finding and result |
|---:|---|---|---|
| 1 | Principal system architect | Service boundaries and request flow | Selected-profile flow remains single-route; no automatic cross-profile model routing. |
| 2 | Model identity auditor | UI model vs actual provider request | Request carries selected profile and model; backend rejects mismatch before saving/sending the prompt. |
| 3 | Provider routing specialist | Profile selection and fallback | One active profile is resolved; provider failures do not trigger another model/profile. |
| 4 | Credential-scope reviewer | API key assignment | **Fixed:** explicit key IDs stay scoped to the profile; unselected vault keys are no longer discovered as implicit backups. |
| 5 | Authentication reliability engineer | 401/403 handling and key retries | Only keys explicitly assigned to the selected profile are eligible; successful side effects stop key retry/replay. |
| 6 | Consent and permission UX reviewer | Model/provider/endpoint changes | Consent fingerprint includes profile, provider, endpoint, model, auth mode and key IDs; old chats compare their stored model before restoring. |
| 7 | Chat continuity reviewer | Reopening old conversations | Model mismatch prompts before changing the active selection; declining retains the current selection. |
| 8 | Model catalogue reviewer | Listed vs usable model IDs | Discovery and access checks remain separate; only successful probes populate the verified list. Account entitlement still requires a real key test. |
| 9 | Context-window engineer | User context limit and compaction | **Fixed:** the selected/discovered context limit now reaches the chat API and sets a bounded history compaction budget. It remains an estimate, not provider-tokenizer accounting. |
| 10 | Skills prompt engineer | Skill activation and payload size | **Fixed:** combined activated skill context is capped at 12,000 characters and reports truncation. |
| 11 | Mode architect | Fifteen operational modes | Mode-specific instructions and tool sets are present; no mode is permitted to silently change the selected model. |
| 12 | Tool-permission reviewer | Read/write separation | Architect/Review/File Analysis/Data Analysis and planning paths remain read-only; writing tools are mode-gated. |
| 13 | Autonomous execution reviewer | Unattended execution boundaries | Autonomous mode remains bounded by selected project, command allowlist, checkpoints and confirmation boundaries. |
| 14 | Path-traversal reviewer | Project path resolution | Workspace safe-path and symlink checks prevent writes/reads outside the selected project. |
| 15 | Secret-handling auditor | Credentials and private files | Protected credential directories/files are blocked from agent read/write and omitted from listings; common token patterns are redacted. |
| 16 | Terminal security reviewer | Command execution | Commands use an allowlist and `shell=False`; this is not an OS sandbox, and running user project code can still execute code with the user's Windows permissions. |
| 17 | Git checkpoint reviewer | Rollback before edits | Project edits checkpoint the previous file before the write; checkpoints use Git metadata or a project-local fallback. |
| 18 | Replay/idempotency reviewer | Retry after side effects | **Fixed:** live tool handler now exposes the shared side-effect set to the provider retry guard; file writes, checks and browser mutations prevent a replay after execution. |
| 19 | Browser SSRF reviewer | Private/local network access | Browser destination guard rejects local/private/reserved targets after DNS resolution. DNS rebinding between validation and request remains a residual limitation; this is not a hardened network sandbox. |
| 20 | Browser interaction safety reviewer | Direct link-click path | **Fixed:** direct `browser_click_link` now rejects destructive/account labels instead of bypassing the command parser's safety guard. |
| 21 | Browser lifecycle engineer | Chromium resource cleanup | **Fixed:** browser close is idempotent and registered on FastAPI shutdown. |
| 22 | Document-ingestion reviewer | PDF/Office/spreadsheet reading | Document extraction supports text-bearing PDF, DOCX, XLSX, PPTX and CSV/TSV paths; scanned/image-only documents still need OCR/vision. |
| 23 | Skills import reviewer | Imported skill file limits | Per-file import limit remains 200 KB; combined activation prompt now has its own strict budget. |
| 24 | Streaming/API reviewer | Response status and persistence | Streaming path retains the selected profile/model identity and reports completion/error state through the API event stream. |
| 25 | Chat database reviewer | Conversation storage | Conversation history remains persisted locally; compaction affects only provider context, not stored history. |
| 26 | Chat deletion reviewer | Delete controls and cascade | Existing delete endpoints and confirmation flows remain covered by the current suite. |
| 27 | Copy/export reviewer | Reusability of outputs | Message/code/terminal copy controls and raw-code/full-Markdown paths remain present and regression-tested. |
| 28 | UI/accessibility reviewer | Theme, focus and motion | Green-charcoal visual system, floating controls, keyboard focus and reduced-motion handling remain present; a graphical end-to-end screenshot was not available in this runner. |
| 29 | Release engineer | Windows setup and metadata | **Fixed:** app version, API user-agent, README, quick start and `.spaceline_ready_0.8.7` launcher marker are aligned. |
| 30 | Adversarial QA reviewer | Release claims vs evidence | Added targeted regression tests; superseded a legacy test that expected unselected credential discovery. Full automated suite and static checks pass. |

## Additional fixes in 0.8.7

- Selected connection credential scope is explicit: `provider_key_ids(provider, preferred_ids)` treats `None` as a catalogue/discovery query, while an explicit list (including an empty list) is authoritative.
- Direct browser link navigation checks the risk label before following the link.
- Browser page mutations are tracked as side effects and block automatic re-execution after a later provider auth failure.
- Chromium resources are cleaned up on app shutdown.
- The configured context window is submitted with chat requests. If it is absent, Spaceline attempts provider discovery where supported; otherwise it uses a conservative default history budget.
- Skill payload is bounded across all activated skills, rather than only applying a file-size limit to each skill independently.

## Verification

- `python -m pytest -q` — **272 passed, 68 subtests passed**.
- `python -m compileall -q app` — passed.
- `node --check static/app.js` — passed.
- `tinycss2` parsed `static/style.css` — **745 rules, zero parse errors**.
- App API reports version `0.8.7`; Windows setup stamp and provider User-Agent are also `0.8.7`.
- Release ZIP integrity is checked during packaging.

## Not verified here

- Real provider keys, account-specific model entitlements, paid tiers and API quotas; these require the user's own credentials.
- Graphical end-to-end browser rendering on the user's Windows machine.
- Provider-internal routing/aliases after Spaceline has sent the exact model ID.
- OS-level sandboxing: the project terminal runs approved commands with the user's Windows account permissions.
