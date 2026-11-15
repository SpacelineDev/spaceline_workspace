# Spaceline 0.9.6 repair report

Date: 2026-11-13
Source archive: `Spaceline-0.9.6.zip`

## Implemented in this repair

- Rebuilt the signed-out first screen as a responsive landing experience with product introduction, feature highlights, and a compact sign-in card. Once Firebase restores or completes authentication, the existing workspace UI is shown.
- Fixed the Firebase frontend initialization defect: `config` is now read from `window.SPACELINE_FIREBASE_CONFIG` before validation and `initializeApp`.
- Added Firebase GitHub authentication to the existing Google and email/password options, using popup authentication and redirect fallback. Requests `read:user` and `user:email` scopes.
- Added per-verified-Firebase-UID local storage for workspace SQLite data, project files, API-key metadata, generated images, imported skills, and embedded Chromium profiles.
- Added a first-account legacy-workspace migration. The first verified Firebase UID claims prior installation-wide data. A pending/claimed ownership marker prevents another account from claiming the remainder after an interrupted migration; incomplete migration fails closed. A cross-process filesystem lock serializes first-account claims when two Spaceline instances are started against the same workspace root.
- Kept Firebase ID-token verification and the local per-process token requirement at the API boundary. No unauthenticated fallback was added.
- Updated Firebase setup, README, changelog, `.env.example`, and release notes. The template carries the project ID and auth domain visible during the user's Firebase setup; remaining public web config values must be copied locally.
- Added tests for UID-scoped storage, legacy migration, incomplete migration fail-closed behavior, GitHub auth wiring, config initialization, and the first-open landing screen.

## Verification performed

| Check | Result |
|---|---|
| `python -m pytest -q` | 389 passed, 68 subtests passed |
| `python -m compileall -q app run.py tests` | Passed |
| `node --check static/auth.js` | Passed |
| `python package_release.py` | Passed; package path structure preserved |
| API-level two-UID isolation test | Passed using synthetic Firebase token verification in tests |
| Visual browser launch | Not run; the build environment has Playwright installed but its Chromium executable is absent |
| Real Firebase sign-in | Not run; requires the user's Firebase Web App values and configured Firebase Admin Application Default Credentials |
| Windows launcher / Chromium smoke test | Not run; requires a Windows runtime and Playwright browser installation |

## Remaining setup / verification on the user's machine

1. Back up the current `Documents\\Spaceline` data folder before first launch after upgrading.
2. Copy `.env.example` to `.env` and fill in `FIREBASE_WEB_API_KEY`, `FIREBASE_APP_ID`, and `FIREBASE_MESSAGING_SENDER_ID` from Firebase Console → Project settings → General → Your apps. Verify the project ID and auth domain already present in the template.
3. Configure Firebase Admin Application Default Credentials for project `spaceline-87f04` using `gcloud auth application-default login`.
4. Confirm Google, GitHub and Email/Password are enabled in Firebase Authentication. Confirm the GitHub OAuth app callback is `https://spaceline-87f04.firebaseapp.com/__/auth/handler`, and its Client ID / Client Secret are saved in Firebase's GitHub provider configuration.
5. Run `start.bat` on Windows and test account creation, Google sign-in, GitHub sign-in, email/password sign-in, password reset, refresh, sign-out and account switching.
6. Test two separate Firebase accounts and verify their workspace contents remain separate. The first account to sign in after upgrading claims the existing legacy workspace; use the account that owns that data.

## Release status

The identified source-code defects addressed above are fixed and automated tests pass. The archive is suitable for controlled local setup/testing, but a real Firebase/Windows end-to-end release check is still outstanding. Do not treat external OAuth or local runtime as verified until the manual checks above pass.
