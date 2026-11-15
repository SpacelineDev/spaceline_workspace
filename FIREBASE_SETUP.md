# Firebase setup

1. In Firebase Console, select project `spaceline-87f04` and open Project settings → General → Your apps → Spaceline. Copy its web configuration values into `.env` (`FIREBASE_WEB_API_KEY`, `FIREBASE_APP_ID`, `FIREBASE_MESSAGING_SENDER_ID`, and optionally `FIREBASE_STORAGE_BUCKET`). `.env.example` already contains the project ID and auth domain observed during setup; verify those match the Firebase screen.
2. Under Authentication → Sign-in method, enable Google, GitHub, and **Email/Password**. For GitHub, create a GitHub OAuth App and set its authorization callback URL to `https://spaceline-87f04.firebaseapp.com/__/auth/handler`, then enter its Client ID and Client Secret in the Firebase GitHub provider settings. Never put the GitHub Client Secret in the frontend or commit it to source control.
3. Under Authentication → Settings → Authorized domains, include `localhost`. If you use another local hostname, add it explicitly.
4. Install the Firebase Admin Python dependency (included in requirements) and configure Application Default Credentials for the same project. On developer machines use `gcloud auth application-default login`; in hosted environments use workload identity. Do not commit, zip, or share service-account JSON files.
5. Restart Spaceline and inspect the public `/api/status` diagnostic for the booleans `firebase_web_configured` and `firebase_admin_ready`. It does not expose configuration values or credentials.

Spaceline supports Google, GitHub, and Firebase Email/Password authentication. The sign-in screen is also the first-open landing page; it introduces the workspace and provides provider sign-in plus email access. The login screen uses the Firebase browser persistence selected by the user: **Remember me** keeps the Firebase session in browser-local persistence; clearing it uses browser-session persistence. Passwords are submitted only to Firebase and are never stored by Spaceline.

Spaceline Google sign-in grants identity to this application only. It requests no Gmail or Drive scopes. The embedded Chromium profile remains independent.

## Configuration diagnosis

Spaceline reads `.env` from the project root at startup. Copy `.env.example` to `.env`, fill in the Firebase web-app values, then restart the server. When required web settings are missing, the login page names the missing variables. The public `/api/status` endpoint reports only configuration readiness and missing variable names; it never returns values or credentials.

## Per-account local workspace storage

Workspace files, SQLite state, API-key metadata, generated images, imported skills and embedded-browser profiles are stored under `.spaceline-users/<uid-hash>` for each verified Firebase UID. On first use after upgrading, the first authenticated UID claims and moves legacy installation-wide data into its own folder. Back up the workspace before upgrading and sign in first with the account that owns the existing data. If the migration is interrupted, Spaceline fails closed rather than letting another account claim the remaining files. This is local filesystem isolation, not cloud synchronization or protection from other Windows users with access to the same Windows profile.
