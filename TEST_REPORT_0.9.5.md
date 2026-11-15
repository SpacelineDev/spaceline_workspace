# Spaceline 0.9.5 — Verification report

Date: 2026-11-12

## Automated checks

| Check | Result |
|---|---:|
| Full Python test suite | **377 passed** |
| Python subtests | **68 passed** |
| Python bytecode compilation (`python -m compileall -q app run.py`) | Passed |
| JavaScript syntax (`node --check static/app.js`) | Passed |
| CSS parser (`tinycss2`) | 0 top-level parse errors |
| Release contracts | Passed; version 0.9.5 API marker, no-store HTML, and cache-busted 0.9.5 JS/CSS assets |
| Local server smoke test | Passed; `/api/status` returned version 0.9.5 with a valid local session token; static app bundle returned HTTP 200 |

## Copy-note browser regression

Executed the actual message-rendering and copy-normalization functions from `static/app.js` in system Chromium using a Playwright DOM harness. It inserted stale legacy **Copy**, **Copy markdown**, **Copy all**, and **Copy code** buttons after the MutationObserver started.

Results:

- Exactly **one** button remained in the assistant reply.
- The button had an icon only (one note SVG), with accessible name/title `Copy note`.
- The note control was below the complete response.
- No buttons remained inside Markdown or code content.
- Research stayed on Activity; an explicit request to open the Browser workbench displayed Browser; a negated request stayed in Activity.
- Clicking the note control copied the complete original Markdown exactly, including the heading, prompt, Python code block, and details.

## Research routing and safety checks

- Web Search initial evidence uses two concurrent direct HTTP queries; Deep Research uses three distinct search angles concurrently.
- Follow-up model tools expose `web_search` and `web_open_source`, not Chromium navigation or interaction tools, unless the user explicitly requested interactive browser use.
- Research completion no longer requests a browser page snapshot; this was the hidden path that previously started Chromium.
- Embedded Playwright Chromium remains installed/available for explicit interactive browser tasks.
- Search/source fetch tests cover provider fallback, DuckDuckGo/Bing URL unwrapping, redirect revalidation, rejection of local/private destinations, rejection of unsupported content types, and a 2 MB streaming response cap.
- Research content is bounded and marked untrusted before it is added to model context.

## Codex comparison performed

Reviewed the current official ChatGPT Work and Codex guide, Codex app announcement and current Codex changelog. The guide distinguishes Chat (quick assistance), Work (longer research/deliverables) and Codex (software-development tasks); it also documents Codex Cloud, voice, project/worktree and multi-agent workflows. The public changelog lists Codex CLI 0.167.2 (2026-11-11) and Codex app 26.1007 (2026-10-08) as separate release tracks. See `CODEX_WORKFLOW_REVIEW_2026-11-12.md` for the detailed comparison and explicit feature gaps.

## Not verified in this environment

- A live request to DuckDuckGo, Bing or Google could not be completed because outbound DNS resolution is restricted in this build environment. The retrieval logic is covered by mocked HTTP tests, but real external search must be tested on the target Windows network.
- A live request to the user's configured AI provider/API key was not made.
- Spaceline was smoke-tested through a local ASGI server on Linux/Python 3.13; Windows 11 GUI behavior was not run on the user's laptop.
- The standalone Windows EXE was not built here; run `build_windows_exe.bat` on Windows after installing the development requirements if an EXE is required.

No test result is reported as passing unless it was run in this build.
