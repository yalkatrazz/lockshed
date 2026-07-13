============================================
  The LockShed - Brave Extension Setup
============================================

STEP 1 - Make sure The LockShed itself is running at least once
  - Installed via LockShed-Setup.exe? Just launch it once from the
    Start Menu (or desktop shortcut, if you created one). Nothing
    else needed here - Setup.exe already bundled everything this
    extension needs to talk to it.
  - Running from source instead? Run installera.bat first (if not
    done already) to install Flask, which powers this connection.

STEP 2 - Install extension in Brave:
  1. Open Brave and go to: brave://extensions/
  2. Enable "Developer mode" (top right toggle)
  3. Click "Load unpacked"
  4. Select THIS folder (chrome_extension) - if you installed via
     LockShed-Setup.exe, it's inside the install folder, typically:
       C:\Program Files\LockShed\chrome_extension
  5. The LockShed icon appears in toolbar

STEP 3 - Pair the extension with the app (one-time):
  1. Open The LockShed (Start Menu / desktop shortcut, or starta.bat
     if running from source) and unlock it
  2. Go to Settings -> "Extension" tab
  3. Click "Copy" next to the pairing code
  4. Right-click The LockShed icon in Brave's toolbar
     -> "Options"
  5. Paste the code and click "Save pairing code"
  You only need to do this once per installation. If you ever
  click "Regenerate code" in the app, you'll need to repeat
  step 5 with the new code.

STEP 4 - Start using:
  1. Go to any website with a login form
  2. A small 🔐 button appears in the password field
  3. Click it — matching passwords appear automatically!

KEYBOARD SHORTCUT (fallback for tricky popups):
  Press Ctrl+Shift+L while a password/login field is visible.
  This works even when the 🔐 badge doesn't appear, for example
  on sites that load their login form inside a popup or modal
  (the badge sometimes can't keep up with how fast these load).

HOW MATCHING WORKS:
  The extension sends the current domain (e.g. "steam.com")
  to the app, which looks for entries where the URL or
  service name contains that domain.

  TIP: Make sure your entries have URLs filled in for
  the best matching results!

SECURITY:
  - Server only listens on localhost (127.0.0.1)
  - Requests are only accepted from the extension's own
    background script (verified via its browser-assigned
    origin), never from a regular website's JavaScript
  - On top of that, every request needs a pairing code that
    is randomly generated per installation - it's shown once
    in Settings and never hardcoded in the extension's source
  - The app also refuses to hand out any passwords while the
    vault is locked, even if the extension is correctly paired
  - No data leaves your computer

============================================
