# Spaceline 0.9.0 — verification report

## Implemented and reviewed

- Added **Customize → Personalization** with persisted local preferences: preferred name, background/context, response tone, detail level, preferred format, problem-solving style, assumption-challenge behavior, useful-step explanations, examples, ambiguity handling, and custom instructions.
- Preferences are validated by the API, stored in the existing local SQLite workspace, and added to the system instructions used for the currently selected provider/model. They do not change provider, endpoint, model, or credential routing and do not fine-tune model weights.
- Refined **Deep Think** to request structured problem solving: decomposition, assumptions, constraints, alternatives, edge cases and verification. It does not expose hidden chain-of-thought. Deep Think no longer opens or refreshes the browser by default; browser use remains available when explicitly requested or needed by a browser-backed research mode.
- Added the **Preview** top-bar shortcut and a Codex-style source/HTML-preview split in the right workbench. HTML edits auto-save after a pause, can be saved with the Save control or Ctrl+S, and refresh the preview only after a successful save. Opening Preview from either editor now saves dirty content first and refuses to switch when saving fails.
- Applied a black, white and neutral-gray interface theme. User-generated HTML and image content retain their own intended colors inside their previews.
- Simplified chat reply controls to a single **▤ Copy note** button below assistant responses. Copying preserves the complete Markdown reply and code blocks; separate message/code copy options were removed, while terminal output copying remains.
- Updated app version, provider user-agent and Windows dependency-ready marker to 0.9.0.
- Added focused regression coverage for personalization persistence and prompt injection, preview endpoint delivery, Deep Think browser behavior and saving unsaved editor changes before preview navigation.

## Automated verification

- `python -m pytest -q` — **325 passed, 68 subtests passed**.
- `python -m compileall -q app` — passed.
- `node --check static/app.js` — passed.
- `tinycss2` parse of `static/style.css` — **1,075 top-level rules, zero parse errors**.
- Local server smoke test — `run.py` started; `GET /`, `/assets/app.js`, and `/assets/style.css` returned HTTP 200. The served HTML had its local session token injected.
- Post-change HTTP smoke test — the updated app served `/`, `/assets/app.js`, and `/assets/style.css` with HTTP 200; the served JavaScript and CSS contained the Copy note implementation.
- Targeted regression test for unsaved changes before top-bar Preview — first failed against the old behavior, then passed after the save guard was added.
- Targeted regression test for Deep Think opening the browser without research — first failed against the old behavior, then passed after mode routing was corrected.
- ZIP integrity checked after release packaging.
- Regression test confirms one Copy note action appears after assistant response content and the old chat/code copy controls are absent.

## Not verified in this environment

- A graphical browser interaction run could not be completed: headless Chromium returned `ERR_BLOCKED_BY_ADMINISTRATOR` when navigating to the local app. The app's HTTP/static asset smoke tests and API/frontend contract tests passed, but this report does not claim a visual end-to-end browser pass.
- Real provider chat and image-generation requests were not sent. They require the user's own provider key, model entitlement, account quota and network access. Existing provider tests use controlled test doubles for external API boundaries.
- `start.bat` and Smart App Control behavior have not been executed on the user's Windows PC. The project remains a source-based Windows/Python release; do not disable Smart App Control. If Windows blocks a dependency, capture the exact Code Integrity event and blocked module for diagnosis.

## Review method and limits

The accompanying `UPGRADE_REVIEW_14_ROLES_0.9.0.md` records 14 specialist review lenses applied to the shared implementation. It does not claim that 14 autonomous subprocess agents were launched. No existing provider, key-vault, image-generation, project, notes, browser, editor, terminal, or workspace data subsystem was intentionally removed.
