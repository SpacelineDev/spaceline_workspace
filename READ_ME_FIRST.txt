SPACELINE QUICK SETUP PATCH

1. Extract these 3 files into the MAIN Spaceline folder (the folder containing start.bat and .env).
2. Double-click QUICK_SETUP.bat.
3. If prompted, sign into Google in the browser. On the Firebase Service accounts page, click Generate new private key. The setup window detects the downloaded JSON for project spaceline-87f04 and stores it under your Windows LocalAppData folder, outside the project.
4. Spaceline then launches. Keep the window open.

The Firebase Admin key is private. Do not upload it, share it, or put it in the project ZIP/repository. The script moves the downloaded JSON out of Downloads into your local AppData secrets folder. It does not request billing information.

The existing .env (Firebase web app settings) is preserved. This patch does not overwrite it.
