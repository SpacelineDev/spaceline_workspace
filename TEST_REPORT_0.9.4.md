# Spaceline 0.9.4 — verification report

Date: 2026-11-12

## Automated checks

| Check | Result |
|---|---:|
| Full Python test suite | **366 passed** |
| Python subtests | **68 passed** |
| Python bytecode compilation (`app/*.py`, `run.py`) | Passed |
| JavaScript syntax (`node --check static/app.js`) | Passed |
| CSS parser (tinycss2) | 0 top-level parse errors |
| Release API/static asset tests | Passed; HTML, JS and CSS are versioned 0.9.4 and served with no-store cache headers |
| Local port-selection tests | Passed; occupied ports are skipped and an exhausted range raises a clear error |

## Chromium DOM regression

Executed the actual message-rendering and copy-normalization functions from `static/app.js` in system Chromium using a Playwright DOM harness.

The harness inserted stale legacy **Copy**, **Copy markdown**, **Copy all** and **Copy code** buttons after the observer started. Results:

- Exactly **one** button remained in the assistant reply.
- Its accessible label and title were `Copy note`; the visible content was only the note SVG icon.
- The button appeared below the full message content.
- No buttons remained inside the Markdown/code content.
- The observer settled; the SVG was not rewritten in an endless mutation loop.
- Clicking the note button copied the original Markdown response exactly, including heading, prompt, Python code block and details.

This test reproduced and fixed the 0.9.3 defect. The prior normalizer compared SVG `innerHTML` strings; Chromium normalizes parsed SVG markup, so the comparison never became stable. Version 0.9.4 uses the parsed DOM structure instead.

## Research and Codex workflow checks

- Web Search and Deep Research seed multiple live searches through the app-managed, headless Chromium session.
- Research evidence is bounded and marked as untrusted page data before it reaches the selected model.
- Research progress remains in Activity; the visible Browser workbench is not auto-opened. An explicit request to open/show/use the browser now reveals it even when a research mode is selected.
- Deep Research allows up to 14 model tool rounds; Web Search allows up to 8.
- The active provider/model remains pinned. Spaceline does not silently switch providers or models to imitate another service.
- Review tab selection is persisted across reloads.

## Not verified in this environment

- A live call to the user's configured AI provider/API key was not made.
- Windows 11 GUI behavior was not run on the user's actual laptop.
- The standalone Windows EXE was not built here; use `build_windows_exe.bat` on Windows to build it after installing the development requirements.

These are intentionally not reported as passing.
