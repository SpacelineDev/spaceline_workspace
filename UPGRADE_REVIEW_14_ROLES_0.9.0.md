# Spaceline 0.9.0 — 14-role upgrade review

This document records 14 specialist review lenses applied to one implementation pass. It does not claim that 14 autonomous subprocess agents were launched.

| # | Review lens | Scope and acceptance check | Result / limitation |
|---:|---|---|---|
| 1 | Product architect | Preserve the existing FastAPI/local workspace architecture | Existing app and APIs retained |
| 2 | Frontend engineer | Add personalization and preview UI without replacing navigation | Added Customize tab and topbar Preview |
| 3 | UX engineer | Clear states, save feedback, accessible controls | Save status, reset, auto-save and refresh controls added |
| 4 | Personalization engineer | Persist user response preferences locally | SQLite settings table and GET/PUT endpoints added |
| 5 | Prompt engineer | Apply preferences to selected-model request context | Preferences included in system instructions; limits remain enforced |
| 6 | Reasoning-workflow reviewer | Make Deep Think structured without exposing hidden reasoning | Adds decomposition, assumptions, trade-offs and checks; no private chain-of-thought display |
| 7 | Provider-routing engineer | Preserve exact selected provider/model | Existing routing checks untouched; regression test retained |
| 8 | Editor engineer | Keep edits safe and save through protected API | Auto-save, Save and Ctrl+S use existing `/api/file` endpoint |
| 9 | Preview engineer | Show HTML preview beside editable code | Sandboxed iframe and cache-busting refresh added |
| 10 | Backend engineer | Validate preference values and persist settings | Pydantic constraints and SQLite persistence added |
| 11 | Data-integrity reviewer | Prevent losing edits while switching files/tabs | Save-before-open and save-before-preview guards added |
| 12 | Security reviewer | Keep API secrets server-side; don't weaken local auth | No key handling changes; personalization endpoints use local token |
| 13 | Windows/reliability reviewer | Keep Windows launcher/security model | Windows-only launcher retained; setup marker bumped to 0.9.0 |
| 14 | QA/release reviewer | Test regression paths and avoid unsupported release claims | Final test counts are recorded in `TEST_REPORT_0.9.0.md` |

## Explicit limitations

- Personalization steers response instructions; it does not fine-tune model weights or enable hidden provider reasoning controls.
- Deep Think does not expose hidden chain-of-thought. It requests concise, useful reasoning summaries and verifiable steps.
- Live preview is for project HTML served by Spaceline. It is not a full browser devtools replacement.
- Actual provider availability and generated-image quality depend on the user's own keys, entitlements, provider status and internet connection.
- This environment can run automated tests and static checks, but cannot certify graphical behavior on the user's Windows desktop.
