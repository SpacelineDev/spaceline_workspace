# Spaceline 0.8.6 — 11-specialist review record

**Target:** the in-progress 0.8.5 working source tree.  
**Result:** prepared for the 0.8.6 release candidate.  
**Method:** eleven sequential specialist review lenses. These are distinct analytical roles performed by one assistant, not eleven independently spawned agents. Findings from each lens were applied before the next review.

| # | Specialist lens | Challenge / failure mode examined | Correction / evidence |
|---:|---|---|---|
| 1 | Principal architect | Multiple enabled profiles could be treated as a routing pool. | `connection_pool_order()` now returns exactly one explicitly selected profile; missing/disabled selection is an error. |
| 2 | Backend API reviewer | A stale or malicious client could submit a different profile ID than the active one. | Chat API rejects a request profile that differs from the approved active profile before adding the user message or contacting the provider. |
| 3 | Provider protocol reviewer | Key retries could be confused with model failover. | Credential rotation is scoped to the selected profile's own key pool; it retains the profile's provider, endpoint and exact model ID. |
| 4 | Model identity reviewer | The selected model could mismatch the request body or active profile config. | The frontend sends `profile_id` and `model`; backend validates both against the approved profile before sending. Regression test captures the profile passed to the provider stream. |
| 5 | Permission UX reviewer | Model/provider/endpoint changes and reopening old chats could silently alter the active model. | Added a modal showing current and proposed connection/model; approval is required. Declining preserves the current selection. Connection edits, model picker, verified-model shortcut and old-chat open path use this guard. |
| 6 | Frontend state reviewer | Boot and chat-history loading could reselect the first enabled model. | Removed implicit fallback in `selectedProfile()` and `loadProviders()`. No selection remains visibly unselected; send stays disabled until a real selection exists. |
| 7 | Modes / agent-tool reviewer | Requested operational modes might share identical tools or bypass permissions. | Retained 15 distinct task modes; Architect and Review remain read-only, Build/Debug/Autonomous use bounded project tools, file/data analysis use read-only file tools. Existing tests cover tool sets and unique instructions. |
| 8 | Copy/export reviewer | Generated answers/code/terminal output might be difficult to reuse. | Verified plain message, Copy raw code, Copy full Markdown, code-block copy and terminal-output copy controls with clipboard feedback. |
| 9 | Context and rollback reviewer | Long conversations and project edits could lose context or become unrecoverable. | Automatic context compaction preserves recent turns; every project file write creates a checkpoint, stored under `.git/spaceline-checkpoints` for Git projects or `.spaceline-checkpoints` otherwise. |
| 10 | Visual system / accessibility reviewer | The UI could remain grey/black, inconsistent or inaccessible. | Applied `#121614` / `#181C1A` green-charcoal surfaces, translucent borders, Space Grotesk/Inter and Geist Mono stacks, floating controls, modal clarity, custom cursor halo, visible focus and reduced-motion handling. |
| 11 | Adversarial QA / release reviewer | Claims could exceed tests or release metadata could be inconsistent. | Added active-profile list and bypass regression tests; aligned app version, user-agent and setup marker to 0.8.6; ran full pytest, Python compile, JS syntax and CSS parsing. User API keys and a graphical Windows run remain unverified. |

## Verification

- `python -m pytest -q` — **260 passed, 68 subtests passed** in the last full run before final packaging checks.
- `python -m compileall -q app run.py` — passed.
- `node --check static/app.js` — passed.
- `tinycss2` stylesheet parse — zero CSS parse errors.
- Exact-routing tests verify the provider stream receives the selected profile/model; mismatch and unapproved-profile requests are rejected without sending or persisting the prompt.

## Not claimed as verified

- No real user API credentials were available here; paid/free access and account-specific model entitlements still need testing with your own keys.
- A provider can still apply its own server-side aliases or routing after Spaceline sends the exact model ID. Spaceline cannot guarantee provider-side execution identity unless that provider returns verifiable response metadata.
- Graphical end-to-end testing on your Windows laptop, Windows Credential Manager, and actual Chromium startup remain to be checked on your PC. The browser in this build is a separate Spaceline Chromium profile, not your ordinary Chrome session.
- The eleven specialists above are sequential review roles, not independently running agents.
