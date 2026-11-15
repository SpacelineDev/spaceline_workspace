# Spaceline 0.8.2 — 11-specialist review record

**Target:** The previously delivered Spaceline 0.8.0 project source.

**Method:** Eleven sequential specialist review passes over the same working tree. These are distinct review lenses performed by one assistant, not eleven independently spawned agents. Each pass used the latest code and carried fixes into the next pass.

| Pass | Specialist lens | Critique / risk found | Correction or verification |
|---:|---|---|---|
| 1 | Product workflow | Browser navigation existed, but there was no obvious control surface beside chat. | Added a right-side Browser command bar and a chat-toolbar shortcut that reveals it. |
| 2 | Browser interaction | Basic research could read and follow links but did not expose normal page controls. | Added bounded commands for links, buttons, tabs, menu items, text fields, select menus, checkboxes, hover and scrolling. |
| 3 | Browser safety | General browser commands can easily cross into account or transaction actions. | Blocked password/token/payment fields, form submission, purchases, sending, transfer, deletion, booking, subscription and destructive/account actions. Private/local destinations remain blocked by the request guard. |
| 4 | AI tool integration | The command bar alone would not let a tool-capable model operate the same controls from chat. | Added browser select/checkbox controls and expanded the tool schemas and handlers used by Web Search/Deep Think/Deep Research. |
| 5 | Model entitlement | Provider model-list APIs return IDs that may not be callable by the current key/account. | Added **Test all models** per provider connection using a minimal native-protocol generation probe. |
| 6 | Model-result UX | Failed model IDs and errors should not pollute the usable chat model list. | After a completed bulk run, only passing model IDs appear in the working list; failures are summarized as a count and individual failure text is not displayed in the UI. |
| 7 | Provider reliability | An unexpected SDK exception could terminate the SSE stream and skip later models. | Catch unexpected probe failures per model, suppress raw diagnostics and continue through remaining IDs; the stream still emits a final summary. |
| 8 | Cost and key-pool review | Bulk tests may consume quota/credits and a profile can contain multiple saved keys. | Added an explicit confirmation warning. Alternate keys may be tried after auth/permission denials; this is documented. |
| 9 | Thinking-state UX | The processing state needed a small visible text cue rather than only a canvas animation. | Kept the 36px HUD and added a subtle shimmer to the small “Thinking” label; respects reduced-motion. |
| 10 | Frontend defects | Dead/empty controls and double browser commands could create confusing states. | Added busy-state protection to the command runner and a source-level regression test for literal empty button templates. |
| 11 | Adversarial/release QA | New tests must actually be collected; the browser and provider paths need honest verification boundaries. | Moved bulk tests into the pytest-discoverable test class, added error-continuation and tool-schema tests, ran full tests/compilation/JS syntax checks, and documented that live API keys and a graphical browser smoke test were unavailable in this build environment. |

## Verification

- Full verification: `python -m pytest -q` — **217 passed, 68 subtests passed**. `python -m compileall -q app run.py tests` and `node --check static/app.js` both pass. The bulk route tests are inside the pytest-discovered `ApiTests` class; collection explicitly confirms these tests run.
- Python compilation and JavaScript syntax are checked before packaging.
- Empty literal `<button></button>` templates are checked by regression test.
- Live provider entitlements cannot be validated without the user's own provider keys. Bulk verification itself may incur charges/quota use.
- Browser visual/E2E smoke test could not be completed in the build container because Chromium navigation to both local HTTP and local file URLs is blocked by the environment (`ERR_BLOCKED_BY_ADMINISTRATOR`). Browser command parsing, route authentication, tool schemas and UI contracts are covered by tests instead.

## Scope boundaries

The embedded browser is a separate persistent Chromium profile; it does not control the user's existing Chrome process or reuse its cookies. It can operate ordinary visible page elements only; sensitive authentication, payment, submit, messaging and destructive actions are intentionally blocked. Browser-level DNS checks are not a complete OS/network sandbox. A model passing a probe proves only that the selected key/profile accepted a tiny request at test time, not that future quota, uptime or billing will remain available.


## 0.8.2 follow-up — browser startup repair
- Finding: the 0.8.1 UI and browser-control endpoints existed, but the Windows launcher did not provision the Playwright-managed Chromium executable. This caused the missing-browser warning on a fresh install.
- Fix: `start.bat` now verifies the expected Chromium executable and installs it automatically if absent, including existing virtual environments. If download fails, the launcher continues with other workspace features and prints a recovery command.
- Verification: release-contract test covers the launcher check/install commands; full tests, Python compilation and JavaScript syntax checks pass. Windows GUI/browser startup remains to be confirmed on the user's PC.
