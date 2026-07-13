@echo off
chcp 65001 >nul
echo ============================================
echo   Installerar The LockShed...
echo ============================================
python -m pip install customtkinter cryptography pyperclip reportlab pillow pystray zxcvbn flask flask-cors --quiet
if %errorlevel% == 0 (
    echo.
    echo Klart! Kor starta.bat for att oppna appen.
) else (
    echo.
    echo Fel: Kontrollera att Python ar installerat och tillagt i PATH.
)
pause
