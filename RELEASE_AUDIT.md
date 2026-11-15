# Spaceline 0.9.6 — repair and release audit

Date: 2026-11-13  
Source: user-supplied `Spaceline-0.9.6.zip`

## Repair status

| Area | Original issue | Repair status |
|---|---|---|
| First-open experience | The signed-out screen was only a compact login card and did not introduce the product. | Responsive landing page added with workspace introduction, feature summaries, Google/GitHub/email sign-in and a responsive sign-in card. |
| Firebase initialization | `auth.js` checked and initialized an undeclared `config` variable. | Fixed by reading `window.SPACELINE_FIREBASE_CONFIG` before validation/initialization; regression test added. |
| GitHub sign-in | Firebase GitHub provider could be enabled, but the frontend had no GitHub provider button/handler. | Added `GithubAuthProvider`, popup/redirect fallback and `read:user` / `user:email` scopes. Firebase-side OAuth credentials still need real verification. |
| Firebase web setup | Project values were absent from `.env`. | `.env.example` includes the project ID and auth domain observed in setup; API key, App ID and sender ID must be filled locally. |
| Firebase Admin | Backend requires Firebase Admin ADC to verify ID tokens. | Fail-closed behavior retained; setup docs use `gcloud auth application-default login`. Real ADC was not available in this environment. |
| API authentication | Protected API calls require both the local per-process token and a verified Firebase ID token. | Retained, not weakened. API integration tests use a synthetic verifier only in test fixtures. |
| Account isolation | Workspace state was installation-wide. | Added per-verified-UID workspace, SQLite, API-key metadata, generated-image, skills and embedded-browser roots. |
| Legacy migration | Existing local data needed a safe first-account owner. | First verified UID claims the legacy workspace. A pending/claimed ownership marker makes an interrupted move fail closed. Back up before first upgraded launch and use the Firebase account that owns the old data. |
| Release packaging | Runtime directories and assets must preserve relative paths; secrets must not ship. | Release packager retains path structure and excludes `.env`, private key files, local databases, caches and service-account files. |

## Verification evidence

| Check | Result |
|---|---|
| `python -m pytest -q` | 389 passed, 68 subtests passed |
| `python -m compileall -q app run.py tests` | Passed |
| `node --check static/auth.js` | Passed |
| `python package_release.py` | Passed; path-preserving archive generated |
| Two-UID API isolation integration test | Passed using a synthetic Firebase ID-token verifier |
| Legacy migration / interrupted migration tests | Passed |
| Real Firebase Google/GitHub/email authentication | Not run; requires configured Firebase Web values, Admin ADC and real user accounts |
| Windows launcher / embedded Chromium | Not run; requires Windows and Playwright Chromium installation |
| Visual screenshot/browser smoke | Not run; this environment has Playwright but no installed Chromium executable |

The synthetic token verifier exercises the app's middleware/storage routing. It does not establish that the user's Firebase OAuth configuration is valid or that live token verification has succeeded.

## Remaining user setup and manual checks

1. Back up the existing `Documents\\Spaceline` workspace before the first upgraded launch.
2. Copy `.env.example` to `.env`. Fill `FIREBASE_WEB_API_KEY`, `FIREBASE_APP_ID` and `FIREBASE_MESSAGING_SENDER_ID` from Firebase Console → Project settings → General → Your apps. Verify the project ID and auth domain match `spaceline-87f04`.
3. Configure Firebase Admin ADC for the same project with `gcloud auth application-default login`.
4. Confirm Firebase Authentication has Google, GitHub and Email/Password enabled. Confirm GitHub callback `https://spaceline-87f04.firebaseapp.com/__/auth/handler` and the GitHub OAuth Client ID/Secret saved in Firebase.
5. On Windows, run `start.bat` and test account creation, Google sign-in, GitHub sign-in, email/password sign-in, password reset, refresh, sign-out and account switching.
6. Test two distinct Firebase users on the same installation. Confirm projects, chats, API key metadata, images and browser sessions remain separate. The first user to use the workspace after upgrade claims legacy data.

## Release decision

**Suitable for controlled local setup/testing; not yet verified for general release.** Source-code repairs and automated tests are complete. Real Firebase OAuth/Admin ADC, the Windows launcher, Chromium startup and live two-account behavior still require a manual end-to-end run on the user's machine.
