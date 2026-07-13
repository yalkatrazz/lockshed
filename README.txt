========================================
  THE LOCKSHED - Complete Guide
========================================

A private, local password manager that runs entirely on your own
computer. No cloud account, no subscription, no third party ever
sees your data.

NOTE: This app used to be called "Lösenordsvalvet". If you're
upgrading from that version, nothing you need to do - the app
automatically copies your existing vault and settings over to
the new file names the first time it starts (see section 2 for
details). Your old files are left in place untouched, just in case.


----------------------------------------
1. INSTALLATION
----------------------------------------

Two ways to get The LockShed running - pick whichever matches
what you have:

OPTION A - You have "LockShed-Setup.exe"
  1. Run LockShed-Setup.exe and follow the installer
  2. Windows SmartScreen may show an "unknown publisher" warning
     the first time - click "More info" -> "Run anyway" (this is
     just because the installer isn't code-signed, not a sign of
     a problem - see section 10 for why)
  3. Launch The LockShed from the Start Menu (or desktop shortcut,
     if you checked that box during install)
  4. Choose a strong master password when prompted
  No Python installation needed - everything required is already
  bundled inside the installer.

OPTION B - You have the source folder (password_manager.py etc.)
  REQUIREMENTS
    Python 3.9 or newer
    Download: https://www.python.org/downloads/
    IMPORTANT: Check "Add Python to PATH" during installation!

  FIRST-TIME SETUP
    1. Double-click "installera.bat"
    2. Wait for "Done!" message
    3. Double-click "starta.bat" to open the app
    4. Choose a strong master password when prompted

  STARTING THE APP AFTERWARDS
    Just double-click "starta.bat". The console window flashes
    briefly and closes - this is normal, the app itself opens
    separately.

  IF SOMETHING WON'T START
    Double-click "debug.bat" instead. This keeps a console window
    open so you can read any error message and share it for help.

  (Section 10 covers turning this source folder into your own
  LockShed-Setup.exe, if you want Option A's convenience instead.)


----------------------------------------
2. WHERE YOUR DATA LIVES
----------------------------------------

Your passwords are stored in a single encrypted file:

  C:\Users\<YourName>\.lockshed.enc

This file is created automatically the first time you set a
master password. It is NOT readable as plain text by anyone -
not even you - without going through the app and entering your
master password.

Settings (theme, categories, mobile PIN, etc.) are stored
separately in:

  C:\Users\<YourName>\.lockshed_settings.json

This settings file does NOT contain any passwords and is safe
to view or delete (deleting it just resets app preferences).

UPGRADING FROM "LÖSENORDSVALVET": the first time this version
starts, it looks for the old .losenordsvalvet.enc and
.losenordsvalvet_settings.json files and copies (not moves) them
to the new names above if the new ones don't exist yet. The old
files are left untouched - you can delete them yourself later
once you've confirmed everything looks right.


----------------------------------------
3. SECURITY: HOW YOUR DATA IS PROTECTED
----------------------------------------

Your master password is never stored anywhere, in any form.
Instead, every time you unlock the vault, the app:

  1. Takes your master password
  2. Runs it through a slow key-derivation function (industry
     standard, hundreds of thousands of rounds) combined with a
     random "salt" unique to your vault file
  3. Uses the result to decrypt your data with a well-established,
     widely audited symmetric encryption algorithm (the same family
     used by banks and password managers like Bitwarden)
  4. Separately verifies the file hasn't been tampered with before
     trusting its contents

If someone steals your .enc file without your master password,
they get unreadable scrambled bytes - nothing more. The slow
key-derivation step also makes brute-force guessing attacks on
your master password extremely time-consuming, even with
powerful hardware.

WHAT THIS MEANS FOR YOU
  - Your master password is the ONLY key. If you forget it,
    there is no recovery option, no "reset password" link, no
    backdoor. This is by design - it's what makes the encryption
    meaningful.
  - Choose a master password you can remember but that isn't
    easily guessed (avoid birthdays, pet names, "password123").
    A passphrase of 4-5 random words is both memorable and strong.
  - The app warns you if Caps Lock is on while typing passwords,
    and tells you if a password is weak or reused elsewhere.


----------------------------------------
4. BACKING UP YOUR VAULT
----------------------------------------

Because there's no cloud account, YOU are responsible for backups.
If your hard drive fails and you have no backup, your passwords
are gone permanently (the encryption that protects you from
hackers also means we can't recover it for you).

RECOMMENDED: Point your vault file at a synced cloud folder
  1. Open the app -> Settings -> Data file
  2. Click "New…" and choose a folder inside your OneDrive,
     Dropbox, or Google Drive folder
  3. The app will offer to move your existing file there

This is safe because the file is already encrypted - cloud
storage providers (and anyone who might access your account)
only ever see scrambled data, never your actual passwords.

MOVING TO A NEW COMPUTER OR AFTER REINSTALLING WINDOWS
  Your Windows username may be different on a new PC or after
  reinstalling/formatting - this means the app's default file
  location (which is based on your username) will point to a
  folder that doesn't exist on the new system, and the vault
  will appear empty even though nothing was lost.

  To fix this:
  1. Find your old .lockshed.enc file (e.g. from a backup,
     USB drive, or your old OneDrive folder)
  2. Copy it anywhere on the new computer (e.g. the Desktop)
  3. Open the app -> Settings -> Data file -> click "Open existing…"
  4. Select the copied file, then click "Save & apply"
  5. Unlock with your existing master password - nothing was reset

  IMPORTANT: Use "Open existing…" (not "New…") for this - "New…"
  is only for creating a brand new, empty vault.

ALTERNATIVE: Manual backup
  Periodically copy .lockshed.enc to a USB drive or
  external disk. Since it's encrypted, it's safe to store
  anywhere, even on a public USB stick - just don't lose the
  master password that unlocks it.

ALSO CONSIDER: PDF export (Settings -> Import/Export)
  Exports your entries to a PDF, with or without passwords in
  plain text. Useful as an emergency offline reference, but if
  you choose to include passwords, store that PDF as carefully
  as you would the vault itself - delete it when no longer needed.


----------------------------------------
5. MOBILE ACCESS (WiFi)
----------------------------------------

You can view and copy passwords from your Android phone's
browser while connected to the same WiFi network as your
computer.

SETUP
  1. On the computer: Settings -> Mobile, note your IP address
     and set a PIN (6-10 digits)
  2. Restart The LockShed (only needed the FIRST time you set
     a PIN - the phone server doesn't start until it knows you
     actually want it)
  3. On your phone's browser, visit:
     http://<your-computer-IP>:19486
  4. Enter the IP, port, and PIN to unlock

IMPORTANT NOTES
  - This only works while both devices are on the SAME local
    network (e.g. your home WiFi). It does not work over mobile
    data or different networks.
  - ONLY enable this on networks you trust (e.g. your home WiFi),
    never public/office WiFi - anyone else on that network can
    reach this feature too.
  - The PIN is a convenience lock for casual access on your own
    network, not a replacement for your master password's
    encryption strength. Don't reuse your master password as
    the mobile PIN.
  - Your phone's PIN entry is exchanged for a temporary session -
    after 5 wrong PIN attempts from the same device, that device
    is locked out for a minute before it can try again.
  - If you don't set a PIN, the phone server never starts at all
    - there's no open port sitting on your network for a feature
    you're not using.
  - If your phone can't connect, check that Windows Firewall
    allows incoming connections on port 19486, and that your
    computer's network is set to "Private" (not "Public") in
    Windows network settings.


----------------------------------------
6. BROWSER AUTOFILL (Brave/Chrome)
----------------------------------------

A browser extension lets you autofill saved passwords directly
on websites.

SETUP
  1. Make sure The LockShed is running and unlocked (Start Menu /
     desktop shortcut, or starta.bat if running from source)
  2. In Brave, go to brave://extensions/
  3. Enable "Developer mode"
  4. Click "Load unpacked" and select the "chrome_extension" folder
     (inside your install folder, e.g. C:\Program Files\LockShed\
     chrome_extension, or next to password_manager.py if running
     from source)
  5. PAIR the extension (one-time step):
       a. In the app: Settings -> Extension tab -> "Copy" the
          pairing code
       b. Right-click the extension's icon in Brave's toolbar ->
          Options
       c. Paste the code and click "Save pairing code"
  6. A small lock icon appears in login forms with saved passwords

If you ever click "Regenerate code" in Settings -> Extension, the
old code stops working immediately and you'll need to repeat
step 5 with the new one.

KEYBOARD SHORTCUT
  Press Ctrl+Shift+L while a login field is focused to trigger
  autofill manually - useful on sites where the icon doesn't
  appear (e.g. some popup login forms).

This extension only talks to the app on your own computer
(localhost) - it never sends anything over the internet. Only
the extension itself (not any website you visit) is able to
reach it: every request is checked against both the pairing code
above and the browser's own proof of which extension is asking,
which is not something a website can fake. Passwords also never
leave the app while the vault is locked, even if the extension
is correctly paired.


----------------------------------------
7. GOOD HABITS WHILE USING THIS APP
----------------------------------------

  - Use the password generator for new accounts instead of
    reusing passwords. The app warns you about duplicates.
  - Pay attention to the strength indicator - "Very weak" and
    "Weak" passwords are flagged using realistic pattern
    detection (not just length/character counting), so it
    catches things like "Password123" that look complex but
    aren't.
  - The vault automatically locks after 10 minutes of inactivity.
    You'll need your master password again - this protects you
    if you walk away from your computer.
  - Use "Exit" (left sidebar) to fully close the app when done,
    rather than leaving it minimized to the system tray
    indefinitely on shared computers.
  - Periodically check Settings -> Categories and clean up
    anything you no longer need. You can also reorder categories
    by typing a new position number next to any category (1 =
    top of the list) and pressing Enter.


----------------------------------------
8. WHAT THIS APP DOES NOT DO
----------------------------------------

To set expectations clearly:

  - No cloud sync between multiple devices (by design - your
    data never leaves your control)
  - No password sharing with other people/accounts
  - No biometric unlock (fingerprint/face) - master password only
  - No automatic dark web breach monitoring
  - Mobile access requires same WiFi network, not available
    from anywhere

If your needs grow beyond what this app offers, that's a sign
you might want a commercial password manager with a dedicated
security team - this is a personal project built for one person's
use, not a replacement for professional security infrastructure
at scale.


----------------------------------------
9. TROUBLESHOOTING
----------------------------------------

APP WON'T START
  If installed via LockShed-Setup.exe: try reinstalling, or check
  Windows Event Viewer for a crash log to share for help - there's
  no debug.bat in this version since there's no Python/console step.
  If running from source: run debug.bat and read the error message.
  Most commonly this is a missing Python package - run installera.bat
  again.

FORGOT MASTER PASSWORD
  There is no recovery. This is intentional (see section 3).
  If you have a PDF export or written-down backup of your
  passwords from before, you can rebuild a new vault from that.
  Otherwise, the data is unrecoverable - this is the tradeoff for
  genuinely strong encryption.

VAULT APPEARS EMPTY AFTER REINSTALLING WINDOWS OR MOVING TO A
NEW COMPUTER
  Nothing was deleted - see section 4 ("MOVING TO A NEW COMPUTER
  OR AFTER REINSTALLING WINDOWS") for how to point the app back
  at your existing encrypted file using Settings -> Data file ->
  "Open existing…".

MOBILE/EXTENSION NOT CONNECTING
  See sections 5 and 6 above for network-specific troubleshooting.

EXTENSION SAYS "NOT PAIRED" OR "APP NOT RUNNING" BUT THE APP IS OPEN
  The extension needs a one-time pairing code from the app before
  it will talk to it - see section 6, step 5. If you already
  paired it once and it stopped working, someone (maybe you)
  probably clicked "Regenerate code" in Settings -> Extension -
  re-paste the new code into the extension's Options page.

MOBILE ACCESS STILL NOT REACHABLE AFTER SETTING A PIN
  The phone server only starts the FIRST time it sees a PIN is
  configured, which means you need to fully close and reopen
  The LockShed once after setting a PIN for the first time.
  After that first restart it starts automatically every time.

GENERAL ODD BEHAVIOR
  If running from source, try debug.bat to see if any error
  appears in the console. If installed via LockShed-Setup.exe,
  see "APP WON'T START" above instead.


----------------------------------------
10. BUILDING A WINDOWS INSTALLER (Setup.exe)
----------------------------------------

This is for developers/maintainers who want to package the app
into a single Setup.exe that installs LockShed without anyone
needing Python installed. Regular users can ignore this section
entirely - installera.bat + starta.bat is all you need day to day.

BEFORE EVERY RELEASE - BUMP THE VERSION NUMBER IN 3 PLACES
  These three must always match:
    1. APP_VERSION in password_manager.py           (e.g. "v1.0.1")
    2. MyAppVersion in build\installer.iss           (e.g. "1.0.1")
    3. The version-tag text in index.html's download section
  Use semantic-ish versioning: bump the last number for small
  fixes (v1.0.0 -> v1.0.1), the middle number for new features
  (v1.0.x -> v1.1.0), the first number for major overhauls.

ONE-TIME SETUP (on a Windows machine)
  1. Install Python 3.10+ if not already installed, and make sure
     "Add to PATH" was checked during its install.
  2. Install Inno Setup: https://jrsoftware.org/isinfo.php
     (free, used to build the actual Setup.exe wrapper)

BUILDING
  1. Double-click build.bat in the project root.
  2. It will:
       a. pip-install PyInstaller plus all of LockShed's own
          dependencies
       b. Run PyInstaller to bundle password_manager.py, its
          dependencies, and the chrome_extension/mobile_pwa/assets
          folders into dist\LockShed\LockShed.exe (a standalone
          app - no Python installation needed to run it)
       c. Run Inno Setup on build\installer.iss to wrap that into
          dist_installer\LockShed-Setup.exe
  3. If Inno Setup's ISCC.exe isn't on your PATH, step (c) is
     skipped automatically with instructions - you can either add
     it to PATH and re-run, or open build\installer.iss directly
     in the Inno Setup app and click Compile.

WHAT'S BUNDLED VS. WHAT ISN'T
  - The .exe itself, all Python dependencies, and the
    chrome_extension/mobile_pwa/assets folders are bundled and
    installed automatically.
  - The browser extension is NOT auto-installed into Brave/Chrome.
    Browsers don't allow installers to silently add extensions
    (a deliberate security restriction from Google) - whoever
    installs LockShed still needs to do the one-time "Load
    unpacked" step from section 6 themselves, pointing at the
    chrome_extension folder inside the install directory. The
    only way around this is publishing the extension to the
    Chrome Web Store, which is a separate, optional step.

THINGS TO EXPECT
  - Setup.exe is unsigned, so Windows SmartScreen will show an
    "unknown publisher" warning the first time someone runs it.
    Clicking "More info" -> "Run anyway" proceeds normally. Getting
    rid of this warning requires a paid code-signing certificate -
    not required for the app to work, purely cosmetic trust
    signaling.
  - Some antivirus engines flag PyInstaller-built executables as
    false positives (a known, common issue with the tool, not
    specific to this app). If that happens, add an exception.
  - Uninstalling never touches your vault or settings files -
    those live in your user profile (see section 2), completely
    outside the installer's install directory.
  - If you already have an existing "Lösenordsvalvet" install,
    the automatic migration described in section 2 still runs
    the first time the new Setup.exe-installed version starts.


========================================
  Keep your master password safe.
  Nobody - including the creator of this app - can recover
  your data without it. That's what makes it secure.
========================================
