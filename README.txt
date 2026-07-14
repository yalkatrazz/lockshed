========================================
  THE LOCKSHED - Guide
========================================

A private, local password manager. No cloud account, no
subscription, no third party ever sees your data.


----------------------------------------
1. INSTALLATION
----------------------------------------

OPTION A - You have "LockShed-Setup.exe"
  1. Run it and follow the installer
  2. If Windows SmartScreen warns "unknown publisher", click
     "More info" -> "Run anyway" (just means it isn't
     code-signed - nothing to worry about)
  3. Launch The LockShed from the Start Menu
  4. Choose a strong master password when prompted

OPTION B - Running from source
  1. Install Python 3.9+ (check "Add Python to PATH")
  2. Double-click installera.bat
  3. Double-click starta.bat to open the app
  4. Choose a strong master password when prompted
  If something won't start, run debug.bat to see the error.


----------------------------------------
2. WHERE YOUR DATA LIVES
----------------------------------------

  Vault (encrypted):        C:\Users\<You>\.lockshed.enc
  Settings (no passwords):  C:\Users\<You>\.lockshed_settings.json

The vault file can't be read without your master password -
not even by you, directly. The settings file is safe to view
or delete (just resets preferences).


----------------------------------------
3. SECURITY
----------------------------------------

  - AES-256-CBC + HMAC-SHA256 encryption, PBKDF2 key derivation
  - Your master password is never stored anywhere, in any form
  - If you forget it, there is no recovery - by design
  - Choose something memorable but not guessable (a 4-5 word
    passphrase beats a short "clever" password)


----------------------------------------
4. BACKING UP YOUR VAULT
----------------------------------------

There's no cloud account, so backups are on you.

RECOMMENDED - sync via cloud storage
  1. Settings -> Data file -> "New..."
  2. Choose a folder inside OneDrive/Dropbox/Google Drive
  3. The app offers to move your existing file there
  Safe to do - the file is already encrypted before it ever
  touches the cloud folder.

MOVING TO A NEW COMPUTER
  1. Copy your old .lockshed.enc file to the new computer
  2. Settings -> Data file -> "Open existing..."
  3. Select the file, click "Save & apply"
  4. Unlock with your existing master password
  Use "Open existing...", not "New..." - "New..." creates an
  empty vault.

MANUAL BACKUP
  Copy .lockshed.enc to a USB drive or external disk whenever
  you like - it's encrypted, so safe to store anywhere.

PDF EXPORT (Settings -> Import/Export)
  Useful as an emergency offline reference. If you include
  passwords in plain text, treat that PDF as carefully as the
  vault itself.


----------------------------------------
5. MOBILE ACCESS (WiFi)
----------------------------------------

  1. Settings -> Mobile: note your IP, set a PIN (6-10 digits)
  2. Restart The LockShed (only needed the first time)
  3. On your phone (same WiFi): visit http://<computer-IP>:19486
  4. Enter IP, port, and PIN to unlock

  - Only use this on networks you trust (e.g. home WiFi)
  - 5 wrong PIN attempts locks that device out for a minute
  - No PIN set = the phone server never starts at all
  - Can't connect? Check Windows Firewall allows port 19486,
    and your network is set to "Private", not "Public"


----------------------------------------
6. BROWSER AUTOFILL (Brave/Chrome)
----------------------------------------

  1. Make sure The LockShed is running and unlocked
  2. brave://extensions/ -> enable "Developer mode"
  3. "Load unpacked" -> select the chrome_extension folder
  4. Pair it (one-time):
       a. In the app: Settings -> Extension -> "Copy" pairing code
       b. Right-click the extension icon -> Options
       c. Paste the code -> "Save pairing code"
  5. A lock icon now appears in login forms with saved passwords

  Shortcut: Ctrl+Shift+L autofills manually if the icon doesn't
  appear (e.g. some popup login forms).

  The extension only talks to the app on localhost, verified by
  both the pairing code and the browser's own proof of which
  extension is asking - no website can fake that.


----------------------------------------
7. GOOD HABITS
----------------------------------------

  - Use the built-in generator instead of reusing passwords
  - Pay attention to the strength indicator
  - The vault auto-locks after 10 minutes idle
  - Use "Exit" to fully close the app on shared computers
  - Reorder categories by dragging the handle in Settings


----------------------------------------
8. WHAT THIS APP DOES NOT DO
----------------------------------------

  - No cloud sync between devices (by design)
  - No sharing passwords with other accounts
  - No biometric unlock - master password only
  - No breach monitoring
  - Mobile access requires the same WiFi network


----------------------------------------
9. TROUBLESHOOTING
----------------------------------------

APP WON'T START
  Installed version: try reinstalling, or check Windows Event
  Viewer for a crash log.
  Source version: run debug.bat and read the error.

FORGOT MASTER PASSWORD
  No recovery - see section 3. Rebuild from a PDF export/backup
  if you have one.

VAULT APPEARS EMPTY AFTER A NEW COMPUTER OR REINSTALL
  Nothing was deleted - see section 4, "MOVING TO A NEW COMPUTER".

EXTENSION SAYS "NOT PAIRED" OR "APP NOT RUNNING"
  Re-pair it (section 6, step 4) - especially if you clicked
  "Regenerate code" in Settings recently.

MOBILE NOT REACHABLE AFTER SETTING A PIN
  Restart the app once - the phone server only starts on the
  first launch after a PIN is configured.


========================================
  Keep your master password safe.
  Nobody - including the creator of this app - can recover
  your data without it.
========================================
