@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   Building The LockShed - Setup.exe
echo ============================================
echo.
echo This must be run on Windows, with Python installed and on PATH.
echo See README.txt section 10 for one-time setup instructions.
echo.

echo [1/3] Installing/upgrading build dependencies...
python -m pip install --upgrade pyinstaller customtkinter cryptography pyperclip reportlab pillow pystray zxcvbn flask flask-cors --quiet
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Check that Python is installed and on PATH.
    pause
    exit /b 1
)

echo [2/3] Running PyInstaller (this can take a minute or two)...
if exist build\work rmdir /s /q build\work
if exist dist\LockShed rmdir /s /q dist\LockShed
pyinstaller build\lockshed.spec --distpath dist --workpath build\work --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed - see the output above.
    pause
    exit /b 1
)
echo.
echo Build output: dist\LockShed\LockShed.exe
echo (You can already run that exe directly to sanity-check it before
echo  building the installer.)
echo.

echo [3/3] Building installer with Inno Setup...
where ISCC >nul 2>nul
if %errorlevel%==0 (
    ISCC build\installer.iss
    if errorlevel 1 (
        echo.
        echo ERROR: Inno Setup compilation failed - see the output above.
        pause
        exit /b 1
    )
    echo.
    echo ============================================
    echo   Done! Installer created at:
    echo   dist_installer\LockShed-Setup.exe
    echo ============================================
) else (
    echo Inno Setup compiler (ISCC.exe) not found on PATH.
    echo.
    echo   1. Install Inno Setup:  https://jrsoftware.org/isinfo.php
    echo   2. Either add its install folder to PATH and re-run this
    echo      script, or open build\installer.iss directly in the
    echo      Inno Setup app and click Compile.
)

echo.
pause
