# Spaceline login and first-open repair — 2026-11-13

## Fixed

- Added a responsive landing/first-open screen that introduces the Spaceline workspace before sign-in.
- Fixed the Firebase frontend config variable declaration so the configured web app can initialize.
- Preserved Google sign-in with popup-to-redirect fallback.
- Added GitHub sign-in using Firebase `GithubAuthProvider`, with popup-to-redirect fallback.
- Preserved Email/Password sign-in, account creation, password reset, remember-me persistence and password visibility.
- Kept the workspace hidden until Firebase reports a signed-in user.
- Kept API calls protected by the local session token and verified Firebase ID token.
- Added per-Firebase-UID local data directories for the workspace, API-key metadata, images, skills and embedded browser session.

## Required local configuration

Copy `.env.example` to `.env`. Fill `FIREBASE_WEB_API_KEY`, `FIREBASE_APP_ID` and `FIREBASE_MESSAGING_SENDER_ID` from the Firebase Web App configuration. Confirm project ID `spaceline-87f04` and auth domain `spaceline-87f04.firebaseapp.com` match the console. Configure Firebase Admin ADC with `gcloud auth application-default login`.

For GitHub, keep the GitHub OAuth Client ID and Client Secret in Firebase Authentication → GitHub provider settings. Do not put the Client Secret in source code or `.env`.

## Legacy workspace handling

The first verified Firebase UID claims existing installation-wide workspace data and moves it into its private `.spaceline-users/<uid-hash>` directory. Later UIDs receive separate roots. Back up `Documents\\Spaceline` before first upgraded launch and sign in with the account that owns the old data. An interrupted migration fails closed.

## Verification

See `TEST_REPORT_0.9.6_LOGIN.md` and `REPAIR_REPORT_0.9.6.md`. Automated tests pass; real Firebase sign-in and Windows/Chromium runtime tests remain manual setup tasks.
