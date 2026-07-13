; Inno Setup script for The LockShed.
;
; Requires Inno Setup: https://jrsoftware.org/isinfo.php
; Run this AFTER building with PyInstaller (dist\LockShed\LockShed.exe
; must already exist) - build.bat does both steps in the right order.
;
; Open this file in the Inno Setup app and click Compile, or run
; ISCC.exe on it from the command line (also from the PROJECT ROOT,
; since paths below are relative to that).

#define MyAppName "The LockShed"
; Bump this on every release, kept in sync with APP_VERSION in
; password_manager.py and the version shown on the landing page.
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LockShed"
#define MyAppExeName "LockShed.exe"

[Setup]
; Generated once and then kept stable - lets Windows recognize upgrades
; vs. a totally different app. Do not regenerate this on future builds.
AppId={{B3F1E7B0-4C2A-4E7C-9C7A-6D6D2F9A2B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\LockShed
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=LockShed-Setup
SetupIconFile=..\assets\lock_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; Not code-signed - Windows SmartScreen will show an "unknown publisher"
; warning the first time someone runs this. See README.txt for details;
; a code-signing certificate removes this but isn't required to work.
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Pulls in the entire onedir PyInstaller output - the exe, its bundled
; Python runtime/libraries, and the chrome_extension/mobile_pwa/assets
; data folders that were included via lockshed.spec's `datas`.
Source: "..\dist\LockShed\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Also ship the user-facing README (not part of the PyInstaller bundle
; itself, so it needs to be added here separately).
Source: "..\README.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Read Me"; Filename: "{app}\README.txt"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

; Deliberately no [UninstallDelete] entries for the vault/settings files -
; those live in %USERPROFILE%\.lockshed.enc and .lockshed_settings.json,
; completely outside {app}, so a normal uninstall never touches them.
