# Spaceline 0.9.6 repair verification

Date: 2026-11-13

| Check | Result |
|---|---|
| Full automated suite: `python -m pytest -q` | 389 passed, 68 subtests passed |
| Firebase frontend config declaration | Regression test passed |
| GitHub provider wiring | Regression test passed |
| First-open landing screen markup / auth controls | Regression tests passed |
| Per-UID storage directory separation | Unit tests passed |
| Legacy workspace claim/migration | Unit test passed |
| Interrupted migration fails closed | Unit test passed |
| Authenticated API workspace isolation across two synthetic UIDs | Integration test passed |
| Python syntax: `python -m compileall -q app run.py tests` | Passed |
| JavaScript syntax: `node --check static/auth.js` | Passed |
| Release packaging: `python package_release.py` | Passed; relative paths preserved |
| Real Firebase Google/GitHub/email authentication | Not run; requires project config and valid account credentials |
| Windows startup and embedded Chromium | Not run; requires Windows plus Playwright Chromium installation |

The synthetic UID test exercises the application API and storage routing with a mocked Firebase ID-token verifier. It does not replace real Firebase token verification or browser-based OAuth testing.
